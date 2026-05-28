# EvalForge 🔬

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

**A lightweight, open-source LLM Evaluation Framework for testing and monitoring prompt quality across OpenAI, Claude, and Google Gemini.**

EvalForge lets you define test cases for LLM prompts, run evaluations against any LLM provider, score outputs using multiple strategies, track scores over time to detect regressions, and visualize everything in an interactive Streamlit dashboard.

---

## Why EvalForge?

Modern LLM applications demand rigorous evaluation. As you iterate on prompts, model versions, or deployment strategies, how do you know if quality improved or degraded? EvalForge solves this by automating the evaluation pipeline—define test cases once, run them continuously across providers, and get instant regression alerts. No more manual testing or guesswork.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (optional, but recommended)
- API keys for at least one LLM provider:
  - OpenAI (`OPENAI_API_KEY`)
  - Anthropic Claude (`ANTHROPIC_API_KEY`)
  - Google Gemini (`GOOGLE_API_KEY`)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/evalforge.git
   cd evalforge
   ```

2. **Copy environment template and add your API keys:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run with Docker Compose:**
   ```bash
   docker compose up
   ```

   The API will be available at `http://localhost:8000` and the dashboard at `http://localhost:8501`.

4. **Or run locally (without Docker):**
   ```bash
   # Install dependencies
   pip install -r requirements-api.txt
   pip install -r requirements-dashboard.txt

   # Start API (in one terminal)
   uvicorn api.main:app --reload

   # Start dashboard (in another terminal)
   streamlit run dashboard/app.py
   ```

---

## How to Write a Test Suite

Test suites are defined in YAML format. Create a file like `test_suites/my_suite.yaml`:

```yaml
suite: customer_support_bot
description: "Tests for the customer support chatbot"
model: gpt-4o
prompt_template: "You are a helpful support agent. Answer: {input}"

cases:
  - id: tc_001
    input: "How do I reset my password?"
    expected: "Go to settings and click forgot password"
    scorers: [exact_match, semantic_similarity, llm_judge]
    tags: [account, password]

  - id: tc_002
    input: "What are your business hours?"
    expected: "We are open 9am to 6pm Monday to Friday"
    scorers: [semantic_similarity, llm_judge]
    tags: [info, hours]

  - id: tc_003
    input: "I want to cancel my subscription"
    expected: "You can cancel from Account > Billing > Cancel Subscription"
    scorers: [semantic_similarity, llm_judge]
    tags: [account, billing]
```

### YAML Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `suite` | string | Yes | Unique name for this test suite |
| `description` | string | No | Human-readable description |
| `model` | string | Yes | LLM model to test (e.g., `gpt-4o`, `claude-opus-4-1`, `gemini-2.0-flash`) |
| `prompt_template` | string | Yes | Prompt with `{input}` placeholder |
| `cases` | array | Yes | Test cases (see below) |

### Test Case Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique case identifier (e.g., `tc_001`) |
| `input` | string | Yes | Input to send to the LLM |
| `expected` | string | Yes | Expected/reference output |
| `scorers` | array | Yes | List of scorer names to apply |
| `tags` | array | No | Metadata tags for filtering |

---

## Scorer Reference

EvalForge includes three built-in scorers, each returning a score from 0.0 to 1.0:

### 1. **exact_match**
Lowercased exact string comparison. Returns 1.0 if strings match, 0.0 otherwise.

**Best for:** Short, deterministic answers (e.g., "Yes", "No", specific codes)

### 2. **semantic_similarity**
Embeds both expected and actual outputs using `sentence-transformers` (all-MiniLM-L6-v2) and returns cosine similarity.

**Best for:** Fluent text where multiple phrasings are acceptable

### 3. **llm_judge**
Sends the expected and actual outputs to Claude for evaluation using a structured rubric. Returns a normalized score (0.0–1.0) based on a 1–5 rating.

**Best for:** Complex, subjective quality assessment

---

## API Endpoint Reference

### Health Check
```
GET /health
Response: {"status": "ok"}
```

### Run a Test Suite
```
POST /suites/run
Content-Type: multipart/form-data

Parameter: file (YAML file)

Response:
{
  "run_id": "run_20231215_143022",
  "suite_name": "customer_support_bot",
  "model": "gpt-4o",
  "total_cases": 3,
  "pass_count": 2,
  "avg_score": 0.87,
  "timestamp": "2023-12-15T14:30:22Z",
  "is_regression": false
}
```

### List All Runs
```
GET /runs
Response:
{
  "runs": [
    {
      "run_id": "run_20231215_143022",
      "suite_name": "customer_support_bot",
      "model": "gpt-4o",
      "timestamp": "2023-12-15T14:30:22Z",
      "total_cases": 3,
      "pass_count": 2,
      "avg_score": 0.87,
      "is_regression": false
    }
  ]
}
```

### Get Run Details
```
GET /runs/{run_id}
Response:
{
  "run_id": "run_20231215_143022",
  "suite_name": "customer_support_bot",
  "model": "gpt-4o",
  "timestamp": "2023-12-15T14:30:22Z",
  "total_cases": 3,
  "pass_count": 2,
  "avg_score": 0.87,
  "results": [
    {
      "case_id": "tc_001",
      "input": "How do I reset my password?",
      "expected": "Go to settings and click forgot password",
      "actual": "To reset your password, go to settings and click forgot password",
      "scores": {
        "exact_match": 0.0,
        "semantic_similarity": 0.95,
        "llm_judge": 1.0
      },
      "latency_ms": 1250
    }
  ]
}
```

