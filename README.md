# HireLens AI — Evidence-Driven AI Hiring Panel

Full-stack app: FastAPI backend (multi-agent LLM pipeline) + React/Vite frontend (the UI you
already designed), wired together and ready to demo.

```
hirelens-app/
├── backend/     FastAPI + Anthropic-powered pipeline (see backend/README.md for full details)
├── frontend/    React + Vite + Tailwind UI, calling the backend over HTTP
└── start_all.sh runs both at once
```

## 1. Fastest path to a running demo

```bash
cd hirelens-app/backend
cp .env.example .env
# edit .env -> paste your ANTHROPIC_API_KEY

cd ..
./start_all.sh
```

This starts:
- Backend on **http://localhost:8000** (Swagger docs at `/docs`)
- Frontend on **http://localhost:5173**

Open `http://localhost:5173`, click **New Candidate**, upload a resume + transcript (or use the
files in `backend/sample_data/`), and click **Analyze Candidate**.

> First run installs a Python venv + npm packages, so it'll take a minute the first time. Both
> processes stay attached to your terminal — `Ctrl+C` stops both.

## 2. Running them separately (two terminals)

```bash
# Terminal 1
cd hirelens-app/backend
cp .env.example .env   # add your ANTHROPIC_API_KEY
./run.sh                # -> http://localhost:8000

# Terminal 2
cd hirelens-app/frontend
./run.sh                # -> http://localhost:5173
```

## 3. How the frontend talks to the backend

`frontend/src/api.js` calls the backend's `POST /api/analyze` endpoint (multipart form: resume
file + transcript file + optional job description/target role/voice toggle) and gets back a
single JSON `FinalReport` object that drives every screen (Profile, Agents, Debate, Decision).

By default it points at `http://localhost:8000`. To point at a different backend host (e.g. if
you deploy the backend somewhere), create `frontend/.env` from `frontend/.env.example` and set
`VITE_API_BASE`.

## 4. What's real vs. what's illustrative in the UI

- **Setup → Profile → Agents → Debate → Decision**: all driven by the live API response —
  nothing here is mocked once you click "Analyze Candidate".
- **Sidebar "Demo examples"** and the dashboard's fallback stats before you've run an analysis:
  static placeholder content so the dashboard doesn't look empty on first load. They're visually
  dimmed and non-interactive so they're never mistaken for real results.

## 5. Troubleshooting

- **"Failed to fetch" / network error in the UI** → backend isn't running, or is on a different
  port than `VITE_API_BASE` expects. Check `http://localhost:8000/api/health` in your browser.
- **CORS error in the browser console** → shouldn't happen with the default `.env` (CORS is wide
  open for the hackathon), but if you changed `CORS_ORIGINS` in `backend/.env`, make sure
  `http://localhost:5173` is included.
- **Pipeline errors / JSON parse failures from the LLM** → check the backend terminal logs; the
  LLM client automatically retries once on malformed JSON. If it's a persistent model issue, try
  changing `ANTHROPIC_MODEL` in `backend/.env`.
- **Analysis feels slow** → the pipeline makes ~7 sequential/parallel LLM calls (profile builder,
  4 independent agents in parallel, debate, judge). 30–90 seconds is normal; the UI shows a
  spinner with that expectation set.

See `backend/README.md` for the full API reference and architecture breakdown.
