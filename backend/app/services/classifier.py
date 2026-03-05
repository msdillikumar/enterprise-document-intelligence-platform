"""
Auto Document Classification Service
Classifies documents into types based on extracted text and entities.

Types:
  - invoice: Contains invoice numbers, amounts, vendor info
  - purchase_order: Contains PO numbers, order details
  - contract: Contains legal terms, signatures, agreement language
  - receipt: Contains receipt numbers, payment details, short format
  - report: Contains analysis, summary, findings
  - unknown: Cannot determine type

Methods:
  1. Keyword/pattern matching (fast, reliable)
  2. Entity-based classification (uses extracted entities)
"""

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ── Classification Patterns ──────────────────────────────────────────

CLASSIFICATION_PATTERNS = {
    "invoice": {
        "keywords": [
            r'\binvoice\b', r'\binv[\-#]', r'\bbill\s+to\b', r'\bship\s+to\b',
            r'\bdue\s+date\b', r'\bpayment\s+terms?\b', r'\btax\s+invoice\b',
            r'\bgst\s+invoice\b', r'\bproforma\b', r'\bbalance\s+due\b',
            r'\bamount\s+due\b', r'\binvoice\s+(no|number|#|date)\b',
        ],
        "entity_types": ["INVOICE_NUMBER", "TOTAL_AMOUNT", "VENDOR_NAME", "TAX_AMOUNT"],
        "weight": 1.0,
    },
    "purchase_order": {
        "keywords": [
            r'\bpurchase\s+order\b', r'\bP\.?O\.?\s*(no|number|#)\b',
            r'\border\s+(no|number|#|date)\b', r'\bquotation\b',
            r'\brequisition\b', r'\bprocurement\b', r'\bdelivery\s+date\b',
        ],
        "entity_types": ["PO_NUMBER", "ORDER_NUMBER"],
        "weight": 1.0,
    },
    "contract": {
        "keywords": [
            r'\bagreement\b', r'\bcontract\b', r'\bterms\s+and\s+conditions\b',
            r'\bwhereas\b', r'\bhereby\b', r'\bparties\b', r'\beffective\s+date\b',
            r'\btermination\b', r'\bconfidential\b', r'\bnon[\-\s]disclosure\b',
            r'\bliability\b', r'\bindemnif\b', r'\bgoverning\s+law\b',
            r'\bwaiver\b', r'\bsignature\b', r'\bwit+ness\b',
        ],
        "entity_types": [],
        "weight": 0.8,
    },
    "receipt": {
        "keywords": [
            r'\breceipt\b', r'\bpayment\s+received\b', r'\btransaction\s+(id|no|number)\b',
            r'\bpaid\b', r'\bchange\s+due\b', r'\bcash\s+tendered\b',
            r'\bthank\s+you\b.*\bpurchase\b', r'\bsubtotal\b',
        ],
        "entity_types": ["RECEIPT_NUMBER"],
        "weight": 0.9,
    },
    "report": {
        "keywords": [
            r'\breport\b', r'\banalysis\b', r'\bfindings\b', r'\bsummary\b',
            r'\bconclusion\b', r'\brecommendation\b', r'\bexecutive\s+summary\b',
            r'\bfiscal\s+year\b', r'\bquarterly\b', r'\bannual\b',
            r'\baudit\s+report\b', r'\bfinancial\s+statement\b',
        ],
        "entity_types": [],
        "weight": 0.7,
    },
}


def classify_document(text: str, entities: List[Dict]) -> Dict[str, Any]:
    """
    Classify a document based on its text content and extracted entities.

    Returns:
        {
            "document_type": str,
            "confidence": float,
            "scores": dict,  # per-type scores
            "matched_keywords": list,
            "method": "keyword_entity_hybrid"
        }
    """
    text_lower = text.lower() if text else ""
    scores = {}
    all_matched = {}

    for doc_type, config in CLASSIFICATION_PATTERNS.items():
        score = 0.0
        matched_keywords = []

        # Keyword matching
        for pattern in config["keywords"]:
            matches = re.findall(pattern, text_lower)
            if matches:
                score += len(matches) * 1.0
                matched_keywords.append(pattern)

        # Entity-type matching (stronger signal)
        entity_types = set(e["entity_type"].upper() for e in entities)
        for etype in config["entity_types"]:
            if etype in entity_types:
                score += 3.0  # Entity match is a strong signal

        # Apply type weight
        score *= config["weight"]
        scores[doc_type] = round(score, 2)
        all_matched[doc_type] = matched_keywords

    # Determine winner
    if not scores or max(scores.values()) == 0:
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "scores": scores,
            "matched_keywords": [],
            "method": "keyword_entity_hybrid",
        }

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Normalize confidence to 0-1
    total_score = sum(scores.values())
    confidence = best_score / total_score if total_score > 0 else 0
    confidence = min(confidence, 1.0)

    return {
        "document_type": best_type,
        "confidence": round(confidence, 3),
        "scores": scores,
        "matched_keywords": all_matched.get(best_type, []),
        "method": "keyword_entity_hybrid",
    }
