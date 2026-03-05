"""
LLM-based Entity Extraction Module
Replaces spaCy NLP with Generative AI (Transformer-based LLM).

Extraction Strategy (layered fallback):
  1. llama-cpp-python  →  local GGUF model (best quality)
  2. HuggingFace free Inference API  →  cloud fallback
  3. Enhanced regex patterns  →  always-available safety net

Model: cuongbuift/invoice-extraction-v2-llama-2-7b-v2-Q4_0-GGUF
"""

import os
import re
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ── regex patterns (safety-net & supplement) ──────────────────────────
ENTITY_PATTERNS = {
    "INVOICE_NUMBER": r"(?:invoice|inv|bill)\s*(?:#|no\.?|number)?[\s:]*([A-Z0-9\-]{3,20})",
    "DATE": r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b",
    "AMOUNT": r"\$[\d,]+\.?\d{0,2}",
    "SSN": r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
    "EMAIL": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "PHONE": r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}",
    "PERSON": r"(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+",
    "ORG": r"(?:Inc\.|LLC|Ltd\.|Corp\.|Company|Co\.)(?:\s|$)",
    "ADDRESS": r"\d{1,5}\s+[\w\s]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Dr|Drive|Lane|Ln|Way|Ct|Court)\b",
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "URL": r"https?://[\w\-\.]+\.\w+(?:/[\w\-\./?%&=]*)?",
}

# PII entity types
PII_TYPES = {
    "SSN", "CREDIT_CARD", "EMAIL", "PHONE", "PERSON",
    "IP_ADDRESS", "US_PASSPORT", "IBAN",
}

# ── LLM prompt template ──────────────────────────────────────────────
EXTRACTION_PROMPT = """You are an enterprise document intelligence system.
Extract ALL entities from the following document text. Return ONLY valid JSON.

Categories to extract:
- INVOICE_NUMBER, DATE, AMOUNT, PERSON, ORG, ADDRESS
- SSN, CREDIT_CARD, EMAIL, PHONE, IP_ADDRESS, URL
- Any other relevant named entities

Document text:
\"\"\"
{text}
\"\"\"

Return a JSON array of objects with keys: "entity_type", "entity_value", "confidence".
Example: [{"entity_type": "PERSON", "entity_value": "John Doe", "confidence": 0.95}]
JSON:"""


# ═══════════════════════════════════════════════════════════════════════
#  Layer 1 – Local LLM via llama-cpp-python
# ═══════════════════════════════════════════════════════════════════════

_llm_model = None
_llm_load_attempted = False


def _get_llm():
    """Lazy-load the GGUF model. Returns None if unavailable."""
    global _llm_model, _llm_load_attempted
    if _llm_load_attempted:
        return _llm_model
    _llm_load_attempted = True

    try:
        from llama_cpp import Llama  # type: ignore[import-not-found]

        repo = os.getenv(
            "LLM_REPO_ID",
            "cuongbuift/invoice-extraction-v2-llama-2-7b-v2-Q4_0-GGUF",
        )
        fname = os.getenv(
            "LLM_FILENAME",
            "invoice-extraction-v2-llama-2-7b-v2.Q4_0.gguf",
        )
        logger.info("Loading LLM model from %s / %s …", repo, fname)
        _llm_model = Llama.from_pretrained(
            repo_id=repo,
            filename=fname,
            n_ctx=2048,
            n_threads=4,
            verbose=False,
        )
        logger.info("LLM model loaded successfully.")
        return _llm_model
    except Exception as exc:
        logger.warning("llama-cpp-python not available: %s", exc)
        _llm_model = None
        return None


def _extract_with_llm(text: str) -> Optional[List[Dict]]:
    """Run extraction via local LLM. Returns None on failure."""
    llm = _get_llm()
    if llm is None:
        return None

    try:
        prompt = EXTRACTION_PROMPT.format(text=text[:3000])  # cap context
        output = llm(
            prompt,
            max_tokens=1024,
            temperature=0.1,
            stop=["```", "\n\n\n"],
        )
        raw = output["choices"][0]["text"].strip()
        entities = _parse_llm_json(raw)
        if entities:
            for e in entities:
                e["extraction_method"] = "llm_local"
            return entities
    except Exception as exc:
        logger.warning("LLM extraction failed: %s", exc)
    return None


# ═══════════════════════════════════════════════════════════════════════
#  Layer 2 – HuggingFace Free Inference API
# ═══════════════════════════════════════════════════════════════════════

HF_API_URL = "https://api-inference.huggingface.co/models/dslim/bert-base-NER"