### Export Run Results
```
GET /runs/{run_id}/export?format=csv
GET /runs/{run_id}/export?format=json

Returns: CSV or JSON file download
```

### Suite Score History
```
GET /suites/{suite_name}/history
Response:
{
  "suite_name": "customer_support_bot",
  "history": [
    {
      "run_id": "run_20231215_120000",
      "timestamp": "2023-12-15T12:00:00Z",
      "avg_score": 0.82,
      "scorer_breakdown": {
        "exact_match": 0.33,
        "semantic_similarity": 0.85,
        "llm_judge": 0.88
      }
    },
    {
      "run_id": "run_20231215_143022",
      "timestamp": "2023-12-15T14:30:22Z",
      "avg_score": 0.87,
      "scorer_breakdown": {
        "exact_match": 0.33,
        "semantic_similarity": 0.90,
        "llm_judge": 0.92
      }
    }
  ]
}
```

---

## Regression Detection

EvalForge automatically flags runs as regressions if the average score drops more than a configurable threshold (default: 0.05 or 5%) from the previous run on the same suite.

### How It Works

1. After each run completes, EvalForge calculates the average score across all cases and scorers.
2. It compares this to the previous run's average on the same suite.
3. If `|previous_avg - current_avg| > threshold`, it's flagged as a regression.
4. The flag is stored in the `regression_alerts` table and displayed in the dashboard.

### Example

- **Previous run average:** 0.87
- **Current run average:** 0.81
- **Difference:** 0.06 (6%)
- **Threshold:** 0.05 (5%)
- **Result:** 🔴 **Regression detected**

You can customize the threshold via the `REGRESSION_THRESHOLD` environment variable.

---

## Dashboard Pages

### Page 1: Run Overview
- Dropdown to select a suite
- Table of all runs with timestamp, model, pass rate, avg score, and regression flag (🔴)
- Button to upload and run a new YAML suite

### Page 2: Run Detail
- Select a run by ID
- Summary metrics: total cases, pass rate, avg scores per scorer
- Table of all cases with colour-coded scores:
  - 🟢 Green: score ≥ 0.8
  - 🟡 Yellow: 0.5 ≤ score < 0.8
  - 🔴 Red: score < 0.5
- Expandable rows showing input, expected, actual, per-scorer breakdown, and LLM judge reasoning

### Page 3: Score History & Drift
- Line chart of average score over time per scorer
- Regression points highlighted in red
- Prompt Drift Index (standard deviation of scores over last 5 runs)
- Export chart as PNG

### Page 4: Export
- Select a run
- Choose format (CSV or JSON)
- Download button

---

## Project Structure

```
evalforge/
├── api/
│   ├── __init__.py
│   ├── config.py                # Configuration & settings
│   ├── main.py                  # FastAPI app, router registration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── suites.py            # /suites endpoints
│   │   └── runs.py              # /runs endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── db.py                # SQLAlchemy models + async engine
│   │   └── schemas.py           # Pydantic request/response schemas
│   └── services/
│       ├── __init__.py
│       ├── runner.py            # Suite orchestration
│       ├── llm_clients.py       # OpenAI/Claude/Gemini wrappers
│       └── scorers/
│           ├── __init__.py
│           ├── base.py          # BaseScorer abstract class
│           ├── exact.py         # ExactMatchScorer
│           ├── semantic.py      # SemanticSimilarityScorer
│           └── llm_judge.py     # LLMJudgeScorer
├── dashboard/
│   └── app.py                   # Streamlit dashboard
├── test_suites/
│   └── example_suite.yaml       # Example test suite
├── tests/
│   ├── test_scorers.py
│   └── test_runner.py
├── data/                        # SQLite database
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.dashboard
├── requirements-api.txt
├── requirements-dashboard.txt
└── README.md
```

---

## Roadmap

- [ ] **Multi-model comparison**: Run the same suite against multiple models in parallel and compare scores
- [ ] **GitHub Actions integration**: Auto-run evaluations on PR, comment results back on PR
- [ ] **Async batch runs**: Queue and process multiple suites asynchronously with progress tracking
- [ ] **Custom scorer plugins**: Allow users to register custom scoring functions
- [ ] **Webhook notifications**: Send Slack/Discord alerts on regressions
- [ ] **Cost tracking**: Track and display API costs per run
- [ ] **Prompt versioning**: Store prompt versions with each run for comparison
- [ ] **Team collaboration**: Multi-user support with shared suites and run history

---

## Contributing

We welcome contributions! Please open an issue or PR on GitHub.

---

## License

MIT License — see LICENSE file for details.

---

## Support

- 📖 **Docs**: Check the README and inline code comments
- 🐛 **Issues**: Open an issue on GitHub
- 💬 **Discussions**: Start a discussion for feature requests or general questions

---

## Screenshot Placeholders

(After building the dashboard, add screenshots here)

- **Run Overview Page**
- **Run Detail Page with Case Breakdown**
- **Score History & Drift Chart**
- **Export Interface**

---

Built with ❤️ by the EvalForge team.
