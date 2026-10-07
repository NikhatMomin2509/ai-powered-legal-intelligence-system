"""
routers/documents.py — document upload + analysis endpoints (Phase 5D).
Thin layer: validation + HTTP concerns only, all real logic lives in
app.services.document_service.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import config  # noqa: F401
from app.config import ALLOWED_UPLOAD_EXTENSIONS
from app.database import get_db
from app.models.document import DocumentAnalysis
from app.services import document_service

from llm_client import LLMConfigError, LLMTruncatedError
from rag_engine import RAGEngineError

logger = logging.getLogger("legal_ai.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB — reasonable MVP cap, not a hard platform limit


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Supported types: "
                   f"{', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    document_id = str(uuid.uuid4())

    try:
        dest_path = document_service.save_uploaded_file(contents, document_id, file.filename)
    except Exception:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(status_code=500, detail="Could not save the uploaded file.")

    try:
        record = document_service.create_document_record(db, document_id, file.filename, str(dest_path))
    except Exception:
        logger.exception("Failed to create document database record")
        raise HTTPException(status_code=500, detail="Document uploaded but could not be recorded.")

    return {
        "document_id": record.document_id,
        "filename": record.filename,
        "status": record.status,
    }


@router.post("/{document_id}/analyze")
def analyze(document_id: str, db: Session = Depends(get_db)):
    try:
        return document_service.analyze_document(db, document_id)

    except ValueError:
        # covers document_service's "no document found" — not a request-
        # validation issue, this is a missing-resource case.
        raise HTTPException(status_code=404, detail="Document not found.")

    except RAGEngineError as e:
        logger.error("RAG engine unavailable during document analysis: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Document analysis could not be completed: the retrieval system is unavailable.",
        )

    except LLMConfigError as e:
        logger.error("LLM configuration error during document analysis: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Document analysis could not be completed: the language model is not configured.",
        )

    except LLMTruncatedError as e:
        logger.error("LLM response truncated during document analysis: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Document analysis could not be completed: a response was too long to process.",
        )

    except Exception:
        logger.exception("Unexpected error during document analysis")
        raise HTTPException(status_code=500, detail="Document analysis could not be completed.")


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    try:
        rows = db.query(DocumentAnalysis).order_by(DocumentAnalysis.created_at.desc()).all()
        return [
            {
                "document_id": r.document_id,
                "filename": r.filename,
                "document_type": r.document_type,
                "status": r.status,
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception:
        logger.exception("Database error while listing documents")
        raise HTTPException(status_code=500, detail="Could not retrieve document history.")


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    try:
        row = db.query(DocumentAnalysis).filter(DocumentAnalysis.document_id == document_id).first()
    except Exception:
        logger.exception("Database error while fetching document_id=%s", document_id)
        raise HTTPException(status_code=500, detail="Could not retrieve the requested document.")

    if row is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "document_id": row.document_id,
        "filename": row.filename,
        "document_type": row.document_type,
        "status": row.status,
        "risk_score": row.risk_score,
        "risk_level": row.risk_level,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        **(row.full_result or {}),
    }
