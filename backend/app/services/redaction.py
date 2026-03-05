"""
Sensitive Data Redaction Module
Detects and redacts PII (Personally Identifiable Information) from text.
Uses Microsoft Presidio + custom regex patterns.
"""
import re
from typing import List, Dict, Tuple

# PII patterns for redaction
PII_PATTERNS = {
    "SSN": {
        "pattern": r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b",
        "replacement": "[SSN REDACTED]",
    },
    "CREDIT_CARD": {
        "pattern": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
        "replacement": "[CREDIT CARD REDACTED]",
    },
    "EMAIL": {
        "pattern": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "replacement": "[EMAIL REDACTED]",
    },
    "PHONE": {
        "pattern": r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}",
        "replacement": "[PHONE REDACTED]",
    },
    "IP_ADDRESS": {
        "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "replacement": "[IP REDACTED]",
    },
    "US_PASSPORT": {
        "pattern": r"\b[A-Z]\d{8}\b",
        "replacement": "[PASSPORT REDACTED]",
    },
    "IBAN": {
        "pattern": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b",
        "replacement": "[IBAN REDACTED]",
    },
}


def redact_text(text: str, entities: List[Dict] = None) -> Dict:
    """
    Redact sensitive information from text.
    Returns redacted text and details of what was redacted.
    """
    if not text:
        return {"redacted_text": "", "redactions": [], "pii_count": 0}

    redacted = text
    redactions = []

    # First try Presidio (if available)
    try:
        presidio_result = _redact_with_presidio(text)
        if presidio_result["pii_count"] > 0:
            return presidio_result
    except Exception:
        pass  # Fallback to regex

    # Regex-based redaction
    for pii_type, config in PII_PATTERNS.items():
        pattern = config["pattern"]
        replacement = config["replacement"]

        matches = list(re.finditer(pattern, redacted))
        for match in reversed(matches):  # Reverse to preserve positions
            original = match.group(0)
            redactions.append({
                "type": pii_type,
                "original": original,
                "replacement": replacement,
                "start": match.start(),
                "end": match.end(),
            })
            redacted = redacted[:match.start()] + replacement + redacted[match.end():]

    # Also redact entities flagged as PII
    if entities:
        pii_entity_types = {"PERSON", "person"}
        for entity in entities:
            if entity["entity_type"] in pii_entity_types and entity.get("is_pii"):
                value = entity["entity_value"]
                if value in redacted:
                    replacement = f"[{entity['entity_type']} REDACTED]"
                    redacted = redacted.replace(value, replacement)
                    redactions.append({
                        "type": entity["entity_type"],
                        "original": value,
                        "replacement": replacement,
                    })

    return {
        "redacted_text": redacted,
        "redactions": redactions,
        "pii_count": len(redactions),
    }


def _redact_with_presidio(text: str) -> Dict:
    """Use Microsoft Presidio for PII detection and redaction."""
    from presidio_analyzer import AnalyzerEngine  # type: ignore[import-not-found]
    from presidio_anonymizer import AnonymizerEngine  # type: ignore[import-not-found]

    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()

    # Analyze text for PII
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=[
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
            "CREDIT_CARD", "US_SSN", "IBAN_CODE",
            "IP_ADDRESS", "US_PASSPORT", "US_DRIVER_LICENSE",
        ],
    )

    # Anonymize
    anonymized = anonymizer.anonymize(text=text, analyzer_results=results)

    redactions = []
    for result in results:
        redactions.append({
            "type": result.entity_type,
            "original": text[result.start:result.end],
            "replacement": f"[{result.entity_type} REDACTED]",
            "start": result.start,
            "end": result.end,
            "confidence": result.score,
        })

    return {
        "redacted_text": anonymized.text,
        "redactions": redactions,
        "pii_count": len(redactions),
        "method": "presidio",
    }


def get_redacted_entities(entities: List[Dict]) -> List[Dict]:
    """
    Mark entities as PII and create redacted versions.
    """
    pii_types = {"SSN", "CREDIT_CARD", "EMAIL", "PHONE", "IP_ADDRESS",
                 "US_PASSPORT", "IBAN", "PERSON", "EMAIL_ADDRESS",
                 "PHONE_NUMBER", "US_SSN"}

    for entity in entities:
        if entity["entity_type"] in pii_types:
            entity["is_pii"] = True
            entity["redacted_value"] = f"[{entity['entity_type']} REDACTED]"
        else:
            entity["is_pii"] = False
            entity["redacted_value"] = entity["entity_value"]

    return entities
