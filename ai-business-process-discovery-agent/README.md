# AI Business Process Discovery Agent

Upload your organisational documents, discover how a process actually works,
and get every conclusion gated by X-Verba governance with a tamper-evident
audit trail.

```
backend/   FastAPI · SQLAlchemy · RAG · LangGraph · vsl-core / vsl-langgraph
frontend/  React 18 · Vite · TypeScript · Tailwind · TanStack Query
```

## Quick start

Two terminals.

**Terminal 1 — backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open <http://localhost:5173>. API docs are at <http://localhost:8000/docs>.

### Ollama prerequisites

The default configuration uses Ollama for both analysis and embeddings:

```bash
ollama serve
ollama pull llama3.2          # analysis model
ollama pull nomic-embed-text  # embedding model
```

Without the embedding model, set `EMBEDDING_PROVIDER=local` — but read the
warning below first, because it changes governance behaviour.

> **Embeddings matter more than they look.** The bundled `local` provider
> hashes text rather than understanding it, so its cosine similarity scores
> are effectively random and frequently negative. The process-discovery
> governance gate rejects any citation scoring below
> `GOVERNANCE_MINIMUM_EVIDENCE_SCORE`, so a `local` deployment sees analyses
> blocked at the first gate for reasons that have nothing to do with the
> documents. The UI shows a persistent banner when this is the case. Keep
> `local` for tests.

### Running without a model

For a full offline smoke test of the workflow and both governance screens:

```bash
# backend/.env
LLM_PROVIDER=mock
```

The mock provider is stage-aware, so the complete eleven-gate governed path
runs end to end. Its findings are placeholders and say so.

## Demo walkthrough

1. **Dashboard** — empty state invites you to create a project.
2. **Projects → New project.** Name it, give it an objective. The form
   validates against the same limits the API enforces.
3. **Open the project.** Drag in a process document (`.pdf`, `.docx`,
   `.txt`, `.csv`, `.xlsx`, up to 25 MB). Watch the status chip move
   *Queued → Processing → Ready* on its own — extraction, chunking and
   embedding run in the background and the row polls until it settles.
   Word count and searchable-section count appear when it lands.
4. **Run a governed analysis.** The button stays disabled until at least one
   document is indexed, because the workflow will not answer from anything
   other than your evidence. Pick a suggested question or write your own.
5. **Watch it run.** The results page shows live stage progress across the
   five analysis stages. Five sequential model calls take a few minutes.
6. **Read the results.** Executive summary first, then the process
   walkthrough, bottlenecks, risks by severity, automation opportunities,
   and a source table. Every finding names the `Source N` markers behind it
   and each resolves to a real filename.
7. **Open Governance & audit.** Eleven gate decisions in the order they ran,
   each explained in business language. Toggle *Show technical detail* to
   reveal construct names and the raw hash-chained ledger.
8. **Try a blocked run.** Ask something your documents do not cover. The
   workflow stops at `INSUFFICIENT_EVIDENCE` and says so plainly — and the
   audit page now shows the human-authorisation check *failing*, because
   this application has no approval workflow. That failure is reported
   honestly rather than hidden.

## Testing

```bash
cd backend  && pytest              # 158 tests
cd frontend && npm test            # 46 tests
cd frontend && npm run build       # typecheck + production build
```

## API

Base path `/api/v1`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Status and provider configuration |
| GET | `/dashboard` | Portfolio aggregates and recent activity |
| GET POST | `/projects` | List / create |
| GET PUT DELETE | `/projects/{id}` | Read / update / delete |
| GET POST | `/projects/{id}/documents` | List / upload |
| GET DELETE | `/documents/{id}` | Read / delete |
| POST | `/documents/{id}/reindex` | Retry extraction and indexing |
| GET POST | `/projects/{id}/analyses` | List / start a governed run |
| GET | `/analyses/{id}` | Run detail, including all five analyses |
| GET | `/analyses/{id}/governance` | Decisions, ledger, audit checks |
| GET | `/governance/catalogue` | The governance rulebook |

## Notes on scope

Governance here constrains the *process*: whether a stage had grounded
evidence before running, and whether its output cited real sources and
stayed in scope. It does not and cannot establish that the model read your
documents correctly. The risk analysis is deliberately prevented from
drawing legal or regulatory conclusions.

Two of the five ledger audit checks are expected to fail whenever a run
stops at a terminal state, because this application has no human-approval or
specification-update workflow. The audit screen reports that plainly.
