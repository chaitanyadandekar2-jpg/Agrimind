# AgriMind: Advanced Multi-Agent AI Agricultural Decision-Support Platform

AgriMind is an explainable, evidence-grounded, multi-agent Generative AI agricultural decision-support platform. It analyzes soil test reports (Soil Health Cards and private lab PDFs), evaluates multi-parameter crop suitability, recommends targeted fertilizers and organic amendments, retrieves authoritative agricultural research from ChromaDB via LangChain, and evaluates live meteorological and hourly spray windows to deliver actionable, trustworthy recommendations to farmers.

```
       Soil PDF Report
              ↓
  Deterministic Soil Extraction & Classification (PyMuPDF + Regex)
              ↓
    CrewAI Multi-Agent Orchestrator (Intent-Driven Conditional Routing)
     ├── Agent 1: Soil Analysis Agent (SHC Bands & Deficiency Assessment)
     ├── Agent 2: Crop Recommendation Agent (Multi-factor Suitability Scoring)
     ├── Agent 3: Fertilizer Optimization Agent (Chemical, Organic & Foliar)
     ├── Agent 4: Weather Intelligence Agent (Open-Meteo Daily + Hourly Windows)
     └── Agent 5: Agricultural Knowledge & RAG Agent (LangChain + ChromaDB)
              ↓
  Deterministic Validation & Contradiction Resolution
              ↓
  LangChain Explanation Layer (ChatOpenAI / Centralized Prompts / Session Memory)
              ↓
  React Farmer Dashboard (Soil Core, Suitability, Weather, Evidence & AI Chat)
```

---

## 1. Core Architecture & New Technologies

### LangChain Integration
- **Replaceable Chat Models**: Integrated through `ChatOpenAI` in `app/services/langchain_service.py`, supporting OpenAI models (e.g. `gpt-4o-mini`), Google Gemini endpoints via OpenAI compatibility, and local LLMs (Ollama / LM Studio) via `LLM_BASE_URL`.
- **Centralized Prompt Engineering**: Standardized agricultural system and human message prompt templates enforcing grounded explanations, strict prohibition of fabricated dosages, and natural citation attribution.
- **Conversational Memory**: Isolated per-session chat history (`InMemoryChatMessageHistory`) enabling farmers to ask follow-up questions without re-uploading documents or re-specifying location.
- **ChromaDB Retriever Interface**: `AgriMindChromaRetriever` implements the standard LangChain `BaseRetriever` interface with cosine similarity semantic retrieval and keyword-boosted reranking.
- **Structured Pydantic Schemas**: Structured output validation for explanation summaries, intent classification, and chat responses.

### CrewAI Multi-Agent System
Coordinated agricultural multi-agent architecture in `app/agents/crew_agents.py` and `app/agents/crew_orchestrator.py`:
1. **Soil Analysis Agent** (`Senior Agricultural Soil Chemist`): Interprets test metrics, classifies deficiencies against official Soil Health Card thresholds, flags pH acidity/alkalinity and organic carbon levels, and detects unmeasured parameters.
2. **Crop Recommendation Agent** (`Crop Agronomy & Suitability Specialist`): Evaluates crop suitability using deterministic scoring across pH, N, P, K, Organic Carbon, Electrical Conductivity (salinity), and seasonal fit.
3. **Fertilizer Optimization Agent** (`Plant Nutrition & Fertilizer Optimization Specialist`): Identifies targeted chemical fertilizers and organic soil amendments for LOW nutrients, distinguishes application methods (foliar vs soil), checks crop compatibility, and avoids over-application.
4. **Weather Intelligence Agent** (`Agricultural Meteorologist & Application Timing Advisor`): Analyzes live daily and hourly forecasts from Open-Meteo, distinguishing between soil application and foliar spraying windows (wind < 15 km/h, rain probability < 30-40%, morning/evening slots).
5. **Agricultural Knowledge & RAG Agent** (`Agricultural Extension Knowledge Researcher`): Retrieves authoritative research documents (CGIAR Soil Health Framework, ICAR guidelines) and grounds advice with exact source citations.

### Deterministic Agricultural Engine
- The LLM explains; it does **NOT** calculate.
- Calculations for nutrient deficiencies, crop scores, fertilizer selection, and weather application windows are executed in pure Python in `app/engine/`.
- Contradiction avoidance: explicitly detects and warns if a farmer asks to add a nutrient that is already HIGH in their soil.

---

## 2. Root Causes of Previous Chatbot Issues & Solutions

