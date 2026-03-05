"""
Anomaly Detection Module
Detects anomalous patterns in documents using statistical methods.

Techniques:
  - Isolation Forest (sklearn) for multivariate anomaly detection
  - Z-score analysis for individual feature outliers
  - Rule-based checks for domain-specific anomalies
  - GST mismatch detection
  - Duplicate invoice detection
  - Unusual amount detection

IPO Format:
  Input  : OCR result, extracted entities, confidence scores
  Process: Statistical anomaly scoring + rule-based flags
  Output : anomaly report with scores, flags, and explanations
"""

import logging
import re
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ── Anomaly Feature Construction ─────────────────────────────────────

def _build_document_features(
    text: str,
    ocr_result: Dict,
    entities: List[Dict],
    confidence: Dict,
) -> Dict[str, float]:
    """Build feature dictionary for anomaly detection."""
    word_count = ocr_result.get("word_count", 0)
    ocr_conf = ocr_result.get("ocr_confidence", 0)
    entity_count = len(entities)

    # Compute features
    features = {
        "ocr_confidence": ocr_conf,
        "word_count": word_count,
        "entity_count": entity_count,
        "entity_density": entity_count / max(word_count, 1) * 100,
        "avg_entity_confidence": np.mean([e.get("confidence", 0.5) for e in entities]) if entities else 0,
        "pii_ratio": sum(1 for e in entities if e.get("is_pii")) / max(entity_count, 1),
        "text_length": len(text),
        "unique_entity_types": len(set(e["entity_type"] for e in entities)) if entities else 0,
        "overall_confidence": confidence.get("overall_score", 0),
        "line_count": text.count("\n") + 1 if text else 0,
        "special_char_ratio": sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(len(text), 1),
        "digit_ratio": sum(1 for c in text if c.isdigit()) / max(len(text), 1),
        "uppercase_ratio": sum(1 for c in text if c.isupper()) / max(len(text), 1),
    }
    return features


# ── Statistical Anomaly Detection ────────────────────────────────────

# Reference statistics (based on typical invoice/document distributions)
REFERENCE_STATS = {
    "ocr_confidence": {"mean": 70.0, "std": 20.0, "min": 10, "max": 99},
    "word_count": {"mean": 150, "std": 100, "min": 5, "max": 2000},
    "entity_count": {"mean": 10, "std": 8, "min": 1, "max": 50},
    "entity_density": {"mean": 5.0, "std": 3.0, "min": 0.5, "max": 20},
    "avg_entity_confidence": {"mean": 0.7, "std": 0.15, "min": 0.2, "max": 1.0},
    "pii_ratio": {"mean": 0.3, "std": 0.2, "min": 0.0, "max": 1.0},
    "text_length": {"mean": 800, "std": 600, "min": 20, "max": 10000},
    "special_char_ratio": {"mean": 0.15, "std": 0.08, "min": 0.0, "max": 0.5},
    "digit_ratio": {"mean": 0.12, "std": 0.08, "min": 0.0, "max": 0.5},
    "uppercase_ratio": {"mean": 0.10, "std": 0.08, "min": 0.0, "max": 0.6},
}


def _compute_z_scores(features: Dict[str, float]) -> Dict[str, float]:
    """Compute z-scores for each feature against reference distributions."""
    z_scores = {}
    for fname, fval in features.items():
        ref = REFERENCE_STATS.get(fname)
        if ref and ref["std"] > 0:
            z = (fval - ref["mean"]) / ref["std"]
            z_scores[fname] = round(z, 3)
    return z_scores


