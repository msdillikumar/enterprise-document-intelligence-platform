"""Database models for documents, entities, users, and audit logs."""
import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base


# ═══════════════════════════════════════════════════════════════════════
#  User Model (RBAC)
# ═══════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    role = Column(String(50), default="user")  # admin, auditor, finance_user, compliance_officer, user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════
#  Audit Log Model
# ═══════════════════════════════════════════════════════════════════════

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(100), default="anonymous")
    action = Column(String(50), nullable=False)   # login, upload, view, search, download, delete, export
    resource_type = Column(String(50), default="")  # document, user, system
    resource_id = Column(String(100), default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String(50), default="")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ═══════════════════════════════════════════════════════════════════════
#  Document Model
# ═══════════════════════════════════════════════════════════════════════

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    upload_time = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(50), default="uploaded")  # uploaded, processing, completed, failed
    encrypted_path = Column(String(500))
    raw_text = Column(Text)
    redacted_text = Column(Text)
    confidence_score = Column(Float)
    confidence_details = Column(JSON)  # Per-entity confidence breakdown
    explainability = Column(JSON)       # SHAP-based explainability data
    is_authentic = Column(Boolean, default=None)
    compliance_status = Column(String(50))  # compliant, non_compliant, warning
    compliance_details = Column(JSON)
    anomaly_score = Column(Float)       # Anomaly detection score (0-1)
    anomaly_details = Column(JSON)      # Full anomaly report
    ocr_quality = Column(JSON)           # Scan quality metrics (DPI, skew, contrast)
    layout_data = Column(JSON)           # Layout blocks from PaddleOCR
    processing_time_ms = Column(Integer)
    error_message = Column(Text)
    extraction_method = Column(String(100))  # llm_local, huggingface_ner, regex_pattern
    document_type = Column(String(50), default="unknown")  # invoice, purchase_order, contract, receipt, report, unknown
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    entities = relationship("ExtractedEntity", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "upload_time": self.upload_time.isoformat() if self.upload_time else None,
            "status": self.status,
            "raw_text": self.raw_text,
            "redacted_text": self.redacted_text,
            "confidence_score": self.confidence_score,
            "confidence_details": self.confidence_details,
            "explainability": self.explainability,
            "is_authentic": self.is_authentic,
            "compliance_status": self.compliance_status,
            "compliance_details": self.compliance_details,
            "anomaly_score": self.anomaly_score,
            "anomaly_details": self.anomaly_details,
            "ocr_quality": self.ocr_quality,
            "layout_data": self.layout_data,
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
            "extraction_method": self.extraction_method,
            "document_type": self.document_type,
            "uploaded_by": self.uploaded_by,
            "entities": [e.to_dict() for e in self.entities] if self.entities else [],
        }


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    entity_type = Column(String(100))   # PERSON, DATE, MONEY, ORG, etc.
    entity_value = Column(Text)
    redacted_value = Column(Text)
    confidence = Column(Float)
    start_pos = Column(Integer)
    end_pos = Column(Integer)
    is_pii = Column(Boolean, default=False)
    extraction_method = Column(String(100))  # spacy, regex, pattern

    document = relationship("Document", back_populates="entities")

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "redacted_value": self.redacted_value,
            "confidence": self.confidence,
            "is_pii": self.is_pii,
            "extraction_method": self.extraction_method,
        }
