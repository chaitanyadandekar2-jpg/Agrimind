from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.pdf_service import extract_text
from app.services.soil_parser import parse_soil_text
from app.models.soil import SoilReport

router = APIRouter(prefix="/api/soil", tags=["soil"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))


@router.post("/upload", response_model=SoilReport)
async def upload_soil_report(file: UploadFile = File(...)) -> SoilReport:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF soil reports are supported right now.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{file.filename}")

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    try:
        text = extract_text(dest_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {exc}") from exc

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in this PDF (it may be a scanned image). "
            "OCR is not part of the current pipeline.",
        )

    return parse_soil_text(text)
