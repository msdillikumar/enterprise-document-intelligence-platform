"""
Confidence Scoring & Explainability Module
Provides confidence scores for each extraction and explanations for why
entities were identified.
"""
from typing import List, Dict
from ..config import MIN_CONFIDENCE_THRESHOLD


def compute_confidence_scores(
    entities: List[Dict],
    ocr_confidence: float,
    text_length: int,
) -> Dict:
    """
    Compute overall and per-entity confidence scores.
    Factors:
      - OCR quality (text clarity)
      - Entity extraction confidence
      - Text completeness (word count)
      - Method reliability (regex > NER)
    """
    if not entities:
        return {
            "overall_score": 0.0,
            "grade": "F",
            "details": {},
            "explanation": "No entities were extracted from the document.",
        }

    # Weight factors
    ocr_weight = 0.3
    entity_weight = 0.5
    completeness_weight = 0.2

    # OCR score (normalized to 0-1)
    ocr_score = min(ocr_confidence / 100, 1.0)

    # Average entity confidence
    entity_scores = [e.get("confidence", 0.5) for e in entities]
    avg_entity_score = sum(entity_scores) / len(entity_scores)

    # Completeness score (heuristic based on text length)
    completeness = min(text_length / 500, 1.0)

    overall = (
        ocr_score * ocr_weight
        + avg_entity_score * entity_weight
        + completeness * completeness_weight
    )
    overall = round(min(overall, 1.0), 3)

    # Grade
    if overall >= 0.9:
        grade = "A"
    elif overall >= 0.75:
        grade = "B"
    elif overall >= 0.6:
        grade = "C"
    elif overall >= 0.4:
        grade = "D"
    else:
        grade = "F"

    # Per-entity details
    per_entity = {}
    for e in entities:
        etype = e["entity_type"]
        if etype not in per_entity:
            per_entity[etype] = {
                "count": 0,
                "avg_confidence": 0,
                "values": [],
            }
        per_entity[etype]["count"] += 1
        per_entity[etype]["avg_confidence"] += e.get("confidence", 0.5)
        per_entity[etype]["values"].append(e["entity_value"])

    for etype in per_entity:
        per_entity[etype]["avg_confidence"] = round(
            per_entity[etype]["avg_confidence"] / per_entity[etype]["count"], 3
        )

    return {
        "overall_score": overall,
        "grade": grade,
        "ocr_quality": round(ocr_score, 3),
        "entity_confidence": round(avg_entity_score, 3),
        "text_completeness": round(completeness, 3),
        "details": per_entity,
    }


# Note: generate_explainability() has been moved to app.services.explainability
# which uses SHAP-based feature attribution (v2 upgrade).
