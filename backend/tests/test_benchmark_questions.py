import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

SAMPLE_SOIL = {
    "ph": {"value": 6.8},
    "nitrogen": {"value": 180.0, "unit": "kg/ha"},
    "phosphorus": {"value": 14.0, "unit": "kg/ha"},
    "potassium": {"value": 290.0, "unit": "kg/ha"},
    "organic_carbon": {"value": 0.45, "unit": "%"},
    "electrical_conductivity": {"value": 0.5, "unit": "dS/m"},
    "zinc": {"value": 0.4, "unit": "ppm"},
    "iron": {"value": 4.0, "unit": "ppm"},
    "sulphur": {"value": 8.0, "unit": "ppm"},
}

SAMPLE_PREVIOUS_WINDOW = {
    "recommendation": "YES",
    "apply_today": "GO",
    "reason": "Clear skies and moderate wind (< 15 km/h).",
    "application_type": "foliar",
    "morning_window": "06:00 - 09:00: Favorable (Temp 24°C, Wind 8 km/h, Rain 5%)",
    "evening_window": "16:30 - 18:30: Ideal for foliar spray (Temp 28°C, Wind 9 km/h, Rain 0%)",
}

@pytest.mark.asyncio
async def test_benchmark_q1_which_fertilizer_suitable():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "Which fertilizer is suitable for my crop?",
                "session_id": "test_bench_1",
                "soil": SAMPLE_SOIL,
                "selected_crop": "Tomato",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "fertilizer" in data["answer"].lower() or "urea" in data["answer"].lower() or "dap" in data["answer"].lower()
        assert "not recorded" not in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q2_which_crop_should_i_grow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "Which crop should I grow according to my soil?",
                "session_id": "test_bench_2",
                "soil": SAMPLE_SOIL,
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "crop" in data["answer"].lower()
        assert "not available" not in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q3_can_i_spray_fertilizer_this_evening():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "Can I spray fertilizer this evening?",
                "session_id": "test_bench_3",
                "soil": SAMPLE_SOIL,
                "selected_crop": "Tomato",
                "previous_application_window": SAMPLE_PREVIOUS_WINDOW,
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "evening" in data["answer"].lower() or "spray" in data["answer"].lower() or "window" in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q4_what_is_the_deficiency_in_my_soil():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "What is the deficiency in my soil?",
                "session_id": "test_bench_4",
                "soil": SAMPLE_SOIL,
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nitrogen" in data["answer"].lower()
        assert "low" in data["answer"].lower() or "deficient" in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q5_which_organic_fertilizer_can_i_use():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "Which organic fertilizer can I use?",
                "session_id": "test_bench_5",
                "soil": SAMPLE_SOIL,
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "organic" in data["answer"].lower() or "fym" in data["answer"].lower() or "vermicompost" in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q6_why_is_nitrogen_low():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "Why is nitrogen low in my soil?",
                "session_id": "test_bench_6",
                "soil": SAMPLE_SOIL,
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nitrogen" in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q7_how_to_improve_organic_carbon():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "What should I do to improve organic carbon?",
                "session_id": "test_bench_7",
                "soil": SAMPLE_SOIL,
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "carbon" in data["answer"].lower() or "organic" in data["answer"].lower() or "fym" in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q8_is_crop_suitable():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "Is Tomato suitable for this soil?",
                "session_id": "test_bench_8",
                "soil": SAMPLE_SOIL,
                "selected_crop": "Tomato",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tomato" in data["answer"].lower()

@pytest.mark.asyncio
async def test_benchmark_q9_what_should_i_do_next():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "What should I do next?",
                "session_id": "test_bench_9",
                "soil": SAMPLE_SOIL,
                "selected_crop": "Tomato",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["answer"]) > 20

@pytest.mark.asyncio
async def test_benchmark_q10_can_i_use_alternative_fertilizer():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat",
            json={
                "message": "Can I use an alternative fertilizer?",
                "session_id": "test_bench_10",
                "soil": SAMPLE_SOIL,
                "selected_crop": "Tomato",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["answer"]) > 20
