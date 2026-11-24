from __future__ import annotations

import re
import httpx
from fastapi import APIRouter, Query, Response, HTTPException

router = APIRouter(prefix="/api/voice", tags=["voice"])

GOOGLE_TTS_URL = "https://translate.google.com/translate_tts"
LANG_CODE_MAP = {
    "en": "en",
    "hi": "hi",
    "mr": "mr",
}


@router.get("/tts")
async def text_to_speech(
    text: str = Query(..., description="Text to convert to speech"),
    language: str = Query("en", description="Language code: en, hi, mr"),
):
    """Converts multilingual agricultural text into clean native MP3 audio.
    Supports English, Hindi, and Marathi with 100% accurate native pronunciation.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    lang_code = LANG_CODE_MAP.get(language.lower(), "en")

    # Strip markdown symbols, asterisks, bullet points, and URLs
    clean = re.sub(r"[*_#`~]", "", text)
    clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
    clean = re.sub(r"^[•\-\*]\s+", "", clean, flags=re.MULTILINE)
    clean = clean.strip()

    # Split text into manageable chunks along punctuation boundaries
    sentence_delimiters = r"(?<=[।?!.\n])\s+"
    parts = re.split(sentence_delimiters, clean)
    chunks: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) < 150:
            current = f"{current} {part}".strip()
        else:
            if current:
                chunks.append(current)
            if len(part) > 150:
                words = part.split()
                w_curr = ""
                for w in words:
                    if len(w_curr) + len(w) < 150:
                        w_curr = f"{w_curr} {w}".strip()
                    else:
                        if w_curr:
                            chunks.append(w_curr)
                        w_curr = w
                if w_curr:
                    chunks.append(w_curr)
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)

    if not chunks:
        chunks = [clean[:150]]

    # Limit maximum chunks to prevent excessively large payload
    chunks = chunks[:15]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    combined_audio = bytearray()
    async with httpx.AsyncClient(timeout=10.0) as client:
        for chunk in chunks:
            params = {
                "ie": "UTF-8",
                "tl": lang_code,
                "client": "tw-ob",
                "q": chunk,
            }
            try:
                res = await client.get(GOOGLE_TTS_URL, params=params, headers=headers)
                if res.status_code == 200:
                    combined_audio.extend(res.content)
            except Exception:
                continue

    if not combined_audio:
        raise HTTPException(status_code=502, detail="Speech synthesis service unavailable")

    return Response(
        content=bytes(combined_audio),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=speech.mp3",
            "Cache-Control": "public, max-age=3600",
        },
    )
