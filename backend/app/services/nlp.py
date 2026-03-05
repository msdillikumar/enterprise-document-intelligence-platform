"""
NLP Entity Extraction Module
Uses spaCy NER + regex patterns to extract structured entities from text.
"""
import re
import spacy
from typing import List, Dict

_nlp = None


def _get_nlp():
    """Lazy-load spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


# Regex patterns for structured data extraction
PATTERNS = {
    "INVOICE_NUMBER": r"(?i)(?:invoice|inv|bill)\s*(?:#|no\.?|number)?\s*:?\s*([A-Z0-9\-]{3,20})",
    "DATE": r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b",
    "AMOUNT": r"(?:USD|\$|€|£|₹)\s*[\d,]+\.?\d*|\b\d{1,3}(?:,\d{3})*\.\d{2}\b",
    "EMAIL": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "PHONE": r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}",
    "SSN": r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
    "ID_NUMBER": r"(?i)(?:id|passport|license)\s*(?:#|no\.?|number)?\s*:?\s*([A-Z0-9\-]{5,20})",
}


def extract_entities_spacy(text: str) -> List[Dict]:
    """Extract named entities using spaCy NER."""
    nlp = _get_nlp()
    doc = nlp(text)
    entities = []

    for ent in doc.ents:
        entities.append({
            "entity_type": ent.label_,
            "entity_value": ent.text,
            "start_pos": ent.start_char,
            "end_pos": ent.end_char,
            "confidence": round(0.7 + (0.3 * min(len(ent.text) / 20, 1)), 2),  # heuristic
            "extraction_method": "spacy_ner",
        })

    return entities


def extract_entities_regex(text: str) -> List[Dict]:
    """Extract entities using regex patterns."""
    entities = []

    for entity_type, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text):
            value = match.group(0)
            entities.append({
                "entity_type": entity_type,
                "entity_value": value,
                "start_pos": match.start(),
                "end_pos": match.end(),
                "confidence": 0.95,  # regex matches are high confidence
                "extraction_method": "regex_pattern",
            })

    return entities


def extract_entities(text: str) -> List[Dict]:
    """
    Extract all entities using both spaCy NER and regex patterns.
    Deduplicates overlapping entities, preferring higher confidence.
    """
    if not text or not text.strip():
        return []

    spacy_entities = extract_entities_spacy(text)
    regex_entities = extract_entities_regex(text)

    # Combine and deduplicate (prefer regex for overlapping spans)
    all_entities = []
    used_spans = set()

    # Add regex entities first (higher confidence)
    for entity in regex_entities:
        span = (entity["start_pos"], entity["end_pos"])
        used_spans.add(span)
        all_entities.append(entity)

    # Add spaCy entities that don't overlap
    for entity in spacy_entities:
        span = (entity["start_pos"], entity["end_pos"])
        overlaps = any(
            not (span[1] <= s[0] or span[0] >= s[1])
            for s in used_spans
        )
        if not overlaps:
            all_entities.append(entity)
            used_spans.add(span)

    return sorted(all_entities, key=lambda e: e["start_pos"])
