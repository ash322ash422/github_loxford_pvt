# Deploying TenderExtractor to Azure — from scratch

A clean, from-zero runbook for deploying the backend (FastAPI) and frontend
(Streamlit) as two separate Azure Container Apps, built from everything that
broke (and got fixed) the first time this was done. Follow it in order and
you should not hit any of the errors described in the "Known pitfalls"
section at the bottom — they're folded into the steps themselves.

Contains **no secrets** — every real value comes from your local `.env`,
which is gitignored and never leaves your machine except as Container Apps
secrets (encrypted at rest, never baked into the image).

Written for **Windows Command Prompt** (`cmd.exe`) — `set VAR=value`,
`%VAR%`, `^` for line continuation. If you use PowerShell instead, swap
those for `$env:VAR = "value"`, `$env:VAR`, and backtick continuation.

---

## 0. Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli-windows) installed, then `az login`
- Docker Desktop installed and running
- An Azure subscription you can create resources in
- A filled-in `.env` at the repo root (copy `.env.example` if you haven't) —
  `AZURE_OPENAI_*` and `AZURE_DOCINTEL_*` are required; everything else has
  a sane default

Pick names once and reuse them everywhere below. `STORAGE_ACCOUNT` must be
**globally unique** (lowercase, 3–24 chars) — change it if it's taken.
## NOTE: All following  commands need to be run in  cmd.exe shell, not powershell

```bash
set RESOURCE_GROUP=tender
set LOCATION=centralindia
set ACR_NAME=tenderregistry123
set ENV_NAME=tenderextractor-env
set STORAGE_ACCOUNT=storetender
set BACKEND_APP=tenderextractor-backend
set FRONTEND_APP=tenderextractor-frontend
```

(cmd.exe forgets `set` variables when the window closes — re-run this block
in every fresh terminal session before continuing.)

---

## 1. Resource group, registry, storage (one-time)

```bash
az group create --name %RESOURCE_GROUP% --location %LOCATION%
```

Create the container registry **with admin access enabled from the start**
— doing this after the fact, once a container app is already pointing at
the registry, is the two-step pattern that caused the UNAUTHORIZED pull
error the first time around (see Pitfall #2).

```bash
az acr create --resource-group %RESOURCE_GROUP% --name %ACR_NAME% --sku Basic --admin-enabled true
```

Storage account + 3 file shares (persistent volumes for `data_uploads/`,
`output/`, `logs/` — **not** for the SQLite job store, see Pitfall #3):

```bash
az storage account create --name %STORAGE_ACCOUNT% --resource-group %RESOURCE_GROUP% --location %LOCATION% --sku Standard_LRS

for /f "tokens=*" %i in ('az storage account keys list --resource-group %RESOURCE_GROUP% --account-name %STORAGE_ACCOUNT% --query "[0].value" -o tsv') do set STORAGE_KEY=%i

az storage share create --name data-uploads --account-name %STORAGE_ACCOUNT% --account-key %STORAGE_KEY%
az storage share create --name output --account-name %STORAGE_ACCOUNT% --account-key %STORAGE_KEY%
az storage share create --name logs --account-name %STORAGE_ACCOUNT% --account-key %STORAGE_KEY%
```

Container Apps environment (auto-creates a Log Analytics workspace for you):

```bash
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

az containerapp env create --name %ENV_NAME% --resource-group %RESOURCE_GROUP% --location %LOCATION%
```

Wire the 3 file shares into the environment as named storages — these
names (`data-uploads-storage`, etc.) are what `azure/backend.yaml`'s
`volumes:` section references, so keep them exactly as below:

```bash
az containerapp env storage set --name %ENV_NAME% --resource-group %RESOURCE_GROUP% --storage-name data-uploads-storage --azure-file-account-name %STORAGE_ACCOUNT% --azure-file-account-key %STORAGE_KEY% --azure-file-share-name data-uploads --access-mode ReadWrite

az containerapp env storage set --name %ENV_NAME% --resource-group %RESOURCE_GROUP% --storage-name output-storage --azure-file-account-name %STORAGE_ACCOUNT% --azure-file-account-key %STORAGE_KEY% --azure-file-share-name output --access-mode ReadWrite

az containerapp env storage set --name %ENV_NAME% --resource-group %RESOURCE_GROUP% --storage-name logs-storage --azure-file-account-name %STORAGE_ACCOUNT% --azure-file-account-key %STORAGE_KEY% --azure-file-share-name logs --access-mode ReadWrite
```

Verify all 4 landed:

```bash
az containerapp env storage list --name %ENV_NAME% --resource-group %RESOURCE_GROUP% -o table
```

---

## 2. Build and push both images

Run from the repo root:

```bash
docker build -t %ACR_NAME%.azurecr.io/tenderextractor-backend:latest ./backend
docker build -t %ACR_NAME%.azurecr.io/tenderextractor-frontend:latest ./frontend

az acr login --name %ACR_NAME%

docker push %ACR_NAME%.azurecr.io/tenderextractor-backend:latest
docker push %ACR_NAME%.azurecr.io/tenderextractor-frontend:latest
```

---

## 3. Prepare `azure/backend.yaml`

```bash
copy azure\backend.yaml.example azure\backend.yaml
```

Open `azure/backend.yaml` and fill in every `<PLACEHOLDER>`:

- The `secrets:` block — copy each value straight from your `.env`
  (`AZURE_OPENAI_KEY`, `AZURE_DOCINTEL_KEY`, `AZURE_STORAGE_CONNECTION_STRING`,
  `AZURE_EMAIL_COMMUNICATIONS_STRING`, `AUTH_PASSWORD`, `JWT_SECRET_KEY`).
  If `AUTH_PASSWORD`/`JWT_SECRET_KEY` are blank in `.env`, generate them now:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- Add an `acr-password` secret and a `registries:` block **in this same
  file**, so the very first `containerapp create` already has pull
  credentials — don't create the app first and patch registry creds in
  afterward (Pitfall #2):
  ```bash
  for /f "tokens=*" %i in ('az acr credential show --name %ACR_NAME% --query "username" -o tsv') do set ACR_USERNAME=%i
  for /f "tokens=*" %i in ('az acr credential show --name %ACR_NAME% --query "passwords[0].value" -o tsv') do set ACR_PASSWORD=%i
  echo %ACR_USERNAME%
  echo %ACR_PASSWORD%
  ```
  ```yaml
      secrets:
        # ...your other secrets above...
        - name: acr-password
          value: "<paste %ACR_PASSWORD% here>"
      registries:
        - server: tenderregistry123.azurecr.io
          username: tenderregistry123
          passwordSecretRef: acr-password
  ```
- `image:` → `%ACR_NAME%.azurecr.io/tenderextractor-backend:latest`
- All the plain `env:` values (`NOTIFY_RECIPIENTS`, endpoints, etc.) → from `.env`
- `ingress.allowInsecure: false` must be present explicitly — leaving it
  unset causes a 400 error on this API version (Pitfall #1). It's already
  in the template; don't delete it.
- `scale.minReplicas: 1` must stay `1`, not `0` — this is what keeps
  `local_state/job_flow_status.db` (the SQLite job store) from resetting
  on every scale-to-zero idle cycle (Pitfall #3). Already set correctly in
  the template; don't change it back to `0`.

---

## 4. Deploy the backend

One command, already carrying registry credentials and correct scale —
this avoids the failed-then-patch pattern from Pitfall #2 entirely:

```bash
az containerapp create --resource-group %RESOURCE_GROUP% --name %BACKEND_APP% --environment %ENV_NAME% --yaml azure/backend.yaml
```

Confirm it's actually healthy before moving on:

```bash
for /f "tokens=*" %i in ('az containerapp show --resource-group %RESOURCE_GROUP% --name %BACKEND_APP% --query "properties.configuration.ingress.fqdn" -o tsv') do set BACKEND_URL=%i
echo %BACKEND_URL%
curl https://%BACKEND_URL%/health
```

Expect `{"status":"ok"}`. If you get UNAUTHORIZED or a boolean/JSON error
instead, see "Known pitfalls" below before doing anything else.

---

## 5. Deploy the frontend

The frontend has no YAML manifest — it's simple enough to pass everything
as flags in one `create` call (same principle as step 4: registry creds
included from the very first command):

```bash
az containerapp create ^
  --resource-group %RESOURCE_GROUP% ^
  --name %FRONTEND_APP% ^
  --environment %ENV_NAME% ^
  --image %ACR_NAME%.azurecr.io/tenderextractor-frontend:latest ^
  --target-port 8501 ^
  --ingress external ^
  --registry-server %ACR_NAME%.azurecr.io ^
  --registry-username %ACR_USERNAME% ^
  --registry-password %ACR_PASSWORD% ^
  --env-vars TENDEREXTRACTOR_API_URL=https://%BACKEND_URL% ^
  --min-replicas 1 --max-replicas 1 ^
  --cpu 0.5 --memory 1Gi
```

```bash
for /f "tokens=*" %i in ('az containerapp show --resource-group %RESOURCE_GROUP% --name %FRONTEND_APP% --query "properties.configuration.ingress.fqdn" -o tsv') do set FRONTEND_URL=%i
echo %FRONTEND_URL%
```

(No CORS changes needed — Streamlit's server makes the HTTP calls to the
backend itself, server-side; the browser only ever talks to the Streamlit
origin, so cross-origin rules don't apply here.)

---

## 6. Verify end-to-end

1. Open `https://%FRONTEND_URL%` in a browser.
2. Log in with `AUTH_USERNAME`/`AUTH_PASSWORD` from `.env` — this is the
   bootstrap admin, seeded once into `local_state/users.db` on first
   login against an empty account table. Add any further accounts
   afterward through the frontend's "Manage users" section, not `.env`
   (see README's **Accounts and roles** section).
3. Upload a small PDF (e.g. `backend/data_uploads/01_tender_mini_version.pdf`)
   and let it run the full 2–3 minutes.
4. Confirm it completes and produces a download — this is the real test;
   `/health` returning `ok` only proves the container started, not that a
   full pipeline run (and the SQLite writes it does along the way) works.

---

## 7. Pushing a code change later 

Every time you edit backend code:

### NOTE: Make sure Docker Desktop Engine is running

### NOTE: All following commands need to be run in cmd.exe shell, not powershell


```bash
docker build -t %ACR_NAME%.azurecr.io/tenderextractor-backend:latest ./backend

az acr login --name %ACR_NAME%

docker push %ACR_NAME%.azurecr.io/tenderextractor-backend:latest

az containerapp update --resource-group %RESOURCE_GROUP% --name %BACKEND_APP% --image %ACR_NAME%.azurecr.io/tenderextractor-backend:latest


```

Same pattern for the frontend, swapping the app/image names.

```bash

docker build -t %ACR_NAME%.azurecr.io/tenderextractor-frontend:latest ./frontend

az acr login --name %ACR_NAME%

docker push %ACR_NAME%.azurecr.io/tenderextractor-frontend:latest

az containerapp update --resource-group %RESOURCE_GROUP% --name %FRONTEND_APP% --image %ACR_NAME%.azurecr.io/tenderextractor-frontend:latest

```

### To check status/watch it roll out

```bash
az containerapp revision list --resource-group %RESOURCE_GROUP% --name %FRONTEND_APP% -o table
```

Look for the newest revision with Active: True and TrafficWeight: 100. If it's stuck at 0% traffic or not Active, that usually means the new container failed to start (bad image, crash on boot) — worth checking logs:


### Viewing Logs

```bash
az containerapp logs show --resource-group %RESOURCE_GROUP% --name %FRONTEND_APP% --tail 50
```


### Forcing a restart of container if it does not get updated:

1. Get the current revision name:
   
```bash
az containerapp revision list --resource-group %RESOURCE_GROUP% --name %BACKEND_APP% -o table
```

This prints a table — copy the value under the Name column (something like tenderextractor-backend--xxxxxxx).

2. Restart that revision:
 
```bash
az containerapp revision restart --resource-group %RESOURCE_GROUP% --name %BACKEND_APP% --revision <paste-the-name-here>





**Important:** `--image`-only updates do **not** touch scale settings. If
you ever need to change `minReplicas`/`maxReplicas`, that's a separate call:

```bash
az containerapp update --resource-group %RESOURCE_GROUP% --name %BACKEND_APP% --min-replicas 1 --max-replicas 1
```

---

## Known pitfalls (already designed around, but useful if something still breaks)

1. **`The JSON value could not be converted to System.Boolean`** on
   `containerapp create --yaml` — the CLI silently sends `allowInsecure:
   null` if it's not explicit in the YAML, and this API version rejects a
   null bool. Fix: `ingress.allowInsecure: false` explicit in the manifest
   (already in `azure/backend.yaml.example`).

2. **`UNAUTHORIZED` pulling the image** right after `containerapp create`
   — happens when the registry was created without `--admin-enabled true`,
   or when registry credentials are patched onto an app *after* its first
   (failed) revision. Once a Container App enters `Failed` provisioning
   state, patching it further tends to fail too — the reliable fix is
   `az containerapp delete` and recreate with credentials already in the
   initial `create` call, as steps 4–5 above do.

3. **`sqlite3.OperationalError: database is locked`**, surfacing as a
   `ReadTimeout` from the frontend on upload — SQLite does not work
   reliably over Azure Files (SMB), in *any* journal mode; confirmed via
   two separate failures (`PRAGMA journal_mode=WAL`, then plain `CREATE
   TABLE`). Fix: `config.JOBS_DB` lives under `backend/local_state/`,
   which is deliberately **not** one of the 4 mounted Azure Files volumes
   — it's local container disk. That's why `scale.minReplicas: 1` matters:
   local disk doesn't survive scale-to-zero, so the app needs to just
   never scale to zero. This is already how the code and
   `azure/backend.yaml.example` are set up — just don't add a 5th volume
   mount over `/app/local_state` or drop `minReplicas` back to `0`.

4. **Secrets in the image** — never happens if you follow steps 2–3 as
   written: `.env` is in `.dockerignore` and `.gitignore`, images are built
   from source only, and all real secret values live in Container Apps
   `secrets:` (encrypted, referenced via `secretRef`) rather than baked
   into `env:` or the image layers.
