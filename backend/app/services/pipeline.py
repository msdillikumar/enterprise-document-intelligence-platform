"""
Pipeline Orchestrator – v2
Runs the full document processing pipeline in sequence:
1. Encryption → 2. OCR → 3. LLM Entity Extraction → 4. Confidence →
5. SHAP Explainability → 6. Anomaly Detection → 7. Compliance →
8. Redaction → 9. Storage

IPO (Input → Process → Output):
  Input  : uploaded document (bytes + filename)
  Process: AES encryption, Tesseract OCR, Transformer-based LLM extraction,
           SHAP feature attribution, statistical anomaly detection,
           compliance checks, PII redaction
  Output : structured result with entities, scores, explanations, anomaly flags
"""
import time
import uuid
from pathlib import Path
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import UPLOAD_DIR, PROCESSED_DIR
from ..models import Document, ExtractedEntity
from .encryption import encrypt_file, decrypt_file
from .ocr import extract_text
from .llm_extractor import extract_entities
from .confidence import compute_confidence_scores
from .explainability import generate_explainability
from .anomaly import detect_anomalies
from .compliance import check_authenticity, check_compliance
from .redaction import redact_text, get_redacted_entities
from .classifier import classify_document  # type: ignore[import-not-found]
from .task_manager import init_task, update_task, complete_task  # type: ignore[import-not-found]


async def process_document(
    file_data: bytes,
    original_filename: str,
    db: AsyncSession,
    uploaded_by: int = None,
) -> Dict:
    """
    Execute the full processing pipeline for an uploaded document.
    """
    start_time = time.time()
    file_ext = Path(original_filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{file_ext}"

    # Create document record
    doc = Document(
        filename=unique_name,
        original_filename=original_filename,
        file_type=file_ext,
        file_size=len(file_data),
        status="processing",
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    await db.flush()

    # Initialize progress tracking
    init_task(doc.id)

    try:
        # ─── Step 1: AES-256 Encryption ───
        update_task(doc.id, 0, "encrypting")
        upload_path = UPLOAD_DIR / unique_name
        upload_path.write_bytes(file_data)
        encrypted_path = PROCESSED_DIR / f"{unique_name}.enc"
        encrypt_file(str(upload_path), str(encrypted_path))
        doc.encrypted_path = str(encrypted_path)
        upload_path.unlink(missing_ok=True)

        # ─── Step 2: OCR Text Extraction (PaddleOCR / Tesseract) ───
        update_task(doc.id, 1, "ocr_extraction")
        ocr_result = extract_text(file_data, file_ext)
        raw_text = ocr_result.get("text", "")
        doc.raw_text = raw_text
        doc.ocr_quality = ocr_result.get("quality", {})
        doc.layout_data = ocr_result.get("layout_blocks", [])

        # ─── Step 3: LLM Entity Extraction (Gen-AI) ───
        update_task(doc.id, 2, "entity_extraction")
        entities = extract_entities(raw_text)
        # Track which method was used
        methods_used = set(e.get("extraction_method", "unknown") for e in entities)
        primary_method = "llm_local" if "llm_local" in methods_used else (
            "huggingface_ner" if "huggingface_ner" in methods_used else "regex_pattern"
        )
        doc.extraction_method = primary_method

        # ─── Step 4: Auto Document Classification ───
        update_task(doc.id, 3, "classification")
        classification = classify_document(raw_text, entities)
        doc.document_type = classification["document_type"]

        # ─── Step 5: Confidence Scoring ───
        update_task(doc.id, 4, "confidence_scoring")
        confidence = compute_confidence_scores(
            entities=entities,
            ocr_confidence=ocr_result.get("ocr_confidence", 0),
            text_length=len(raw_text),
        )
        doc.confidence_score = confidence["overall_score"]
        doc.confidence_details = confidence

        # ─── Step 6: SHAP Explainability ───
        update_task(doc.id, 5, "explainability")
        explainability = generate_explainability(
            entities, ocr_result, confidence, text=raw_text
        )
        doc.explainability = explainability

        # ─── Step 7: Anomaly Detection ───
        update_task(doc.id, 6, "anomaly_detection")
        anomaly_result = detect_anomalies(raw_text, ocr_result, entities, confidence)
        doc.anomaly_score = anomaly_result["anomaly_score"]
        doc.anomaly_details = anomaly_result

        # ─── Step 8: Authenticity & Compliance Check ───
        update_task(doc.id, 7, "compliance_check")
        auth_result = check_authenticity(raw_text, ocr_result, entities)
        doc.is_authentic = auth_result["is_authentic"]

        compliance_result = check_compliance(raw_text, entities, file_ext)
        doc.compliance_status = compliance_result["status"]
        doc.compliance_details = {
            "authenticity": auth_result,
            "compliance": compliance_result,
        }

        # ─── Step 9: Sensitive Data Redaction ───
        update_task(doc.id, 8, "pii_redaction")
        entities = get_redacted_entities(entities)
        redaction_result = redact_text(raw_text, entities)
        doc.redacted_text = redaction_result["redacted_text"]

        # ─── Step 10: Store Entities in Database ───
        update_task(doc.id, 9, "storage")
        for entity in entities:
            db_entity = ExtractedEntity(
                document_id=doc.id,
                entity_type=entity["entity_type"],
                entity_value=entity["entity_value"],
                redacted_value=entity.get("redacted_value"),
                confidence=entity.get("confidence"),
                start_pos=entity.get("start_pos"),
                end_pos=entity.get("end_pos"),
                is_pii=entity.get("is_pii", False),
                extraction_method=entity.get("extraction_method"),
            )
            db.add(db_entity)

        # Finalize
        doc.status = "completed"
        proc_time = int((time.time() - start_time) * 1000)
        doc.processing_time_ms = proc_time

        await db.commit()
        await db.refresh(doc)

        complete_task(doc.id, success=True)

        return {
            "success": True,
            "document_id": doc.id,
            "filename": original_filename,
            "status": "completed",
            "processing_time_ms": proc_time,
            "pipeline_results": {
                "encryption": {"status": "encrypted", "method": "AES-256-Fernet"},
                "ocr": {
                    "method": ocr_result.get("method"),
                    "confidence": ocr_result.get("ocr_confidence"),
                    "word_count": ocr_result.get("word_count"),
                    "quality": ocr_result.get("quality", {}),
                    "layout_blocks_count": len(ocr_result.get("layout_blocks", [])),
                },
                "entity_extraction": {
                    "method": primary_method,
                    "entities_extracted": len(entities),
                },
                "classification": {
                    "document_type": classification["document_type"],
                    "confidence": classification["confidence"],
                    "method": classification["method"],
                },
                "confidence": confidence,
                "explainability": {
                    "method": "shap_perturbation",
                    "summary": explainability["summary"],
                    "global_feature_importance": explainability.get(
                        "global_feature_importance", {}
                    ),
                },
                "anomaly_detection": {
                    "score": anomaly_result["anomaly_score"],
                    "verdict": anomaly_result["verdict"],
                    "flags": len(anomaly_result.get("flags", [])),
                },
                "authenticity": auth_result["verdict"],
                "compliance": compliance_result["status"],
                "pii_redacted": redaction_result["pii_count"],
            },
        }

    except Exception as e:
        doc.status = "failed"
        doc.error_message = str(e)
        doc.processing_time_ms = int((time.time() - start_time) * 1000)
        await db.commit()

        return {
            "success": False,
            "document_id": doc.id,
            "filename": original_filename,
            "status": "failed",
            "error": str(e),
        }
