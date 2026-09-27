# Tender Extractor

Turns a government tender PDF into a validated Excel summary — upload a
PDF, get back structured spreadsheets a few minutes later:

```
PDF  →  preview OCR + tender check (first pages)  →  not a tender? stop, no output
                                                    ↓ confirmed tender
                    full OCR (Document Intelligence)  →  LLM field extraction  →
                    validate/normalize  →  Excel (+ page usage report)  →
                    publish (local disk or Blob Storage)  →  notify (email)
```

Before paying for anything expensive, the pipeline OCRs just the first few
pages and checks them for tender keywords (`Notice`/`Tender`/`NIT`). Only a
confirmed tender goes on to a full-document OCR pass and LLM extraction —
anything else stops immediately with no Excel output, so a stray non-tender
upload never burns OCR pages or LLM tokens.

It pulls out these kinds of information from each confirmed tender:

- **NIT fields** (Notice Inviting Tender) — dates, amounts, EMD, etc. —
  extracted, then validated/normalized (dates and currency amounts get
  parsed into a consistent format), producing both a clean spreadsheet
  and an audit version (original value + normalized value + valid flag
  side by side, for QA).
- **Misc data** — terms & conditions, permissible makes, and required
  documents — extracted from the full document in page-chunked batches,
  with matching sections (and split tables) merged back together across
  chunk boundaries.
- **Schedule of Quantity** (a.k.a. Schedule of Work / Bill of Quantities)
  — extracted separately from just the last few pages of the document,
  where it reliably lives, via its own dedicated LLM call.
- **An index/table of contents** of the document, extracted from the same
  preview pages used for the tender check, to help guide the rest of the
  pipeline.
- **A page usage report** — this tender's `job_id` and its own OCR page
  count alongside the shared monthly quota (`MAX_PAGES_PER_MONTH`, usage,
  remaining budget, tenders scanned this month, average pages per tender),
  so anyone opening the workbook can see where usage stands without
  checking the API separately.

Everything gets consolidated into one final Excel deliverable per run.

## How it works (upload → result)

What actually happens when a user uploads a PDF, end to end:

1. The user uploads a PDF in the Streamlit UI (or calls `POST /tenders`
   directly). If this month's total OCR page usage is already at/over
   `MAX_PAGES_PER_MONTH`, the upload is rejected immediately with `429` —
   no job is created.
2. The API generates a unique `job_id`, saves the PDF to
   `data_uploads/{job_id}/`, and records a `PENDING` row for it in the
   SQLite job store.
3. The API returns immediately (`202`, with the `job_id`) and queues the
   actual processing as a background task — the HTTP request doesn't wait
   for the pipeline to finish.
