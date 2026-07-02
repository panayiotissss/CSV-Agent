# CSV Analyst Agent

An AI agent that answers natural-language questions about CSV data by chaining validated, typed tools — **every number is computed, never hallucinated.**

Ask a question in plain English ("What's the average revenue in the North region?") and the agent decides which operations to run, executes them against the data, and returns a structured, auditable answer.

---

## Why this exists

Large language models are notoriously unreliable with numbers — ask a plain LLM to analyze a spreadsheet and it will happily invent plausible-looking figures. That's unacceptable for real analytics.

This agent solves that: it **cannot invent a number.** Every figure in its answer is produced by a real, validated data operation, and each answer ships with the list of tools used to reach it — an auditable trail. It turns "ask your data in plain English" from a demo risk into something a business can actually trust.

---

## Key features

- **Agentic tool-calling loop** — the *model* decides which tools to call and in what order based on the question, not a hardcoded pipeline.
- **Type-safe structured output** — every answer is returned as a validated Pydantic object, not loose text, so it drops straight into an API or downstream system.
- **Safe by design** — the agent can only call a fixed set of typed operations; it never executes arbitrary code against the data.
- **Production patterns** — retry logic with exponential backoff, structured logging, graceful error handling, and a hard cap against runaway loops.
- **Served over HTTP** — a FastAPI endpoint with interactive docs.
- **Containerized** — a Dockerfile for reproducible, deploy-anywhere runs.

---

## How it works

The core is a simple loop with a powerful property: **control flow is handed to the model.**

1. The user's question and the available tools are sent to the model.
2. The model responds either with a **tool call** (e.g. "filter rows where region == North") or a **final answer**.
3. If it's a tool call, the code executes the real function, feeds the result back, and loops.
4. This repeats — the model choosing each step based on the previous result — until it produces a structured final answer.

Because the model chooses the path, a question needing two operations chains two tools automatically, while a simple question uses one or none. Nothing is hardcoded.

### Tools

| Tool | What it does |
|---|---|
| `aggregate` | Groups rows by a column and computes sum / mean / count / min / max over a numeric column. |
| `filter_rows` | Returns rows where a column meets a comparison (`==`, `!=`, `>`, `<`, `>=`, `<=`). |
| `final_answer` | Concludes the task by emitting the structured, validated result. |

### Design decision: constrained tools, not free code execution

The agent is deliberately limited to typed operations rather than being allowed to write and run arbitrary pandas code. This is a safety-for-flexibility trade: constrained tools mean the agent cannot do anything destructive or unexpected, every argument is schema-validated, and the behaviour is auditable — the right call for a system a client would trust with their data.

---

## Tech stack

Python · FastAPI · Anthropic tool-use · Pydantic · Docker

---

## Getting started

### Prerequisites
- An Anthropic API key
- Docker (or Python 3.12+ to run locally)

### Run with Docker

```bash
# 1. Add your API key to a .env file (never commit this)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 2. Build the image
docker build -t csv-agent .

# 3. Run it
docker run -p 8000:8000 --env-file .env csv-agent
```

Then open **http://localhost:8000/docs** for the interactive API, or POST to `/ask`:

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total revenue by region?"}'
```

### Run locally (without Docker)

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Example

**Request**

```json
{ "question": "What is the total revenue by region?" }
```

**Response**

```json
{
  "answer": "The South region leads with total revenue of 88,300, followed by North (71,000), West (53,700), and East (31,600).",
  "key_numbers": { "South": 88300, "North": 71000, "West": 53700, "East": 31600 },
  "tools_used": ["aggregate"],
  "confidence": "high"
}
```

Every number in `key_numbers` was computed by a tool — the `tools_used` field is the audit trail.

---

## Architecture

```
Request → FastAPI /ask → run_agent()
                              │
                    ┌─────────▼─────────┐
                    │   Agent loop      │
                    │  (model decides)  │
                    └─────────┬─────────┘
                              │  tool call
                    ┌─────────▼─────────┐
                    │  aggregate /      │
                    │  filter_rows      │──── result fed back ──┐
                    └───────────────────┘                       │
                              ▲                                  │
                              └──────────────────────────────────┘
                              │  final_answer
                    ┌─────────▼─────────┐
                    │  Pydantic Finding │ → JSON response
                    └───────────────────┘
```

---

## Known limitations & roadmap

- **Tools don't yet compose.** `aggregate` and `filter_rows` are each independently useful, but the agent can't currently aggregate *only* a filtered subset in a single operation (aggregate always runs on the full dataset). A planned v2 lets `aggregate` accept optional filter conditions so compound questions ("average revenue in the North in Q2") resolve cleanly.
- **Single bundled dataset.** The agent analyzes one CSV bundled at build time. A file-upload endpoint is a natural next step.
- **Read-only.** By design, the agent only reads and analyzes — it never modifies data.

---

## License

MIT
