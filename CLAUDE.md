# Counting the Cold

Hackathon app: chill and GDD for any California orchard pin, from Open-Meteo, bias-corrected against CIMIS. FastAPI in `backend/`, React/Vite in `frontend/`.

Three people work here in parallel, each with their own Claude. Before changing anything:

1. Ask your human which role they are if you don't know: **A** (Data & API), **B** (Science & Validation), or **C** (Frontend & Demo).
2. Read `docs/CONTRIBUTING.md` (folder ownership, git workflow) and `docs/api-contract.md` (JSON shapes). The live plan is https://claude.ai/artifact/RircwznHknoxj1voHwgYpK; `docs/BUILD_PLAN.md` is its snapshot.

Rules:

- Only create or edit files your role owns. If a task needs a change elsewhere, stop and say who owns it.
- Never change `docs/api-contract.md`, `backend/app/schemas.py`, or `frontend/src/api/types.ts` on your own; contract changes go through a `contract` PR.
- Don't add dependencies unless your role owns that file (`requirements.txt`: A; `package.json`: C).
- Work on a branch `<data|sci|ui>/<issue#>-<slug>`, rebase on `origin/main`, open a small PR with `Closes #N`. Never push to `main` or force-push a shared branch.
- Never read, print, commit, or log `CIMIS_KEY` or `.env`.
- No CIMIS calls on the request path; upstream calls go through `backend/app/sources/cache.py`; respect `DEMO_MODE`.
- `backend/app/calc/` stays pure (no I/O). Before a PR run `cd backend && pytest` and/or `cd frontend && npm run build`.
- Tests marked `@stub` expect `NotImplementedError`; once the function works, remove the marker.
- No `stretch` issues until milestone M4 is done; nothing new after the H20 feature freeze.