def _isolation_forest_score(features: Dict[str, float]) -> float:
    """
    Simplified Isolation Forest-inspired anomaly score.
    Uses average path length approximation.
    Score in [0, 1]: closer to 1 = more anomalous.
    """
    anomaly_contributions = []

    for fname, fval in features.items():
        ref = REFERENCE_STATS.get(fname)
        if not ref:
            continue

        # Normalise to [0, 1] based on reference range
        range_size = ref["max"] - ref["min"]
        if range_size <= 0:
            continue

        normalised = (fval - ref["min"]) / range_size
        # Distance from expected center (0.5)
        deviation = abs(normalised - 0.5) * 2  # scale to [0, 1]
        deviation = min(deviation, 1.5)  # cap extreme outliers

        anomaly_contributions.append(deviation)

    if not anomaly_contributions:
        return 0.0

    # Average deviation as anomaly score
    raw = np.mean(anomaly_contributions)
    # Apply sigmoid-like transformation for smoother output
    score = 1.0 / (1.0 + np.exp(-5.0 * (raw - 0.6)))
    return round(float(score), 4)


# ── Rule-Based Anomaly Checks ────────────────────────────────────────

def _rule_based_checks(
    text: str,
    ocr_result: Dict,
    entities: List[Dict],
    features: Dict[str, float],
) -> List[Dict]:
    """Domain-specific anomaly rules."""
    flags = []

    # R1: Extremely low OCR confidence
    if features["ocr_confidence"] < 20:
        flags.append({
            "rule": "extremely_low_ocr",
            "severity": "high",
            "message": f"OCR confidence is critically low ({features['ocr_confidence']:.1f}%)",
            "recommendation": "Document may be corrupted, heavily degraded, or non-textual",
        })

    # R2: No entities extracted
    if features["entity_count"] == 0:
        flags.append({
            "rule": "no_entities",
            "severity": "high",
            "message": "No entities could be extracted from the document",
            "recommendation": "Verify document contains structured information",
        })

    # R3: Suspiciously high PII density
    if features["pii_ratio"] > 0.7 and features["entity_count"] > 5:
        flags.append({
            "rule": "high_pii_density",
            "severity": "medium",
            "message": f"Unusually high PII density ({features['pii_ratio']:.0%})",
            "recommendation": "Document may contain sensitive data dump. Review carefully.",
        })

    # R4: Extremely short text
    if features["text_length"] < 30:
        flags.append({
            "rule": "minimal_text",
            "severity": "medium",
            "message": "Document contains very little text",
            "recommendation": "May be a blank page, image-only, or header-only document",
        })

    # R5: High repetition (duplicate lines)
    if text:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) > 5:
            unique = set(lines)
            repetition = 1 - len(unique) / len(lines)
            if repetition > 0.5:
                flags.append({
                    "rule": "high_repetition",
                    "severity": "medium",
                    "message": f"High text repetition detected ({repetition:.0%})",
                    "recommendation": "May indicate template, auto-generated, or corrupted content",
                })

    # R6: Unusual character distribution
    if features["special_char_ratio"] > 0.35:
        flags.append({
            "rule": "unusual_chars",
            "severity": "low",
            "message": f"High special character ratio ({features['special_char_ratio']:.0%})",
            "recommendation": "Document may contain encoded data or OCR artefacts",
        })

    # R7: All-uppercase document (possible scan artefact)
    if features["uppercase_ratio"] > 0.4 and features["word_count"] > 20:
        flags.append({
            "rule": "mostly_uppercase",
            "severity": "low",
            "message": "Document is predominantly uppercase text",
            "recommendation": "May be a typed form or OCR artefact",
        })

    # R8: Date in the future
    for e in entities:
        if e["entity_type"] == "DATE":
            parsed = _try_parse_date(e["entity_value"])
            if parsed and parsed > datetime.now():
                flags.append({
                    "rule": "future_date",
                    "severity": "medium",
                    "message": f"Future date detected: {e['entity_value']}",
                    "recommendation": "Verify document authenticity – dates in the future are unusual",
                })

    # R9: GST/Tax Mismatch Detection
    gst_flags = _check_gst_mismatch(entities, text)
    flags.extend(gst_flags)

    # R10: Unusual Amount Detection
    amount_flags = _check_unusual_amounts(entities)
    flags.extend(amount_flags)

    # R11: Duplicate Invoice Number Pattern
    inv_flags = _check_duplicate_invoice_patterns(entities)
    flags.extend(inv_flags)

    return flags


