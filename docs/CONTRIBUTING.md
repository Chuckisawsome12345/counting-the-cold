# Contributing

Three people, three roles, separate folders. If you only follow one rule: **edit only the files your role owns.**

**Who's who:** A (Data & API) is [@Chuckisawsome12345](https://github.com/Chuckisawsome12345) · B (Science & Validation) is [@karthikmaheshwaran](https://github.com/karthikmaheshwaran) · C (Frontend & Demo) is [@Zooomer69](https://github.com/Zooomer69). `.github/CODEOWNERS` encodes the table below.

## Folder ownership

| Path | Owner |
|---|---|
| `backend/app/main.py`, `config.py`, `schemas.py` | A: Data & API |
| `backend/app/routes/`, `backend/app/pipeline/` | A |
| `backend/app/sources/` except `cimis.py` | A |
| `backend/scripts/prewarm.py`, `backend/scripts/make_mock.py`, `backend/scripts/build_grid.py` | A |
| `backend/data/stations.json`, `backend/data/snapshots/`, `backend/data/mock_point*.json`, `backend/data/grid/` | A |
| `backend/requirements.txt`, `backend/pytest.ini` | A |
| `backend/tests/test_api.py`, `backend/tests/test_sources.py`, `backend/tests/test_pipeline.py` | A |
| Root files (`README.md`, `.gitignore`, `.env.example`, `.github/`) | A |
| `backend/app/calc/`, `backend/app/validation/` | B: Science & Validation |
| `backend/app/sources/cimis.py` | B |
| `backend/scripts/fetch_cimis.py`, `backend/scripts/build_validation.py` | B |
| `backend/data/cimis/`, `backend/data/validation.json` | B |
| `backend/tests/` (everything else, including `fixtures/`) | B |
| `frontend/**` | C: Frontend & Demo |
| `docs/demo-script.md` | C |
| `docs/api-contract.md` | Shared: change only via a `contract` PR |
| `docs/BUILD_PLAN.md` (+ `.pdf`) | Shared: change only via a `plan` PR |

Need something in a folder you don't own? Comment on the owner's issue or ping them.

## Workflow

1. Your role's issues are assigned to you. Take the next one by milestone:
   ```bash
   gh issue list --assignee @me
   ```
2. Branch from fresh `main`, prefixed by role (`data/`, `sci/`, `ui/`):
   ```bash
   git switch main && git pull
   git switch -c sci/7-dynamic-model
   ```
3. Commit small and often. Before opening a PR, rebase and run the checks:
   ```bash
   git pull --rebase origin main
   cd backend && pytest            # backend changes
   cd frontend && npm run build    # frontend changes
   ```
4. Push and open a PR whose description says `Closes #7`. Merge (squash) once CI is green. No approval is required, but tag the others if you touched anything shared.
5. Merge every 1–2 hours. Long-lived branches cause conflicts.

`main` is protected: no direct pushes, no force pushes, and the `backend-tests` and `frontend-build` checks must pass.

## Contract changes

`docs/api-contract.md` is the source of truth for every JSON shape. To change it:

1. Open a PR labeled `contract` that edits `docs/api-contract.md`, and @mention the other two.
2. A mirrors the change in `backend/app/schemas.py` (and re-runs `python scripts/make_mock.py`).
3. C mirrors it in `frontend/src/api/types.ts`.

## Plan changes

`docs/BUILD_PLAN.md` is the team plan and the source of truth (it replaced the Claude Doc). To change it:

1. Open a small PR labeled `plan` that edits only that file, and @mention the other two.
2. Stick to your own role's sections unless the team agreed; say what changed in the PR description.
3. Track progress on the GitHub milestones and issues, not by editing the plan.

## Dependencies

Only A edits `backend/requirements.txt`; only C edits `frontend/package.json` and `package-lock.json`. Ask the owner to add a package.

## Stub tests

Tests for unwritten functions are marked `@stub` (an expected failure on `NotImplementedError`). When you implement the function:

- a correct implementation shows up as `XPASS`: delete the `@stub` marker;
- a wrong one fails the test outright.

## Secrets

`CIMIS_KEY` lives only in your local `.env` (gitignored) and in Render's environment. Never commit it, paste it in chat or an issue, or send it to the frontend.
