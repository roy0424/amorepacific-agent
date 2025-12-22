# Repository Guidelines

## Project Structure & Module Organization
- `src/` holds the application code: core infra (`src/core`), models (`src/models`), scrapers (`src/scrapers`), flows (`src/flows`), insights (`src/insights`), services (`src/services`), and tasks (`src/tasks`).
- `config/` contains runtime settings and prompt templates (e.g., `config/settings.py`, `config/prompt_templates.yaml`).
- `scripts/` provides entry points for setup, flow runs, data export, and utilities.
- `alembic/` and `migrations/` store database migration tooling.
- `data/` contains runtime artifacts (logs, exports, backups). Avoid committing large outputs.
- `ui/` contains Streamlit tooling for prompt testing.
- `tests/` exists but currently has no files; add new tests here.

## Build, Test, and Development Commands
- `python -m venv venv` and `source venv/bin/activate` (or `venv\Scripts\activate`) to create/activate a virtualenv.
- `pip install -r requirements.txt` installs dependencies.
- `playwright install chromium` installs the browser for scraping.
- `python scripts/init_db.py` initializes the database schema and seed data.
- `prefect server start` starts the Prefect UI at `http://localhost:4200`.
- `python scripts/deploy_flows.py` deploys scheduled flows.
- `python scripts/run_manual.py --flow amazon-test` runs a fast Amazon scrape; use `--flow amazon` for full runs.
- `python scripts/start_all.py` starts the quickstart pipeline (see `QUICKSTART_SIMPLE.md`).

## Coding Style & Naming Conventions
- Python 4-space indentation; keep modules small and focused.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and `snake_case.py` for files.
- Optional tooling in `requirements.txt`: `black`, `flake8`, `mypy`, `pytest`. No repo config files are present, so follow default settings if you run them.

## Testing Guidelines
- The repo expects `pytest` and `pytest-asyncio`, but `tests/` is currently empty.
- Name tests `test_*.py` and keep them under `tests/` mirroring `src/` subpackages.
- Run tests with `pytest` once tests are added.

## Commit & Pull Request Guidelines
- No Git history exists yet (`main` has no commits), so there is no established commit message convention.
- For new commits, use a short imperative subject and include context in the body when behavior changes.
- PRs should describe the data sources affected, flows/scripts touched, and any required `.env` settings; include screenshots for Prefect UI changes when relevant.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and set required keys (e.g., `OPENAI_API_KEY`, `YOUTUBE_API_KEY`).
- Use PostgreSQL for local development (`DATABASE_URL=postgresql+psycopg://laneige:laneige@localhost:5432/laneige_tracker`).
- Do not commit secrets or generated files under `data/`.
