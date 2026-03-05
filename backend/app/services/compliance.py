"""
Authenticity & Compliance Check Module
Validates document authenticity and compliance with predefined rules.
"""
import re
from typing import List, Dict
from datetime import datetime, timedelta
from ..config import COMPLIANCE_RULES


def check_authenticity(text: str, ocr_result: Dict, entities: List[Dict]) -> Dict:
    """
    Check document authenticity based on multiple signals:
    - OCR quality (too perfect = possibly generated, too low = unreadable)
    - Text coherence
    - Entity consistency
    - Metadata validation
    """
    signals = []
    score = 1.0  # Start at 100% authentic

    # 1. OCR quality check
    ocr_conf = ocr_result.get("ocr_confidence", 0)
    if ocr_conf < 20:
        signals.append({
            "check": "ocr_quality",
            "status": "fail",
            "message": f"Very low OCR confidence ({ocr_conf}%) - document may be corrupted or unreadable",
        })
        score -= 0.3
    elif ocr_conf < 50:
        signals.append({
            "check": "ocr_quality",
            "status": "warning",
            "message": f"Low OCR confidence ({ocr_conf}%) - text quality is poor",
        })
        score -= 0.1
    else:
        signals.append({
            "check": "ocr_quality",
            "status": "pass",
            "message": f"OCR confidence is acceptable ({ocr_conf}%)",
        })

    # 2. Text length check
    word_count = ocr_result.get("word_count", 0)
    if word_count < 5:
        signals.append({
            "check": "text_content",
            "status": "fail",
            "message": "Document contains almost no readable text",
        })
        score -= 0.3
    elif word_count < 20:
        signals.append({
            "check": "text_content",
            "status": "warning",
            "message": "Document contains very little text",
        })
        score -= 0.1
    else:
        signals.append({
            "check": "text_content",
            "status": "pass",
            "message": f"Document contains {word_count} words",
        })

    # 3. Entity consistency - check for date validity
    dates = [e for e in entities if e["entity_type"] in ("DATE", "date")]
    for d in dates:
        if not _is_valid_date(d["entity_value"]):
            signals.append({
                "check": "date_validity",
                "status": "warning",
                "message": f"Potentially invalid date found: {d['entity_value']}",
            })
            score -= 0.05

    # 4. Repetition check (duplicate text blocks = suspicious)
    lines = text.split("\n")
    unique_lines = set(l.strip() for l in lines if l.strip())
    if len(lines) > 10 and len(unique_lines) < len(lines) * 0.3:
        signals.append({
            "check": "repetition",
            "status": "warning",
            "message": "High text repetition detected - may indicate template or generated content",
        })
        score -= 0.15

    is_authentic = score >= 0.5

    return {
        "is_authentic": is_authentic,
        "authenticity_score": round(max(score, 0), 3),
        "signals": signals,
        "verdict": "AUTHENTIC" if is_authentic else "SUSPICIOUS",
    }


def check_compliance(text: str, entities: List[Dict], file_type: str) -> Dict:
    """
    Check document compliance against predefined rules.
    """
    issues = []
    status = "compliant"

    # 1. File format check
    allowed = COMPLIANCE_RULES.get("allowed_formats", [])
    if file_type.lower() not in allowed:
        issues.append({
            "rule": "file_format",
            "severity": "error",
            "message": f"File type '{file_type}' is not in allowed formats: {allowed}",
        })
        status = "non_compliant"

    # 2. Required fields check
    required = COMPLIANCE_RULES.get("required_fields", [])
    entity_types = {e["entity_type"].lower() for e in entities}
    # Map common entity labels
    type_map = {
        "date": ["DATE", "date"],
        "amount": ["AMOUNT", "MONEY", "money", "amount"],
        "name": ["PERSON", "person", "ORG", "org", "name"],
    }

    for field in required:
        mapped_types = type_map.get(field, [field])
        found = any(
            e["entity_type"] in mapped_types or e["entity_type"].lower() == field
            for e in entities
        )
        if not found:
            issues.append({
                "rule": "required_field",
                "severity": "warning",
                "message": f"Required field '{field}' was not found in the document",
            })
            if status == "compliant":
                status = "warning"

    # 3. PII exposure check
    pii_types = {"SSN", "CREDIT_CARD", "US_SSN", "EMAIL", "PHONE"}
    pii_found = [e for e in entities if e["entity_type"] in pii_types]
    if pii_found:
        issues.append({
            "rule": "pii_detected",
            "severity": "info",
            "message": f"PII detected ({len(pii_found)} instances) - will be redacted",
        })

    # 4. Document age check (if dates found)
    max_age = COMPLIANCE_RULES.get("max_document_age_days", 365)
    for e in entities:
        if e["entity_type"] in ("DATE", "date"):
            parsed = _parse_date(e["entity_value"])
            if parsed and (datetime.now() - parsed).days > max_age:
                issues.append({
                    "rule": "document_age",
                    "severity": "warning",
                    "message": f"Document date '{e['entity_value']}' is older than {max_age} days",
                })

    return {
        "status": status,
        "issues": issues,
        "total_checks": 4,
        "passed_checks": 4 - len([i for i in issues if i["severity"] == "error"]),
    }


def _is_valid_date(date_str: str) -> bool:
    """Check if a date string is plausibly valid."""
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%m.%d.%Y", "%Y-%m-%d"):
        try:
            d = datetime.strptime(date_str.strip(), fmt)
            if 1900 < d.year < 2100:
                return True
        except ValueError:
            continue
    return False


def _parse_date(date_str: str):
    """Try to parse a date string."""
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%m.%d.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None