| Previous Flawed Response | Exact Code Root Cause | How AgriMind Fixes It |
| :--- | :--- | :--- |
| *"Your current temperature was not recorded in the uploaded report."* | `ChatRequest` lacked location/weather data, and `application_window=None` was hardcoded into the chat prompt. | Chat endpoint now takes location/coordinates, retrieves live Open-Meteo forecasts, and supplies weather context to the prompt. |
| *"Specific crop recommendations or crop scores are not available."* | `crop_scores=[]` was hardcoded in `chat.py`. | Chat router identifies crop queries and dynamically executes the Crop Recommendation Agent. |
| *"There is no active fertilizer application recommended for today."* | `fertilizer_options=[]` was hardcoded in `chat.py`. | Chat router identifies fertilizer queries and runs the Fertilizer Optimization Agent. |
| Spray timing questions failed or gave generic answers | Weather service only fetched daily aggregates, lacking hourly temperature and wind arrays. | Weather service now retrieves hourly forecast data and analyzes morning (06:00-10:00) and evening (16:00-19:00) spray windows. |
| Multi-turn conversation amnesia | Chat endpoint was stateless with no session ID or message history. | LangChain session memory maintains conversation context across multiple turns. |

---

## 3. Knowledge Base & Supported Crops

### Crops Evaluated
- **Tomato** (pH 6.0-6.8, high K & N response, sensitive to salinity EC > 1.5 dS/m)
- **Wheat** (pH 6.0-7.5, Rabi staple, moderate salinity tolerance up to 2.5 dS/m)
- **Rice (Paddy)** (pH 5.5-7.0, Kharif, high water demand)
- **Cotton** (pH 6.0-8.0, Kharif, salt-tolerant up to 3.0 dS/m)
- **Soybean** (pH 6.0-7.5, Kharif legume, biological nitrogen fixation)
- **Onion** (pH 6.0-7.0, Rabi, shallow-rooted, salt-sensitive EC > 1.2 dS/m)
- **Sugarcane** (pH 6.5-7.5, heavy nutrient & water consumer)
- **Chickpea / Gram** (pH 6.0-7.5, Rabi legume, low water requirement)

### Fertilizer & Amendment Knowledge
- **Chemical options**: Urea (46% N), Ammonium Sulphate (21% N, 24% S), Single Super Phosphate (SSP, 16% P2O5, 11% S), DAP (18-46-0), Muriate of Potash (MOP, 60% K2O), Sulphate of Potash (SOP, 50% K2O), Zinc Sulphate (ZnSO4), Ferrous Sulphate (FeSO4), Agricultural Gypsum, Elemental Sulphur.
- **Organic alternatives**: Farmyard Manure (FYM), Vermicompost, Green Manure (Dhaincha/Sunhemp), Rock Phosphate, Bone Meal, Wood Ash, Composted Banana Residue, Zinc-enriched FYM.
- **Application methods**: Soil/Basal incorporation, Foliar spraying, Fertigation, Pre-sowing organic incorporation.

---

## 4. Running AgriMind Locally

### Prerequisites
- Python 3.12
- Node.js (v18+)

### 1. Backend Setup
```bash
cd backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1    # On Windows
# source .venv/bin/activate     # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# (Re)build the ChromaDB knowledge base index
python -m app.rag.index_knowledge

# Run all 49 automated unit and integration tests
pytest

# Run the end-to-end PDF demo verification script
python ..\verify_setup.py

# Start the FastAPI backend server
uvicorn app.main:app --reload --port 8000
```
Swagger API documentation: `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Build production bundle
npm run build

# Start development server
npm run dev
```
Open `http://localhost:5173` in your browser.

### 3. Docker Deployment
```bash
docker compose up --build
```

---

## 5. API Endpoints

- `POST /api/soil/upload`: Uploads and parses soil PDF report into structured parameters.
- `POST /api/recommendation`: Full multi-agent recommendation (Soil, Crops, Fertilizers, Weather, RAG Evidence, Explanation).
- `POST /api/chat`: Context-aware conversational AI chat with intent routing, session memory, and contradiction detection.
- `GET /api/weather/forecast`: Live daily and hourly weather forecast with spray window analysis.
- `GET /health`: Health status endpoint.

---

## 6. Automated Test Suite (49 Tests)

All 49 tests pass with 100% success rate:
- `tests/test_application_window.py` (5 tests): Heavy rain, rain probability, wind speed, clear days.
- `tests/test_foliar_spray_window.py` (3 tests): Foliar spray wind limits (15 km/h), rain wash-off, morning/evening slots.
- `tests/test_crop_scorer.py` (3 tests): Soil matching, seasonal fit, case-insensitive lookup.
- `tests/test_fertilizer_optimizer.py` (8 tests): SHC rating bands, micronutrient critical levels, contradiction checks.
- `tests/test_soil_parser.py` (4 tests): Tolerance regex parsing, completeness scoring, micronutrient handling.
- `tests/test_chunker.py` (4 tests): Heading splitting, Q&A pair preservation, sliding window with overlap.
- `tests/test_i18n.py` (7 tests): English, Hindi, and Marathi phrase completeness and script validation.
- `tests/test_langchain_service.py` (3 tests): Structured context building, session memory isolation, multilingual fallback.
- `tests/test_crew_agents.py` (5 tests): 5 specialized agent definitions, roles, and structured task executions.
- `tests/test_crew_orchestrator.py` (4 tests): Intent classification and full workflow orchestration.
- `tests/test_chat_api.py` (3 tests): End-to-end chat API with crop queries, contradiction warnings, and multi-turn session memory.
