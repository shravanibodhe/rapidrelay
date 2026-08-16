# RapidRelay — Multilingual Disaster Triage Backend

RapidRelay is an emergency intake and triage backend built for disaster response in India (floods, cyclones, building collapses). Distress messages arrive in regional languages (**Hindi, Marathi, Tamil, Bengali, Hinglish**). The backend leverages **Claude (Sonnet 4.5)** to extract structured triage metadata, applies an **explainable keyword-heuristic severity boost**, and stores the incidents in SQLite for consumption by responder dashboards.

---

## Architecture & Features

- **Multilingual Intake**: Ingests raw emergency text messages in native Indian scripts or transliterated Latin (Hinglish).
- **Claude Sonnet 4.5 Extraction**: Extracts structured fields (`original_language`, `translated_text`, `location`, `severity`, `need_type`, `people_affected`, `summary`, `confidence`).
- **Explainable Severity Heuristics**: Deterministic rule-based scoring boost (+1 per matched critical keyword such as `trapped`, `unconscious`, `child`, `pregnant`, `collapsed`, `drowning`, capped at 5).
- **Forward-Only Lifecycle**: Enforces status progression: `new` ➔ `acknowledged` ➔ `dispatched` ➔ `resolved`.
- **Pre-Seeded Demo Data**: Includes realistic regional distress records for instant demos without rate-limiting.

---

## 1. Setup Instructions

### Prerequisites
- Python 3.10+ (Tested on Python 3.10 - 3.14)
- Pip

### Installation
From the project root or `/backend` directory:

```bash
cd backend
pip install -r requirements.txt
```

---

## 2. Configuration (`.env`)

Create a `.env` file in the `backend/` directory by copying `.env.example`:

```bash
cp .env.example .env
```

Set your Anthropic API Key:
```env
ANTHROPIC_API_KEY=sk-ant-api03-...your-actual-key-here...
DATABASE_URL=sqlite:///./rapidrelay.db
HOST=0.0.0.0
PORT=8000
```

> **Note**: If `ANTHROPIC_API_KEY` is not set or invalid when calling `POST /incidents`, the endpoint returns a clear, structured **HTTP 502 Bad Gateway** explaining the error so frontends can handle it gracefully.

---

## 3. Seed Demo Data

To populate the SQLite database with realistic Hindi, Tamil, Marathi, and Hinglish disaster incidents:

```bash
python seed_demo_data.py
```

---

## 4. Run the Development Server

From the `backend/` directory:

```bash
uvicorn main:app --reload --port 8000
```

Or from the workspace root:

```bash
uvicorn backend.main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

## 5. API Reference & Example cURL Commands

### A. Emergency Intake (`POST /incidents`)
Submit a raw distress text message in any Indian regional language.

```bash
curl -X POST "http://localhost:8000/incidents" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "मदद करो! हमारे घर में पानी भर गया है, 4 लोग छत पर फंसे हैं और एक बच्चा बीमार है। पटना राजेंद्र नगर।"
  }'
```

**Example Response (`201 Created`):**
```json
{
  "id": 1,
  "created_at": "2026-08-16T07:30:00Z",
  "original_language": "Hindi",
  "original_text": "मदद करो! हमारे घर में पानी भर गया है, 4 लोग छत पर फंसे हैं और एक बच्चा बीमार है। पटना राजेंद्र नगर।",
  "translated_text": "Help! Water has flooded our house, 4 people are trapped on the roof and a child is sick. Patna Rajendra Nagar.",
  "location": "Rajendra Nagar, Patna, Bihar",
  "severity": 5,
  "need_type": "rescue",
  "people_affected": 4,
  "summary": "4 people trapped on roof with a sick child in floodwaters",
  "confidence": 0.95,
  "status": "new"
}
```

---

### B. List Incidents (`GET /incidents`)
Returns incidents sorted by `severity DESC` (highest priority first) and `created_at ASC`.

```bash
# Get all incidents
curl -X GET "http://localhost:8000/incidents"

# Filter by status
curl -X GET "http://localhost:8000/incidents?status=new"

# Filter by need_type
curl -X GET "http://localhost:8000/incidents?need_type=rescue"
```

---

### C. Update Status (`PATCH /incidents/{id}/status`)
Transitions the incident forward in the triage lifecycle (`new` ➔ `acknowledged` ➔ `dispatched` ➔ `resolved`). Reversing or regressing status returns an `HTTP 400 Bad Request`.

```bash
curl -X PATCH "http://localhost:8000/incidents/1/status" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "acknowledged"
  }'
```

**Example Response (`200 OK`):**
```json
{
  "id": 1,
  "created_at": "2026-08-16T07:30:00Z",
  "original_language": "Hindi",
  "original_text": "मदद करो! हमारे घर में पानी भर गया है, 4 लोग छत पर फंसे हैं और एक बच्चा बीमार है। पटना राजेंद्र नगर।",
  "translated_text": "Help! Water has flooded our house, 4 people are trapped on the roof and a child is sick. Patna Rajendra Nagar.",
  "location": "Rajendra Nagar, Patna, Bihar",
  "severity": 5,
  "need_type": "rescue",
  "people_affected": 4,
  "summary": "4 people trapped on roof with a sick child in floodwaters",
  "confidence": 0.95,
  "status": "acknowledged"
}
```

---

### D. Get Single Incident (`GET /incidents/{id}`)

```bash
curl -X GET "http://localhost:8000/incidents/1"
```

---

## 6. Running Automated Tests

Run the backend test suite verifying the heuristics, API endpoints, error handling, and state machine:

```bash
python test_suite.py
```
