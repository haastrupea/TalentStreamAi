# TalentStreamAI

Squad Five capstone for the Andela AI Engineering Bootcamp. The goal is straightforward on paper: help a candidate move from “I found a role” to “I submitted strong materials” without burning an afternoon on manual rewrites. This repository is the **scaffold** only—FastAPI for the API surface, a static-export Next.js client, and a **Terraform root** that is intentionally empty except for provider wiring, variables, outputs, and comments that describe the AWS shape you are heading toward (Aurora Serverless v2 + Data API, Secrets Manager, ECS or Lambda for LangGraph/OpenRouter, API Gateway + Clerk JWT, CloudFront in front of S3). Implementers add resources when they are ready.

Product direction (for context while you build):

- Ingest a resume plus a job posting URL.
 - Diff the candidate's story against the role (ATS-oriented gap analysis).
 - Generate refreshed resume copy, a cover letter with narrative structure, and a Gmail-ready draft.

## Implementation Status

The backend is now fully implemented with a LangGraph-based workflow for generating job application materials.

### API Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/v1/apply` | POST | Run the complete TalentStreamAI workflow |
| `/api/v1/fetch-job` | POST | Fetch and parse a job description from URL |
| `/api/v1/parse-resume` | POST | Parse a resume file (PDF or DOCX) |
| `/api/v1/score-ats` | POST | Score resume against job description for ATS compatibility |

#### Apply Endpoint (Main)

The main `/api/v1/apply` endpoint accepts:
- `job_url` (str): URL of the job posting
- `resume` (UploadFile): Resume file (PDF or DOCX)

Returns job data, resume data, ATS score, gap analysis, tailored resume, cover letter, and email draft.

### LangGraph Workflow

The workflow consists of these nodes executed in sequence:

1. **fetch_job**: Fetches job description from URL using web scraping
2. **parse_resume**: Parses PDF/DOCX resume into structured data
3. **score_ats**: Scores resume against job requirements
4. **analyze_gaps**: Identifies keyword and skill gaps
5. **generate_resume**: Generates ATS-optimized tailored resume (LLM)
6. **generate_cover_letter**: Generates narrative cover letter (LLM)
7. **generate_email**: Generates Gmail-ready email draft (LLM)

### Tools

Located in `backend/app/tools/`:
- **job_fetcher.py**: Fetches and parses job descriptions from URLs
- **resume_parser.py**: Parses PDF and DOCX resumes
- **ats_scorer.py**: Scores resumes against job requirements for ATS compatibility
- **models.py**: Pydantic models for all tool inputs and outputs

### Environment Variables

Required in `.env`:
| Key | Description |
| --- | --- |
| `OPENROUTER_API_KEY` / `OPENAI_API_KEY` | At least one for `AGENT_MODE=llm`: OpenRouter for chat if set, else `OPENAI_API_KEY` (see `.env.example`). |
| `LANGFUSE_*` | Optional: Langfuse keys for API-side LLM observability (see `.env.example`). |

## Prerequisites

Pick what matches how you work day to day:

- **Docker Desktop** (or Docker Engine) plus the Compose plugin for the one-command local stack.
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** for installing and running the Python service (lockfile-backed).
- **Python 3.12** (`backend/.python-version` helps pyenv/asdf) and **Node.js 20+** for host-only development.
- **Terraform 1.6+** and the **AWS CLI v2** when you touch AWS resources.
- An **AWS account** with credentials (`AWS_PROFILE` or standard access keys) when running Terraform or deploy workflows locally.

Secrets stay out of git. Copy `.env.example` at the **repository root** to `.env` and fill in values for your machine. Deployed environments should load the same keys from your secret manager or GitHub Actions secrets/variables.

## First-time local setup (without Docker)

```bash
chmod +x scripts/*.sh   # first clone only
cp .env.example .env    # optional but recommended
./scripts/bootstrap-local.sh
```

Start each service in its own terminal:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` for the UI and `http://localhost:8000/docs` for OpenAPI. The home page calls `/api/v1/health` so you can confirm both halves are talking.