4. The background task runs the pipeline stages in order: **preview OCR**
   (just the first `INDEX_CHECK_PAGES` pages) → **index extraction +
   tender check** (keyword match on those same preview pages — a document
   that doesn't look like a tender stops right here with status
   `NOT_A_TENDER`, no further stages run) → **full OCR** (Document
   Intelligence, confirmed tenders only) → **NIT extraction** → **validate
   & normalize** → **NIT Excel export** → **misc extraction** (Terms &
   Conditions / Acceptable Make / Documents to Upload) → **misc Excel
   export** → **Schedule of Quantity extraction** (last few pages only) →
   **Schedule of Quantity Excel export** → **consolidate** → **page usage
   report** → **publish** (local disk or Blob Storage) → **notify**
   (email) — updating the job's status (and live token/page counts) in
   SQLite after each stage. See [Extraction logic](#extraction-logic-how-each-field-gets-found)
   below for how each of these LLM calls actually decides what to extract.
5. The frontend polls `GET /tenders/{job_id}` every 2 seconds, showing the
   current stage, until the job reaches `COMPLETED` (a download button
   appears), `NOT_A_TENDER` (a warning is shown, no download), or `FAILED`
   (the error and which stage broke are shown).
6. Once the pipeline finishes — whatever the outcome — the job-status
   database (`job_flow_status.db`) is pushed to Blob Storage so job history
   stays reachable from outside the running container, falling back to
   logging the current job records if Blob Storage isn't configured or the
   push itself fails (see [Job status DB backup](#job-status-db-backup-to-blob-storage) below).
7. Once the pipeline finishes, a second background task opportunistically
   triggers old-job cleanup if enough time has passed since the last sweep.

## Extraction logic: how each field gets found

Four separate concerns, each with its own page-scoping strategy and its
own LLM call — not one call trying to find everything at once. This
grew out of real bugs: an early version had Terms & Conditions,
Acceptable Make, Documents to Upload, *and* Schedule of Quantity all
sharing one prompt, and the LLM kept misclassifying content between them
whenever it had to scan large, heterogeneous stretches of the document at
once. What follows is current as of this section being written — if
you're adding a new extracted field, skim this first so you don't
reintroduce a bug that was already fixed once.

### Index (`app/services/tender_index_extract_service.py`)
Sent just the first `INDEX_CHECK_PAGES` pages (default 3) — the same OCR
pass used for the tender keyword check (`stage_ocr_preview`). Looks for
page references to Terms & Conditions / Acceptable Make / Documents to
Upload in the document's own index/table of contents, if it has one.
Written to `logs/{job_id}/index.json` for visibility; nothing downstream
currently depends on these page numbers. A more ambitious redesign was
considered - use the index to narrow the *misc* extraction below to just
the relevant page ranges per field, the way Schedule of Quantity is
narrowed by fixed position - but was set aside in favor of the simpler
fixed-position narrowing (works well since Schedule of Quantity's
position is predictable) plus the deterministic filters below (which
directly targeted the bugs actually observed), rather than taking on the
extra complexity of inferring per-field page ranges from an index that
isn't always complete or present.

### NIT fields (`app/services/tender_nit_extract_service.py`)
Sent the first several pages of the *full* OCR pass — NIT fields (dates,
amounts, EMD, officer names, etc.) reliably live near the front of a CPWD
tender. Extracted, then validated/normalized (`app/services/validation.py`
parses dates and currency amounts into a consistent format), then exported
to *two* spreadsheets (`tender_nit_export_excel.py`): an audit version
(original value + normalized value + valid flag, for QA) and a clean
version (just the normalized values, what ships to the reader).

### Terms & Conditions / Acceptable Make / Documents to Upload (`app/services/tender_misc_extraction_service.py`)
Sent the *whole* document, in page-chunked batches of `MISC_PAGES_PER_CHUNK`
pages (default 30) — unlike NIT fields or Schedule of Quantity, these three
can legitimately appear almost anywhere, so there's no reliable page range
to narrow to. This is the field group that took the most iteration to get
right, across several real documents. The prompt and the deterministic
post-processing filters below both exist because of *specific* observed
misclassification bugs, not speculative hardening — each one is a fix for
something that actually happened once:

- **Ragged rows get a loud warning, not a silent fix.** The LLM
  occasionally drops or duplicates a cell while re-typing a table (usually
  a row with an OCR selection-mark artifact, or heavily wrapped text),
  which silently shifts every later cell in that row into the wrong Excel
  column. There's no reliable way to guess which cell went missing, so
  `ExtractedTable`'s Pydantic validator logs a warning identifying the
  table/row instead of guessing — check `logs/{job_id}/ocr.json`'s raw
  Document Intelligence table for the real values if you see one.
- **A Terms & Conditions section can lose its own table.** The LLM
  sometimes classifies a T&C section correctly but simply omits a small
  table that's actually on that page — non-deterministic across identical
  calls, not a prompt-wording problem. If a T&C section ends up with no
  table of its own, `_attach_missing_terms_tables_from_raw_ocr` attaches
  Document Intelligence's own already-parsed table for that page directly
  — copied verbatim, never re-typed by the LLM, so it can't be wrong.
- **Signature blocks, scope-of-work tables, and equipment inventories get
  excluded from Terms & Conditions**, even when the LLM finds them nested
  under a T&C-shaped heading (e.g. "Maintenance of Fire-Fighting System"
  mixing genuine procedural clauses with an embedded equipment inventory
  and a "Work Involved" scope table). `_drop_non_terms_tables_from_terms_and_conditions`
  recognizes these by column-header shape — all-designation columns
  ("Assistant Engineer" / "Executive Engineer"), "Work Involved"/"Scope of
  Work" columns, or an "Item"+"Total" combination — and drops just the
  offending tables, keeping the genuine clauses.
- **Annexures/proforma templates never get summarized into a fabricated
  list.** A blank "Willingness Certificate" that merely *names* a brand
  (as an OEM-authorization fill-in-the-blank) isn't Acceptable Make, even
  though a brand name is technically present on the page — the LLM was
  once caught inventing a 3-item "Acceptable Make" list by summarizing
  what three such certificate pages were about, rather than quoting them.

### Schedule of Quantity (`app/services/tender_soq_extract_service.py`)
Deliberately **separate** from the three fields above, sent only the
**last** `SOQ_LAST_PAGES` pages (default 5) in one dedicated, narrowly
scoped LLM call. This used to be a fourth field sharing the big
multi-purpose call above — which is exactly what caused it to repeatedly
pick up other pages' tables (a proforma index page's heading glued onto an
unrelated rate table found elsewhere; a Terms & Conditions page's small
example-rates table; the same rows described twice, once as plain items
and once as a table). Narrowing the input to just the pages where it
actually lives fixed that whole class of bug by construction, instead of
needing yet another exclusion rule layered onto an already-long prompt.
Its schema also has no `items` field at all — Schedule of Quantity is
inherently tabular, so there's no way for the same row to get described
twice in two different shapes. Still backed by one deterministic filter:
`_drop_non_quantity_tables` drops any table without an explicit
Quantity/Qty column, since that's the one thing that actually makes a
schedule of *quantity* a schedule of quantity (rather than, say, an
unrelated rate table that happened to be in the last few pages).

### Iterating on extraction logic without re-paying for OCR
`logs/{job_id}/ocr.json` and `ocr_preview.json` are the full,
already-paid-for Document Intelligence output for any job that's gone
through the real pipeline at least once. To test a prompt or filter change
against real tender data without a new OCR call (or without re-running
extraction stages you're not touching):

```bash
cd backend
python -m scripts.rerun_from_cached_ocr JOB_ID --misc   # or --nit, --index, --soq, --all
```

Overwrites that job's own `logs/{job_id}/*.json` audit files and
`output/{job_id}/` deliverables in place — the same paths `run_pipeline()`
itself would have written. This is how every extraction bug fix described
above was actually verified against real tender data before being
considered done; see the script's own docstring for the full option list.

## Architecture at a glance

Backend and frontend are **fully separate**:

- `backend/` — a FastAPI REST API (`app/api/main.py`) wrapping the
  extraction pipeline, plus a CLI (`main.py`) for local/batch use. This is
  where all the logic, Azure calls, and data live.
- `frontend/streamlit_app.py` — a plain HTTP client of the backend's REST
  API. It never imports backend code, so it can run against a backend on a
  completely different host/process/deployment. It logs in first
  (single-user JWT auth) and attaches the token to every request after that.

You can run just the backend (CLI or API), or backend + frontend together,
locally or in containers, or deployed to Azure. All of these are covered below.

---

## Prerequisites

- Python 3.11+
- An **Azure OpenAI** deployment and an **Azure AI Document Intelligence**
  resource — both required; the pipeline can't run without them
- Optional: Azure Blob Storage (falls back to local disk if not configured),
  Azure Communication Services or Gmail for email notifications
- Docker Desktop, only if you want to run it in containers

## Quick start (local, no containers)

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
python -m pip install -r backend/requirements.txt
python -m pip install -r frontend/requirements.txt   # only needed to run the Streamlit UI

cp .env.example .env
# Fill in AZURE_OPENAI_* and AZURE_DOCINTEL_* at minimum, and AUTH_PASSWORD
# (see ## Configuration below — the API refuses ALL logins until AUTH_PASSWORD is set)
```

`requirements.txt` in each directory is the loose, human-edited dependency
list; `requirements.lock.txt` is a fully pinned `pip freeze` snapshot of
it, and is what the Docker images actually install from for reproducible
builds. Use `pip install -r backend/requirements.lock.txt` instead if you
want your local environment to exactly match what's deployed. Regenerate
a lock file after changing its `requirements.txt`:

```bash
python -m venv /tmp/lockenv && /tmp/lockenv/Scripts/pip install -r backend/requirements.txt
/tmp/lockenv/Scripts/pip freeze > backend/requirements.lock.txt
```

Then either:

**Option A — CLI**, no server, no auth, good for a quick local test:

```bash
# drop PDF(s) into backend/data_uploads/, then:
python backend/main.py                                    # processes every PDF there
python backend/main.py --file 01_tender_mini_version.pdf  # or just one
```

**Option B — REST API + Streamlit UI**, the same setup the production
deployment uses:

```bash
cd backend && uvicorn app.api.main:app --reload   # terminal 1 — http://127.0.0.1:8000
streamlit run frontend/streamlit_app.py           # terminal 2 — http://localhost:8501
```

Log in to the Streamlit UI with `AUTH_USERNAME`/`AUTH_PASSWORD` from
`.env` - the first time the API runs against an empty account table, it
seeds exactly one admin account from those two values (see Configuration
below). From then on, manage accounts (add, delete, change password)
through the frontend's "Manage users" section (admin only) or the
`/users*` endpoints directly - not by editing `.env` again.
API docs (Swagger UI, with a working "Authorize" button) are at
`http://127.0.0.1:8000/docs`.

Every run — CLI or API — is isolated by a generated `job_id`, so two jobs
(or two uploads that happen to share a filename) never collide:

- `backend/data_uploads/{job_id}/<name>.pdf` — this run's own copy of the source PDF
- `backend/output/{job_id}/<name>.xlsx` (clean) and `<name>.nit_audit.xlsx`
  (audit version, see above) — this run's deliverables
- `backend/logs/{job_id}/` — an immutable audit copy of each stage's output
  (OCR text, extracted fields, etc.) for this specific run, so "how was
  this result obtained" stays answerable later

Every run always calls Document Intelligence and the LLM fresh — there's
no on-disk cache that skips repeat calls for a file you've already
processed. This keeps results always current for whatever file you
uploaded, at the cost of re-paying for OCR/LLM calls if you reprocess the
same PDF.

Progress for every run is tracked in `backend/local_state/job_flow_status.db`
(SQLite), keyed by `job_id`. Each row records `token_count` (total LLM
tokens spent) and `ocr_page_count` (pages actually sent to Document
Intelligence) for that run. Print a summary across every recorded job:

```bash
cd backend && python -m scripts.print_token_usage
```

## Configuration (`.env`)

Copy `.env.example` to `.env` and fill it in. Everything not listed as
required has a working default.

| Variable | Default | Notes |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_KEY` / `AZURE_OPENAI_DEPLOYMENT` | — | **Required.** Field extraction won't work without these. |
| `AZURE_DOCINTEL_ENDPOINT` / `AZURE_DOCINTEL_KEY` | — | **Required.** OCR won't work without these. |
| `AUTH_USERNAME` / `AUTH_PASSWORD` | `admin` / *(blank)* | **Bootstrap admin seed only** — used once, to create the first admin account when `local_state/users.db` is still empty. Manage every account after that through `/users*` (or the frontend's admin UI), not `.env`. **Blank password = nobody can ever log in** (fails closed, not open) — set this before the first run. |
| `JWT_SECRET_KEY` | random per process | Set this or every login token breaks on the next server restart. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime. |
| `MISC_PAGES_PER_CHUNK` | `30` | Batch size (pages) for the misc-data extraction pass. |
| `MAX_UPLOAD_SIZE_MB` | `10` | `POST /tenders` rejects anything larger with a `413`. |
| `INDEX_CHECK_PAGES` | `3` | How many leading pages get OCR'd for the tender pre-check (keyword match) and fed to the index-extraction LLM call. |
| `SOQ_LAST_PAGES` | `5` | How many trailing pages get sent to the Schedule of Quantity LLM call — it reliably lives near the end of the document, so this is deliberately narrow rather than scanning everything. |
| `MAX_PAGES_PER_MONTH` | `10000` | Shared monthly OCR page budget across all jobs, bucketed by calendar month in IST. `POST /tenders` returns `429` once this month's usage is already at/over the limit; reported in every tender's "Page Usage Report" Excel sheet. |
| `UPLOAD_RETENTION_DAYS` | `7` | Days before a job's `data_uploads/{job_id}/` is deleted by cleanup. |
| `OUTPUT_LOGS_RETENTION_DAYS` | `30` | Days before a job's `output/{job_id}/` + `logs/{job_id}/` are deleted. |
| `CLEANUP_MIN_INTERVAL_DAYS` | `1` | How often the opportunistic cleanup sweep is allowed to actually run. |
| `CORS_ALLOWED_ORIGINS` | `localhost:3000,localhost:8501` | Only matters for a browser-based frontend calling the API directly (e.g. a future React app) — Streamlit's requests are server-to-server, not subject to CORS. |
| `AZURE_STORAGE_CONNECTION_STRING` | — | Optional. If set, the finished Excel is uploaded to Blob Storage and `download_url` becomes a time-limited SAS link (see `URL_EXPIRY_HOURS`) — that's the link emailed via `NOTIFY_ON_COMPLETE`. If unset, the pipeline just leaves Excel output on local disk and `download_url` points there instead. |
| `NOTIFY_ON_COMPLETE` / `NOTIFY_RECIPIENTS` | `false` / — | Email a recipient list when a run completes — needs either the Azure Communication Services or Gmail vars filled in below it. |
| `TENDEREXTRACTOR_API_URL` | `http://127.0.0.1:8000` | Frontend-only: where Streamlit should find the API. |

## Running with Docker

Two images, built from the repo root:

```bash
docker build -t tenderextractor-backend ./backend
docker build -t tenderextractor-frontend ./frontend
```

Or both together, with volumes so the output/job-history persist across restarts:

```bash
docker compose up --build
# Backend  -> http://localhost:8000  (docs at /docs)
# Frontend -> http://localhost:8501
```

Both are long-running servers — there's no separate job/cron container.
Old-job cleanup runs *inside* the backend process itself (see below), and
`docker-compose.yml` reads secrets from the repo-root `.env`. Both
Dockerfiles install from `requirements.lock.txt`, not `requirements.txt`,
so builds are reproducible — see the note in Quick start above.

## API reference

`app/api/main.py` is a thin FastAPI wrapper around `run_pipeline()`. Each
upload runs in a background task so the HTTP request returns immediately
with a `job_id`; the frontend polls status from there. Every endpoint
except `/login` and `/health` requires a JWT from `/login`; the `/users`
collection endpoints additionally require the caller's token to carry the
`admin` role (see [Accounts and roles](#accounts-and-roles-users) below).

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| POST | `/login` | – | Form-encoded `username`+`password`, checked against the account table (`app/services/user_store.py`). Returns `{access_token, token_type}`. |
| POST | `/tenders` | ✓ | Upload a PDF (multipart `file`, max `MAX_UPLOAD_SIZE_MB`, `413` if exceeded). Returns `{job_id, blob_name, status}` immediately (202) and starts processing in the background. `429` if this month's OCR page usage is already at/over `MAX_PAGES_PER_MONTH` — no job is created. |
| GET | `/tenders` | ✓ | List every job, most recent first. |
| GET | `/tenders/{job_id}` | ✓ | Status/details for one job (poll this for progress) — see `JobResponse` fields below. |
| GET | `/tenders/{job_id}/download` | ✓ | Finished Excel file — redirects to the Blob SAS URL, or streams the local file, depending on whether `AZURE_STORAGE_CONNECTION_STRING` is set. `409` if the job isn't `COMPLETED` yet (includes `NOT_A_TENDER`, which never produces a download). |
| GET | `/users/me` | ✓ | Current account's `{username, role, created_at, updated_at}`. |
| GET | `/users` | admin | List every account. |
| POST | `/users` | admin | Create an account: `{username, password, role}` (`role` is `"admin"` or `"user"`, default `"user"`). `409` on a duplicate username. |
| DELETE | `/users/{username}` | admin | Delete an account. `404` if missing; `400` if it's the caller's own account, or the last remaining admin. |
| PUT | `/users/{username}/password` | admin | Reset anyone's password — `{new_password}`, no current-password check. |
| PUT | `/users/me/password` | ✓ | Change your own password — `{current_password, new_password}`. `401` if `current_password` is wrong. |
| GET | `/health` | – | Liveness check, no auth. |

### Accounts and roles (`/users*`)

Accounts are rows in `local_state/users.db` (`app/services/user_store.py`),
not `.env` — see the `AUTH_USERNAME`/`AUTH_PASSWORD` note in Configuration
above for how the *first* admin account gets created. Each account has a
`role` of `admin` or `user`: an admin can list/create/delete accounts and
reset anyone's password; a regular user can only read their own account
(`GET /users/me`) and change their own password (`PUT /users/me/password`).
Passwords are hashed with bcrypt (`app/services/auth.py`), never stored or
returned in plaintext.

The JWT issued by `/login` carries the account's `role` as a claim,
trusted for that token's lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES`, default
60 minutes) rather than re-checked against the database on every request —
the same stateless-JWT tradeoff the app already made for identity, just
now also covering role. Deleting a user or changing their role only takes
effect once their current token expires or they log in again.

`JobResponse` (what `GET /tenders` and `GET /tenders/{job_id}` return):
`job_id`, `blob_name`, `status` (`PENDING` → `STARTED` → `{stage}_done` →
`COMPLETED` / `NOT_A_TENDER` / `FAILED` — `NOT_A_TENDER` means the tender
pre-check ruled the document out; it's a valid outcome, not a failure, so
`failed_stage` stays `null`), `error`, `failed_stage`, `download_url`,
`token_count`, `ocr_page_count`, `created_at`, `updated_at`, `completed_at`
(all three timestamps in India Standard Time, `IST`, `UTC+5:30` — as are log
file timestamps and the "Page Usage Report" sheet's timestamps; the app
deliberately doesn't use UTC anywhere it prints a time, see `config.IST`).

Send the token as `Authorization: Bearer <token>` on every protected call.
Interactive docs (Swagger UI) are at `/docs` once the server is running —
its "Authorize" button calls `/login` for you.

## Cleanup, without a scheduler

`scripts/cleanup_old_jobs.py` deletes a job's `data_uploads/{job_id}/` once
older than `UPLOAD_RETENTION_DAYS`, and its `output/{job_id}/` +
`logs/{job_id}/` once older than `OUTPUT_LOGS_RETENTION_DAYS` — measured
from `completed_at`, falling back to `created_at` so stuck/failed jobs
still get cleaned up eventually. It never touches `job_flow_status.db` rows
— kept indefinitely, tiny, and your usage history.

The backend triggers this **on its own** — every `POST /tenders` queues a
second background task, after the pipeline finishes, that calls
`cleanup_if_due()`. It's gated to run at most once every
`CLEANUP_MIN_INTERVAL_DAYS` (tracked via a marker file, not a calendar
check), wrapped in its own try/except so a cleanup bug can never affect a
job's result, and cheap when it's not due (one SQLite read + a few
timestamp comparisons). No separate container, cron, or scheduler needed —
it travels with the backend wherever that's deployed.

You can still run it by hand any time:

```bash
cd backend && python -m scripts.cleanup_old_jobs --dry-run   # preview
cd backend && python -m scripts.cleanup_old_jobs             # actually delete, ignoring the interval gate
```

## Job status DB backup to Blob Storage

`local_state/job_flow_status.db` lives on local container disk only (see
Known issues below) and doesn't survive a restart on its own. At the end of
every pipeline run — regardless of outcome (`COMPLETED`, `NOT_A_TENDER`, or
`FAILED`) — the whole file is pushed to the `AZURE_STORAGE_CONTAINER_OUTPUT`
Blob container (same container the finished Excel goes to) under a fixed
blob name, overwriting the previous copy, so job history stays reachable
from outside the running container.

**Give local development its own `AZURE_STORAGE_CONTAINER_OUTPUT`,
separate from production's** (e.g. `automation-file-processed-dev` locally
vs. `automation-file-processed` in `azure/backend.yaml`). Since the blob
name is fixed, a local run and the real deployment sharing the same
`AZURE_STORAGE_CONNECTION_STRING`/container would otherwise silently
overwrite each other's `job_flow_status.db` backup (and mix dev/test
tenders into production's Excel output too) — this is a real thing that
happened once during development, not a hypothetical. Azure creates the
new container automatically on first upload (`get_or_create_container`),
so this needs nothing beyond the `.env` change.

If Blob Storage isn't configured (`AZURE_STORAGE_CONNECTION_STRING` unset)
or the push itself fails, the pipeline doesn't fail because of it — it logs
the current job records to `logs/app.log` instead, as a best-effort
fallback for visibility. See `app/services/job_db_backup.py`.

## Deploying to Azure

Full from-scratch runbook: **[AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md)** —
covers creating the resource group, container registry, storage, and
Container Apps environment; building and pushing both images; filling in
`azure/backend.yaml`; deploying backend and frontend; and how to push a
later code change. It also documents (with the fix baked into the steps)
every real error hit setting this up the first time: an `allowInsecure`
boolean quirk in the Container Apps API, an ACR pull-auth ordering issue,
and — most importantly — that **SQLite does not work reliably over Azure
Files (SMB)**, which is why `job_flow_status.db` deliberately lives on
local container disk (`local_state/`) rather than a mounted volume, and
why the production config runs with `minReplicas: 1` (no scale-to-zero) —
see Known issues below.

## Known issues / things to be mindful of

- **Every run always calls Document Intelligence and the LLM fresh** —
  there's no on-disk cache. Re-uploading the same PDF re-pays for OCR/LLM
  calls rather than reusing a prior result; per-job audit copies under
  `logs/{job_id}/` are the recovery mechanism if you need to see what an
  earlier run actually extracted.
- **Uploads are capped at `MAX_UPLOAD_SIZE_MB` (default 10 MB)** —
  `POST /tenders` returns `413` for anything larger, checked before the
  file is written to disk.
- **Blank `AUTH_PASSWORD` means login always fails**, by design (fails
  closed) — this isn't a bug, but it's a common first-run gotcha.
- **Blank `JWT_SECRET_KEY` invalidates every session on restart** — a new
  random key is generated per process if it's not set.
- **`local_state/job_flow_status.db` lives on local disk, not shared
  storage.** In any deployment with more than one replica or with
  scale-to-zero enabled, don't assume job history/status survives a
  restart unless you've deliberately pinned `minReplicas >= 1` (see
  AZURE_DEPLOYMENT.md). This is intentional — SQLite doesn't work
  reliably over network filesystems like Azure Files/NFS — not an
  oversight. It's mirrored to Blob Storage after every pipeline run as a
  best-effort backup (see **Job status DB backup to Blob Storage** above),
  but that's an async, after-the-fact copy taken once per run — not a
  substitute for `minReplicas >= 1` if you need in-flight status to
  survive a mid-run restart.
- **`local_state/users.db` (accounts) has the same local-disk-only
  constraint as `job_flow_status.db` above, but no Blob Storage backup.**
  Losing that container's disk — no `minReplicas >= 1`, or a redeploy that
  doesn't preserve `local_state/` — resets every account: the table comes
  back empty, and the next login re-seeds a single bootstrap admin from
  whatever `AUTH_USERNAME`/`AUTH_PASSWORD` are in `.env` at that moment.
  Any other accounts created since then are gone and have to be re-added
  through `/users`.
- **A JWT's `role` claim is trusted for that token's lifetime**
  (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 60 minutes), not re-checked
  against `users.db` per request — see **Accounts and roles** above.
  Deleting a user or demoting an admin doesn't invalidate a token they're
  already holding; it just stops working the next time they log in.
- **The tender pre-check is a simple keyword heuristic, not a
  classifier** — case-insensitive, word-boundary match for
  `Notice`/`Tender`/`NIT` in the first `INDEX_CHECK_PAGES` pages. It can
  false-negative (an unusual tender that doesn't use those words up
  front) or false-positive (e.g. an unrelated document mentioning "NIT
  Warangal" or generic legal "Notice" boilerplate). A `NOT_A_TENDER`
  result is final — nothing retries it automatically.
- **`MAX_PAGES_PER_MONTH` enforcement is a simple pre-check, not a hard
  lock.** `POST /tenders` only checks usage *before* accepting an upload —
  two uploads landing at the threshold at nearly the same time can jointly
  push usage over the cap once both pipelines run.
- **The misc extraction (Terms & Conditions / Acceptable Make / Documents
  to Upload) is the least deterministic part of the pipeline.** The same
  cached OCR input has produced different results across separate runs in
  practice (a table present on one call, missing on the next). The
  deterministic filters described in
  [Extraction logic](#extraction-logic-how-each-field-gets-found) catch
  every *specific* misclassification pattern seen so far, but that list
  isn't exhaustive — a genuinely new failure shape could still slip
  through. If you spot one, `logs/{job_id}/misc.json` plus
  `logs/{job_id}/ocr.json` (Document Intelligence's own raw parse, usually
  the ground truth) is the fastest way to diagnose it, and
  `scripts/rerun_from_cached_ocr.py` lets you iterate on a fix without
  paying for OCR again.
- **The CLI (`backend/main.py`) has no auth and no CORS.** It's meant for
  trusted local/batch use, not for exposing over a network — only the
  FastAPI app (`app/api/main.py`) is meant to be reachable remotely.
- **Never commit `.env` or `azure/backend.yaml`** — both are gitignored
  already (they hold real API keys/passwords), and neither is baked into
  either Docker image. Double-check `git status` before pushing to a
  public GitHub repo, especially after adding new config.
- **Uploaded PDFs and output may contain sensitive tender data.**
  `backend/data_uploads/`, `output/`, and `logs/` are gitignored for real
  content — but if you ever change how those directories are laid out,
  re-check `.gitignore` actually matches the new paths. A stale
  `.gitignore` here once let real generated Excel files and other output
  get committed to git history before anyone noticed.
- **Blob Storage, when configured, only holds the finished Excel** — the
  source PDF is never mirrored or copied there. `AZURE_STORAGE_CONNECTION_STRING`
  set gets you a durable copy of the *output* plus a shareable SAS
  download link; it says nothing about the input PDF's storage.
- **Cleanup deletes files, never `job_flow_status.db` rows.** Job history
  grows forever (harmless — rows are tiny), but disk usage for
  uploads/output/logs is bounded by the retention settings above.

## Layout

```
backend/
  app/
    config.py               # the only module that reads os.environ
    api/
      main.py                 # FastAPI app: upload/status/download endpoints
      schemas.py               # request/response models
    pipeline/
      context.py             # PipelineContext - the object passed between stages
      exceptions.py           # TenderCheckStopped - raised when the pre-check gate rules a doc out
      stages.py               # one function per pipeline step
      runner.py               # runs the stages in order, updates job status
    services/                # one file per external concern, no pipeline knowledge
      blob_storage.py
      document_intelligence.py
      llm.py
      prompt.py                          # NIT field list (FIELDS_TO_EXTRACT)
      tender_detection.py                 # keyword check used by the tender pre-check gate
      tender_index_extract_service.py      # index/table-of-contents page references
      tender_nit_extract_service.py        # NIT field extraction (dates, amounts, EMD, etc.)
      tender_nit_export_excel.py           # NIT -> audit + clean spreadsheets
      tender_misc_extraction_service.py    # Terms & Conditions / Acceptable Make / Documents to Upload
      tender_misc_export_excel.py          # misc extraction -> one sheet per field
      tender_soq_extract_service.py        # Schedule of Quantity - separate call, last few pages only
      tender_soq_export_excel.py           # Schedule of Quantity -> its own sheet
      validation.py                        # date/currency normalization for NIT fields
      page_usage_report.py     # builds the "Page Usage Report" Excel sheet
      consolidate_excels_files.py
      email_service.py
      job_store.py            # SQLite-backed job status, keyed by job_id
      job_db_backup.py         # pushes job_flow_status.db to Blob Storage after each run
      auth.py                  # JWT login/verification, password hashing
      user_store.py             # SQLite-backed accounts (users.db), keyed by username
    utils/
      logging_config.py
  main.py                    # CLI: discovers PDFs and runs the pipeline over them
  scripts/                   # dev-only utilities
    cleanup_old_jobs.py         # deletes past-retention job folders - triggered by the API itself, see ## Cleanup
    print_token_usage.py        # summarizes token_count/ocr_page_count across every recorded job
    rerun_from_cached_ocr.py    # re-run extraction from a job's saved OCR, no new Document Intelligence call - see ## Extraction logic
  tests/
  data_uploads/{job_id}/       # each run's own copy of its source PDF
  output/{job_id}/              # each run's own Excel deliverables (.nit_audit.xlsx, .nit_clean.xlsx, .misc.xlsx, .soq.xlsx, and the final consolidated .xlsx)
  logs/                          # app.log, logs/.cleanup_last_run, and logs/{job_id}/ per-run audit copies
  local_state/                   # job_flow_status.db + users.db (SQLite) - local disk only, not network-mounted
  Dockerfile                  # backend image build - see ## Running with Docker
  requirements.txt            # loose, human-edited dependency list
  requirements.lock.txt       # pinned `pip freeze` snapshot - what Docker actually installs
frontend/
  streamlit_app.py            # browser UI; talks to app/api/main.py over HTTP only
  Dockerfile
  requirements.txt
  requirements.lock.txt
azure/
  backend.yaml.example        # Container Apps manifest template - see AZURE_DEPLOYMENT.md
docker-compose.yml
AZURE_DEPLOYMENT.md           # full from-scratch Azure deployment runbook
```

**Services** know how to talk to one external thing (Blob Storage, Document
Intelligence, the LLM, email) and nothing about tenders or the pipeline.
**Stages** know the tender domain and call one or two services each.
**The runner** knows the *order* of stages; nothing else does.

## Why it's structured this way

- **Modular** — each stage is a plain function `stage_x(ctx) -> None`. Add a
  step by writing one function and adding one line to `STAGES` in
  `runner.py`. Nothing else has to change.
- **Scales to a batch** — `main.py` loops over every PDF in `data_uploads/`,
  and one tender failing doesn't stop the rest. Each *run* gets its own row in
  `local_state/job_flow_status.db` and its own `data_uploads/{job_id}/` and
  `output/{job_id}/` folders, so concurrent/repeated runs never collide —
  including in Blob Storage, when configured (`stage_publish` uploads
  under `{job_id}/<name>.xlsx` in the processed container).
- **Traceable, not cached** — every run calls Document Intelligence and the
  LLM fresh rather than reusing a prior result for the same filename, so
  results are always current for whatever was actually uploaded. What a
  *specific* run's intermediate output looked like (OCR text, extracted
  fields) is still recoverable afterward, from the always-written
  `logs/{job_id}/` audit copies — that's the traceability mechanism, not
  a cache to invalidate.
- **Degrades gracefully** — if `AZURE_STORAGE_CONNECTION_STRING` isn't set,
  the `publish` stage just leaves the Excel file in `output/{job_id}/`
  instead of failing (and the job-DB backup falls back to logging instead
  of uploading, same principle). Good for local development; nothing to
  configure for a POC.
- **Cost-conscious by default** — a cheap few-page OCR + keyword check
  runs before any full-document OCR or LLM call, so a non-tender upload
  never pays for either. Page usage against a shared monthly budget
  (`MAX_PAGES_PER_MONTH`) is tracked, reported in every tender's own
  workbook, and enforced at upload time.
- **Not over-engineered** — no web framework beyond FastAPI itself, no
  async pipeline, no class hierarchies. It's a list of functions run in
  order. That's the whole abstraction, which is enough for a linear
  document pipeline like this one.

## Adding a new field to extract

Where a new field goes depends on which of the four extraction concerns
in [Extraction logic](#extraction-logic-how-each-field-gets-found) it
belongs to:

- **A new NIT field** (a single scalar value near the front of the
  document, like an existing date/amount/name field):
  1. Add `{"name": ..., "description": ...}` to `FIELDS_TO_EXTRACT` in
     `backend/app/services/prompt.py`.
  2. If it's a date or currency amount, add its exact name to
     `DATE_FIELDS` / `AMOUNT_FIELDS` in `backend/app/services/validation.py`
     so it gets normalized automatically. Otherwise it's carried through
     as-is.
- **A new misc field** (Terms & Conditions-shaped: sections with
  items/tables/notes, could appear almost anywhere in the document): add
  it to `TenderExtraction` and `SYSTEM_PROMPT` in
  `tender_misc_extraction_service.py`, and to `FIELD_TO_SHEET_TITLE` in
  `tender_misc_export_excel.py`. Expect to iterate - this file's real
  history is several rounds of "the LLM over/under-included content" bug
  fixes, each backed by a deterministic filter, not just prompt wording.
  Read the misc section of [Extraction logic](#extraction-logic-how-each-field-gets-found)
  before starting.
- **A field with a known, narrow page range** (like Schedule of Quantity -
  reliably near the front or back, not spread across the whole document):
  give it its own extract-service/export-service pair rather than folding
  it into the misc call, following `tender_soq_extract_service.py` /
  `tender_soq_export_excel.py` as the template. A focused prompt over a
  handful of pages is both cheaper and far less error-prone than adding
  yet another field to the already-large misc prompt.

## Tests

```bash
cd backend && pytest tests/
```

Covers prompt building, chunk-merging, field validation, the SQLite job
store (including the monthly usage queries), the tender pre-check gate
(keyword matching and the `NOT_A_TENDER` short-circuit through
`run_pipeline`), the page usage report, the job-DB Blob Storage backup,
every deterministic misc/Schedule-of-Quantity filter described in
[Extraction logic](#extraction-logic-how-each-field-gets-found) (regression
tests for each real bug they fix), and the API's
login/upload/status/download/quota contract (with `run_pipeline` mocked
where relevant, so these never touch Azure) — everything that doesn't need
live Azure credentials to test.

**If your local `.env` has real Azure credentials** (needed to test Blob
Storage / Document Intelligence / OpenAI features locally), be careful:
`config.py` loads it unconditionally at import, so any test that reaches
the real `run_pipeline()` — via a live `POST /tenders` call or otherwise —
without mocking `run_pipeline` itself, or without resetting
`AZURE_STORAGE_CONNECTION_STRING` to `None`, will make real calls with
real credentials. This isn't hypothetical: a test in `test_api.py` once did
exactly this and pushed a throwaway test database to the real Blob Storage
container. Any fixture whose tests can reach `run_pipeline()` or Blob
Storage (see `test_api.py`, `test_stages.py`, `test_runner.py`) resets
`AZURE_STORAGE_CONNECTION_STRING` to `None` for this reason — keep that
pattern when adding new tests that touch the API or the pipeline.