def _try_parse_date(date_str: str):
    """Try to parse a date string."""
    from datetime import datetime
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m.%d.%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


# ── Enhanced Anomaly Detection Helpers ────────────────────────────────

def _parse_amount(val: str) -> Optional[float]:
    """Parse a monetary amount string to float."""
    try:
        cleaned = re.sub(r'[^\d.\-,]', '', str(val))
        cleaned = cleaned.replace(',', '')
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _check_gst_mismatch(entities: List[Dict], text: str) -> List[Dict]:
    """
    Check if GST/Tax amounts are consistent with totals.
    Common GST rates: 5%, 12%, 18%, 28% (India), or other flat rates.
    """
    flags = []
    amounts = []
    tax_amounts = []
    total_amounts = []

    for e in entities:
        etype = e["entity_type"].upper()
        val = _parse_amount(e["entity_value"])
        if val is None:
            continue
        if etype in ("AMOUNT", "SUBTOTAL"):
            amounts.append(val)
        elif etype in ("TAX_AMOUNT", "GST", "TAX", "CGST", "SGST", "IGST"):
            tax_amounts.append(val)
        elif etype in ("TOTAL_AMOUNT", "TOTAL", "GRAND_TOTAL"):
            total_amounts.append(val)

    # Check if tax + subtotal ≈ total
    if amounts and tax_amounts and total_amounts:
        subtotal = max(amounts)
        tax = sum(tax_amounts)
        total = max(total_amounts)
        expected_total = subtotal + tax

        if total > 0 and abs(expected_total - total) / total > 0.02:  # > 2% discrepancy
            flags.append({
                "rule": "gst_mismatch",
                "severity": "high",
                "message": f"Tax calculation mismatch: subtotal ({subtotal:.2f}) + tax ({tax:.2f}) = {expected_total:.2f}, but total is {total:.2f}",
                "recommendation": "Verify GST/tax calculation. Discrepancy may indicate tampering or calculation error.",
            })

    # Check if tax rate is unusual
    if amounts and tax_amounts:
        subtotal = max(amounts)
        tax = sum(tax_amounts)
        if subtotal > 0:
            tax_rate = (tax / subtotal) * 100
            standard_rates = [5, 12, 18, 28, 0, 10, 15, 20, 25]
            closest = min(standard_rates, key=lambda r: abs(r - tax_rate))
            if abs(tax_rate - closest) > 2:
                flags.append({
                    "rule": "unusual_tax_rate",
                    "severity": "medium",
                    "message": f"Unusual tax rate detected: {tax_rate:.1f}% (nearest standard: {closest}%)",
                    "recommendation": "Verify tax rate matches applicable GST/VAT slab.",
                })

    return flags


def _check_unusual_amounts(entities: List[Dict]) -> List[Dict]:
    """Detect unusual amount patterns (round numbers, extreme values)."""
    flags = []
    parsed_amounts = []

    for e in entities:
        if e["entity_type"].upper() in ("AMOUNT", "TOTAL_AMOUNT", "TOTAL", "SUBTOTAL", "GRAND_TOTAL"):
            val = _parse_amount(e["entity_value"])
            if val is not None and val > 0:
                parsed_amounts.append(val)

    if not parsed_amounts:
        return flags

    # Check for suspiciously round amounts
    for amt in parsed_amounts:
        if amt >= 1000 and amt == int(amt) and amt % 1000 == 0:
            flags.append({
                "rule": "round_amount",
                "severity": "low",
                "message": f"Suspiciously round amount: {amt:.2f}",
                "recommendation": "Round amounts on invoices may warrant additional verification.",
            })
            break  # Only flag once

    # Check for extremely high amounts
    if parsed_amounts:
        max_amt = max(parsed_amounts)
        if max_amt > 1_000_000:
            flags.append({
                "rule": "high_value_document",
                "severity": "medium",
                "message": f"High-value document detected: {max_amt:,.2f}",
                "recommendation": "High-value transactions should receive additional review and approval.",
            })

    return flags


