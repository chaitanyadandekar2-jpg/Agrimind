from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import soil, recommendation, weather, chat, voice

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app = FastAPI(
    title="AgriMind API",
    description="Multi-Agent AI Soil, Crop & Fertilizer Optimization System",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(soil.router)
app.include_router(recommendation.router)
app.include_router(weather.router)
app.include_router(chat.router)
app.include_router(voice.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "AgriMind API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
