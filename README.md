# THERMO-SHIELD AI — SIH 2026

Full-stack SIH prototype for AI-assisted detection, classification and prioritization of industrial fires and persistent thermal sources using NASA FIRMS, OpenStreetMap and optional satellite STAC evidence.

## Structure
- `frontend/` — React/Vite/Leaflet dashboard
- `api/index.py` — FastAPI serverless backend
- `requirements.txt` — backend dependencies
- `vercel.json` — combined Vercel build configuration

## Deploy to Vercel
Import the repository root. Vercel builds the frontend with `cd frontend && npm run build` and serves `api/index.py` as the `/api/*` backend. Add `FIRMS_MAP_KEY` in Vercel Environment Variables for live NASA FIRMS synchronization. Never commit the key.

## Local
Backend: `pip install -r requirements.txt` then `uvicorn api.index:app --reload --port 8000`.
Frontend: `cd frontend && npm install && npm run dev`.

Production frontend automatically uses same-origin `/api`; local development uses `http://localhost:8000/api`.

## SIH model note
The included baseline is deterministic and deployable without heavy ML packages. It is intended as the working integration layer. For the final SIH model, replace the baseline weights with the trained classifier and report validation metrics from the official dataset.
