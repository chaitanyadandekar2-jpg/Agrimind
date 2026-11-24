"""Tests for the improved context-aware AgriMind Chat API."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_chat_with_crop_query_returns_scores():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Which crop should I grow according to my soil?",
            "session_id": "test_session_1",
            "soil": {
                "nitrogen": {"value": 180, "unit": "kg/ha"},
                "phosphorus": {"value": 15, "unit": "kg/ha"},
                "potassium": {"value": 260, "unit": "kg/ha"},
                "ph": {"value": 6.4},
                "organic_carbon": {"value": 0.45, "unit": "%"},
                "electrical_conductivity": {"value": 0.32, "unit": "dS/m"},
            },
            "season": "rabi",
            "language": "en",
        }
        res = await client.post("/api/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert data["crop_scores"] is not None
        assert len(data["crop_scores"]) > 0


@pytest.mark.asyncio
async def test_chat_detects_contradiction_when_asking_for_high_nutrient():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Should I add potassium fertilizer (MOP) to my field?",
            "session_id": "test_session_2",
            "soil": {
                "potassium": {"value": 350, "unit": "kg/ha"},
            },
            "language": "en",
        }
        res = await client.post("/api/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["contradiction_flag"] is not None
        assert "potassium" in data["contradiction_flag"].lower()


@pytest.mark.asyncio
async def test_chat_multi_turn_session_memory():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        session_id = "test_farmer_memory_session"

        # Turn 1
        res1 = await client.post(
            "/api/chat",
            json={
                "message": "What is the deficiency in my soil?",
                "session_id": session_id,
                "soil": {
                    "nitrogen": {"value": 180, "unit": "kg/ha"},
                    "zinc": {"value": 0.42, "unit": "ppm"},
                },
                "language": "en",
            },
        )
        assert res1.status_code == 200

        # Turn 2: Follow-up question referencing previous turn
        res2 = await client.post(
            "/api/chat",
            json={
                "message": "Which organic fertilizer can I use to fix that nitrogen?",
                "session_id": session_id,
                "soil": {
                    "nitrogen": {"value": 180, "unit": "kg/ha"},
                    "zinc": {"value": 0.42, "unit": "ppm"},
                },
                "language": "en",
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2["answer"]) > 0
