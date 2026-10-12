"""
routers/documents.py — document upload + analysis endpoints (Phase 5D),
ALL requiring authentication (privacy/auth feature — see module docstring
in document_service.py for the raw-file-deletion behavior this enables).

Every endpoint here requires a valid user — document upload/analysis is
never available anonymously, by explicit requirement: legal documents can
contain names, addresses, financial details, and other sensitive personal
information that anonymous, unlinked access is not an acceptable fit for
(unlike a one-off text question, there's no safe "don't persist it at all"
option for a file that has to be stored somewhere to even be processed).
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app import config  # noqa: F401
from app.config import ALLOWED_UPLOAD_EXTENSIONS
from app.database import get_db
from app.deps import get_current_user
from app.models.document import DocumentAnalysis
from app.models.user import User
from app.services import document_service

from llm_client import LLMConfigError, LLMTruncatedError
from rag_engine import RAGEngineError

logger = logging.getLogger("legal_ai.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB — reasonable MVP cap, not a hard platform limit


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Supported types: "
                   f"{', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}",
        )

    # Opportunistic hygiene: remove any raw uploads that were never analyzed.
    # Must never block or fail the upload itself.
    try:
        document_service.purge_stale_uploads(db)
    except Exception:
        logger.exception("Stale-upload purge failed (upload continues)")

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
        record = document_service.create_document_record(
            db, document_id, file.filename, str(dest_path), user_id=current_user.id
        )
    except Exception:
        logger.exception("Failed to create document database record")
        raise HTTPException(status_code=500, detail="Document uploaded but could not be recorded.")

    return {
        "document_id": record.document_id,
        "filename": record.filename,
        "status": record.status,
    }


@router.post("/{document_id}/analyze")
def analyze(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return document_service.analyze_document(db, document_id, user_id=current_user.id)

    except document_service.DocumentUnavailableError:
        # The caller owns this document, but its original file is gone (already
        # processed and deleted, or purged as stale). Safe to say so — they own it.
        raise HTTPException(
            status_code=410,
            detail="The original file is no longer available (files are deleted after processing). Please upload the document again.",
        )

    except ValueError:
        # Covers BOTH "no such document" AND "exists but belongs to another
        # user" — document_service raises the same error for both on purpose,
        # so this endpoint can never be used to probe which document_ids
        # exist for other users (they look identical to nonexistent ones).
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
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Filtered by owner at the DATABASE level — never fetch every user's
    rows and filter afterward in Python or on the frontend."""
    try:
        rows = (
            db.query(DocumentAnalysis)
            .filter(DocumentAnalysis.user_id == current_user.id)
            .order_by(DocumentAnalysis.created_at.desc())
            .all()
        )
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
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = db.query(DocumentAnalysis).filter(DocumentAnalysis.document_id == document_id).first()
    except Exception:
        logger.exception("Database error while fetching document_id=%s", document_id)
        raise HTTPException(status_code=500, detail="Could not retrieve the requested document.")

    # 404 for both "doesn't exist" and "exists but isn't yours" — see the
    # matching comment in analyze() above for why these must be indistinguishable.
    if row is None or row.user_id != current_user.id:
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


@router.get("/{document_id}/report.pdf")
def export_document_report(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exports an analyzed document risk audit as a downloadable PDF.
    Only available if status is 'analyzed'; otherwise returns 409 Conflict.
    Deterministic in-memory generation; zero storage.
    """
    row = db.query(DocumentAnalysis).filter(DocumentAnalysis.document_id == document_id).first()
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found.")

    if row.status != "analyzed":
        raise HTTPException(
            status_code=409,
            detail=f"Document cannot be exported because its analysis status is '{row.status}'. Only analyzed documents have reports.",
        )

    doc_data = {
        "document_id": row.document_id,
        "filename": row.filename,
        "document_type": row.document_type,
        "status": row.status,
        "risk_score": row.risk_score,
        "risk_level": row.risk_level,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        **(row.full_result or {}),
    }

    try:
        from app.services import pdf_service
        pdf_bytes = pdf_service.generate_document_pdf(doc_data)
    except Exception:
        logger.exception("Failed to generate PDF for document_id=%s", document_id)
        raise HTTPException(status_code=500, detail="Could not generate document PDF report.")

    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    clean_id = document_id.replace("-", "")[:8]
    filename = f"document_report_{clean_id}_{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )

