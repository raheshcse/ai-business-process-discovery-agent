# Process Discovery — Frontend

React + Vite + TypeScript + Tailwind interface for the AI Business Process
Discovery Agent. Every screen is wired to the FastAPI backend; there is no
mock data anywhere in `src/` outside `src/test/`.

## Setup

```bash
cd frontend
npm install
cp .env.example .env      # edit if your backend is not on :8000
npm run dev               # http://localhost:5173
```

The backend must be running first, and its `CORS_ORIGINS` must include the
frontend origin (`http://localhost:5173` is the default on both sides).

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend base URL, including the API prefix |
| `VITE_POLL_INTERVAL_MS` | `2000` | How often to poll a running analysis or an indexing document |

No URL is hardcoded in a component — everything routes through
`src/api/config.ts`.

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Dev server on port 5173 |
| `npm run build` | Typecheck (`tsc -b`) then production build |
| `npm run preview` | Serve the production build |
| `npm run lint` | Typecheck only |
| `npm test` | Run the Vitest suite |
| `npm run test:watch` | Vitest in watch mode |

## Architecture

```
src/
├── api/
│   ├── client.ts        fetch wrapper, ApiError, upload with progress
│   ├── config.ts        env-based configuration
│   └── endpoints.ts     one function per backend endpoint
├── components/
│   ├── layout/          AppLayout, Sidebar, Header, PageShell, EnvironmentBanner
│   └── ui/              Button, Card, Modal, Table, StatusChip, States, icons
├── features/
│   ├── analysis/        AnalysisSection, FindingCard, ProcessFlow, RunProgress,
│   │                    StartAnalysisPanel
│   ├── documents/       UploadArea, DocumentTable, validateFile
│   └── projects/        ProjectForm + validation
├── hooks/queries.ts     React Query bindings, conditional polling
├── lib/                 formatting and class-name helpers
├── pages/               one component per route
├── types/api.ts         TypeScript mirrors of the backend Pydantic schemas
└── test/                fixtures, fetch stub, render helpers
```

**Layering.** `pages` compose `features`, which compose `ui`. Only
`api/endpoints.ts` knows URLs; only `hooks/queries.ts` knows about caching.
Nothing in `api/` or `lib/` imports React, so both are testable in isolation.

**Types.** `src/types/api.ts` mirrors the backend schemas field for field.
A script in the repo root verifies it against the live `/openapi.json`, so
drift is caught rather than discovered at runtime.

**Polling.** A document polls only while `index_status` is `pending` or
`processing`; an analysis polls only while its status is non-terminal. An
idle tab makes no requests.

**Error handling.** Every failure becomes an `ApiError` carrying a message
a person can act on. FastAPI's `detail` is flattened whether it is a string
or a list of validation objects, and an unreachable backend is reported
distinctly from an HTTP error.

## Screens

| Route | Screen |
| --- | --- |
| `/` | Dashboard — portfolio totals, analysis status, recent activity |
| `/projects` | Projects — create, edit, delete, search |
| `/projects/:projectId` | Workspace — summary, documents, upload, indexing status, run analysis |
| `/analyses/:runId` | Results — process, bottlenecks, risks, automation, summary, citations |
| `/analyses/:runId/governance` | Governance & audit for one run |
| `/governance` | The governance rulebook, independent of any run |

## Accessibility

Semantic landmarks throughout, visible focus rings on every interactive
element, `aria-invalid` and `aria-describedby` on validated fields,
`role="alert"` on errors, `aria-live` on loading states, labelled upload
progress bars, and a `<dialog>`-based modal so the browser owns focus
trapping. Layout is responsive from tablet upward; the sidebar collapses to
a drawer below `lg`.