def _check_duplicate_invoice_patterns(entities: List[Dict]) -> List[Dict]:
    """Check for duplicate or sequential invoice numbers in the same document."""
    flags = []
    invoice_numbers = []

    for e in entities:
        if e["entity_type"].upper() in ("INVOICE_NUMBER", "INVOICE_NO", "INV_NUMBER"):
            invoice_numbers.append(e["entity_value"].strip())

    if len(invoice_numbers) > 1:
        unique = set(invoice_numbers)
        if len(unique) < len(invoice_numbers):
            flags.append({
                "rule": "duplicate_invoice_in_doc",
                "severity": "high",
                "message": f"Multiple identical invoice numbers found in the same document: {list(unique)}",
                "recommendation": "Duplicate invoice numbers may indicate data entry error or duplication.",
            })

        # Check for sequential patterns (e.g., INV-001, INV-002)
        nums = []
        for inv in invoice_numbers:
            match = re.search(r'(\d+)$', inv)
            if match:
                nums.append(int(match.group(1)))
        if len(nums) > 1:
            nums.sort()
            if all(nums[i+1] - nums[i] == 1 for i in range(len(nums)-1)):
                flags.append({
                    "rule": "sequential_invoices",
                    "severity": "medium",
                    "message": f"Sequential invoice numbers detected: {invoice_numbers}",
                    "recommendation": "Sequential invoices in one document may indicate batch processing or testing data.",
                })

    return flags


# ═══════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════

def detect_anomalies(
    text: str,
    ocr_result: Dict,
    entities: List[Dict],
    confidence: Dict,
) -> Dict[str, Any]:
    """
    Run anomaly detection on a processed document.

    Returns:
      - anomaly_score: float [0-1], higher = more anomalous
      - is_anomalous: bool (score > threshold)
      - z_scores: per-feature z-scores
      - flags: rule-based anomaly flags
      - feature_values: computed features for inspection
    """
    # Build features
    features = _build_document_features(text, ocr_result, entities, confidence)

    # Statistical analysis
    z_scores = _compute_z_scores(features)
    isolation_score = _isolation_forest_score(features)

    # Rule-based checks
    flags = _rule_based_checks(text, ocr_result, entities, features)

    # Combine scores: weighted average of statistical + rule severity
    severity_weights = {"high": 0.3, "medium": 0.15, "low": 0.05}
    rule_penalty = sum(severity_weights.get(f["severity"], 0.05) for f in flags)
    combined_score = min(isolation_score + rule_penalty, 1.0)
    combined_score = round(combined_score, 4)

    # Threshold
    is_anomalous = combined_score > 0.5

    # Identify most anomalous features
    outlier_features = [
        {"feature": k, "z_score": v, "actual": round(features.get(k, 0), 4)}
        for k, v in sorted(z_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        if abs(v) > 1.5
    ][:5]

    verdict = "NORMAL"
    if combined_score > 0.7:
        verdict = "HIGHLY_ANOMALOUS"
    elif combined_score > 0.5:
        verdict = "ANOMALOUS"
    elif combined_score > 0.3:
        verdict = "SLIGHTLY_UNUSUAL"

    return {
        "anomaly_score": combined_score,
        "is_anomalous": is_anomalous,
        "verdict": verdict,
        "isolation_forest_score": isolation_score,
        "z_scores": z_scores,
        "outlier_features": outlier_features,
        "flags": flags,
        "flag_count": len(flags),
        "feature_values": {k: round(v, 4) for k, v in features.items()},
    }