### Environment variables (repo root `.env`)

Both FastAPI (`pydantic-settings`) and Next.js (via `dotenv-cli` in `frontend/package.json` scripts) read from the **same** `.env` at the repository root. Keep per-environment values out of source code—set them here locally, or inject them in CI/CD.

| Key | Consumers | Purpose |
| --- | --- | --- |
| `API_HOST` | API | Bind address inside the container or host. |
| `API_PORT` | API | Port for Uvicorn when you run it manually. |
| `CORS_ORIGINS` | API | Comma-separated browser origins allowed to call the API. |
| `NEXT_PUBLIC_API_URL` | UI (build + browser) | Public API base URL the browser calls. Leave empty for production builds that should call same-origin `/api/*` through CloudFront. |
| `DEPLOYMENT_ENVIRONMENT` | API (`/api/v1/health` metadata) | Optional label such as `local`, `dev`, `staging`, or `prod`. |
| `OPENROUTER_API_KEY` | API | OpenRouter key; used for chat when set (with `LLM_BASE_URL` for OpenRouter). |
| `OPENAI_API_KEY` | API | Used for chat when `OPENROUTER_API_KEY` is unset; optional when OpenRouter is set. |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | API | Optional. [Langfuse](https://langfuse.com) project keys for LLM tracing; set with `LANGFUSE_BASE_URL` (or `LANGFUSE_HOST`) for EU/US/self-hosted. |
| `PLAN_CLAIM_PATH` / `PLAN_DEFAULT` | API | Clerk Billing plan extraction from session JWT claims and mapping to internal plan keys (`free`, `starter`, `pro`). |
| `*_MONTHLY_*_LIMIT` and `*_MONTHLY_LLM_TOKEN_BUDGET` | API | Per-plan monthly quotas for applications, base resume uploads, and LLM tokens enforced by the API. |
| `INPUT_INJECTION_MODE` / `EXPECTED_INPUT_MODE` | API | Guard policy mode (`warn` or `block`) for prompt-injection heuristics and document-type validation. |

### Clerk billing claim setup

The backend reads subscription tier from JWT claims (`AuthenticatedUser.claims`) and never calls Clerk on every API request. In Clerk:

1. Ensure your session token template includes the billing signal you want to trust (for example `public_metadata.plan`, a custom plan claim, or a price/product id).
2. Set `PLAN_CLAIM_PATH` to that nested claim path (default `public_metadata.plan`).

Use Clerk test mode with test payment methods in development; production should keep the same mapping logic, with only Clerk live keys and live plan ids changing.

## Run the full stack in Docker

```bash
chmod +x scripts/*.sh   # first clone only
cp .env.example .env      # optional; run.sh exports it for Compose variable substitution
./scripts/run.sh
```

- API on `http://localhost:8000`
- UI on `http://localhost:3000` (**`next dev`** inside Compose — hot reload, not a production `next build`)
- **Why the first run can feel slow:** `./scripts/run.sh` runs `docker compose up --build`. The backend image pulls base layers and runs `uv sync` once; the frontend image runs **`npm ci`** during **`docker compose build`**. After that, Compose just starts the container; the UI is **`next dev`** from `frontend/Dockerfile`. To pick up new frontend dependencies after you edit **`package-lock.json`**, run `docker compose build frontend` (or `docker compose up --build`) again.

Stop everything with `./scripts/stop.sh`.

## Terraform (single root under `terraform/`)

Terraform now contains the active AWS stack for this project (CloudFront + S3 static site, API Gateway + Lambda, VPC/NAT/EFS, and uploads bucket).

For deploy steps, environment wiring, backend zip publishing, and frontend sync/invalidation, use:

- [`terraform/README.md`](terraform/README.md)

## Project structure

Repository root **`TalentStreamAI/`** 

```text
TalentStreamAI/
├── backend/                         # FastAPI API (uv / pyproject.toml)
│   ├── app/
│   │   ├── main.py                  # App factory + CORS + router mount
│   │   ├── api/                     # HTTP routers (e.g. v1/health)
│   │   ├── core/                    # Settings (reads repo-root .env)
│   │   └── services/
│   │       └── langgraph/           # Placeholder for agent graphs / tools
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/                        # Next.js 15 (App Router, static export)
│   ├── src/
│   │   ├── app/                     # Routes, layouts, pages
│   │   └── lib/                     # Shared helpers (e.g. API URL builder)
│   ├── public/                      # Static assets for export
│   ├── Dockerfile                   # Local `next dev` in Docker (used by Compose)
│   ├── next.config.ts
│   └── package.json
├── terraform/                       # AWS scaffold (no resources yet)
│   ├── main.tf                      # terraform {} + locals + architecture checklist
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── backend.hcl.example
│   ├── terraform.tfvars.example
│   └── .terraform.lock.hcl
├── scripts/
│   ├── bootstrap-local.sh           # uv sync + npm install
│   ├── run.sh / stop.sh             # Docker Compose up / down
│   └── deploy-aws.sh / destroy-aws.sh   # Terraform plan / destroy helpers
├── .github/
│   ├── workflows/                   # CI + deploy placeholder workflows
│   └── aws/
│       └── github-oidc-trust-policy.json.example
├── docker-compose.yml               # Local API (:8000) + Next dev server (:3000)
├── .env.example                     # Shared env template (copy to repo-root .env)
├── .gitignore
└── README.md
```

## GitHub Actions (scaffold)

`.github/workflows/ci.yml` runs on pushes and pull requests to `main` but **only checks out the repository** and echoes that real CI is still to be defined (backend uv/tests, frontend npm/lint/build, Terraform fmt/validate, and so on).

`.github/workflows/deploy-aws.yml` is **manual (`workflow_dispatch`) only** and does **not** call AWS or Terraform. It prints a short checklist for when you add OIDC, secrets, `terraform apply`, image pushes, and static asset publishing.

For OIDC trust policy shaping, see `.github/aws/github-oidc-trust-policy.json.example` and replace `ACCOUNT_ID`, `GITHUB_ORG`, and `REPO` before attaching it to an IAM role.

## Where feature work should land

- **FastAPI routers**: add packages under `backend/app/api/v1/` (or new version folders) and include them from `backend/app/api/router.py`.
- **Agents / LangGraph**: keep graphs, tools, and state machines under `backend/app/services/langgraph/` so onboarding stays predictable.
- **UI routes and data fetching**: colocate routes in `frontend/src/app` (static export friendly) and keep shared helpers in `frontend/src/lib`.
- **Infrastructure growth**: add child modules under `terraform/modules/` (or keep everything flat) and call them from `terraform/main.tf` once you outgrow the four-file scaffold.

## Quality gates (lightweight for now)

```bash
cd frontend && npm run lint && npm run build
```

```bash
cd backend && uv sync && uv run python -m compileall -q app
```

Add pytest, Ruff, or mypy when the API surface grows; the scaffold stays intentionally small.

## Troubleshooting quick hits

- **UI shows “Backend not responding.”** Confirm Uvicorn is listening on `8000`, `CORS_ORIGINS` includes your UI origin, and `NEXT_PUBLIC_API_URL` matches how your browser reaches the API.
- **`docker compose` cannot reach Docker.** Start Docker Desktop (macOS/Windows) or the Linux daemon, then rerun `./scripts/run.sh`.
- **`http://localhost:3000` does nothing.** Confirm the frontend container is up (`docker compose ps`) and check `docker compose logs frontend`. If **`docker compose build frontend`** fails or the container exits with **137**, raise **Memory** in Docker Desktop (Settings → Resources), then rebuild. After **`package-lock.json`** changes, run `docker compose build frontend` (or `./scripts/run.sh` with `--build`) again.
- **Terraform init asks for backend settings.** Create `terraform/backend.hcl` or export `TALENTSTREAM_USE_LOCAL_TF_STATE=1` for disposable local state.
- **GitHub Actions.** The bundled workflows are placeholders only; there is nothing to “fix” for credentials until you replace them with real jobs.