def _extract_with_huggingface(text: str) -> Optional[List[Dict]]:
    """Use HuggingFace free NER endpoint as cloud fallback."""
    hf_token = os.getenv("HF_API_TOKEN", "")
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    try:
        import requests

        resp = requests.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": text[:1500]},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning("HF API returned %s", resp.status_code)
            return None

        ner_results = resp.json()
        if not isinstance(ner_results, list):
            return None

        # Merge sub-word tokens and map to our entity types
        entities = _merge_hf_tokens(ner_results)
        for e in entities:
            e["extraction_method"] = "huggingface_ner"
        return entities if entities else None
    except Exception as exc:
        logger.warning("HuggingFace extraction failed: %s", exc)
        return None


def _merge_hf_tokens(tokens: list) -> List[Dict]:
    """Merge BIO-tagged sub-word tokens into full entities."""
    HF_TYPE_MAP = {
        "PER": "PERSON",
        "ORG": "ORG",
        "LOC": "ADDRESS",
        "MISC": "MISC",
    }
    merged: List[Dict] = []
    current = None

    for tok in tokens:
        label = tok.get("entity_group") or tok.get("entity", "")
        word = tok.get("word", "").replace("##", "")
        score = tok.get("score", 0.5)

        # Determine base type
        base = label.replace("B-", "").replace("I-", "")
        mapped = HF_TYPE_MAP.get(base, base)

        is_continuation = label.startswith("I-") or (
            current and mapped == current["entity_type"]
            and tok.get("start", 0) - current.get("_end", 0) <= 1
        )

        if is_continuation and current:
            current["entity_value"] += word if word.startswith("##") else " " + word
            current["confidence"] = (current["confidence"] + score) / 2
            current["_end"] = tok.get("end", current.get("_end", 0))
        else:
            if current:
                merged.append(current)
            current = {
                "entity_type": mapped,
                "entity_value": word,
                "confidence": round(score, 3),
                "_end": tok.get("end", 0),
            }
    if current:
        merged.append(current)

    # Remove helper key
    for m in merged:
        m.pop("_end", None)
    return merged


# ═══════════════════════════════════════════════════════════════════════
#  Layer 3 – Enhanced Regex Patterns (always-available)
# ═══════════════════════════════════════════════════════════════════════

def _extract_with_regex(text: str) -> List[Dict]:
    """Deterministic regex extraction – always works."""
    entities: List[Dict] = []
    seen = set()

    for etype, pattern in ENTITY_PATTERNS.items():
        for m in re.finditer(pattern, text, re.IGNORECASE):
            value = m.group(1) if m.lastindex else m.group(0)
            value = value.strip()
            key = (etype, value)
            if key in seen or len(value) < 2:
                continue
            seen.add(key)
            entities.append({
                "entity_type": etype,
                "entity_value": value,
                "confidence": 0.75,
                "start_pos": m.start(),
                "end_pos": m.end(),
                "is_pii": etype in PII_TYPES,
                "extraction_method": "regex_pattern",
            })

    return entities


# ═══════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════

def extract_entities(text: str) -> List[Dict]:
    """
    Extract entities using the best available method (LLM → HF → regex).

    IPO (Input → Process → Output):
      Input  : raw OCR text
      Process: Transformer-based Gen-AI entity extraction with regex augmentation
      Output : list of entity dicts with type, value, confidence, method
    """
    if not text or not text.strip():
        return []

    all_entities: List[Dict] = []
    method_used = "regex_pattern"

    # Try Layer 1: Local LLM
    llm_entities = _extract_with_llm(text)
    if llm_entities:
        all_entities.extend(llm_entities)
        method_used = "llm_local"
        logger.info("LLM extracted %d entities", len(llm_entities))
    else:
        # Try Layer 2: HuggingFace
        hf_entities = _extract_with_huggingface(text)
        if hf_entities:
            all_entities.extend(hf_entities)
            method_used = "huggingface_ner"
            logger.info("HuggingFace extracted %d entities", len(hf_entities))

    # Always supplement with regex (catches structured PII the LLM may miss)
    regex_entities = _extract_with_regex(text)
    logger.info("Regex extracted %d entities", len(regex_entities))

    # Merge: add regex entities not already found by LLM/HF
    existing_values = {e["entity_value"].lower() for e in all_entities}
    for re_ent in regex_entities:
        if re_ent["entity_value"].lower() not in existing_values:
            all_entities.append(re_ent)
            existing_values.add(re_ent["entity_value"].lower())

    # Enrich PII flags
    for entity in all_entities:
        entity.setdefault("is_pii", entity["entity_type"] in PII_TYPES)
        entity.setdefault("start_pos", None)
        entity.setdefault("end_pos", None)
        entity.setdefault("confidence", 0.5)

    logger.info(
        "Total entities: %d (primary method: %s)", len(all_entities), method_used
    )
    return all_entities


# ── helpers ───────────────────────────────────────────────────────────

def _parse_llm_json(raw: str) -> Optional[List[Dict]]:
    """Best-effort parse JSON from LLM output."""
    # Try direct parse
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try extracting JSON array from surrounding text
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return None
