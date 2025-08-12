# Hackathon Kumo

## College Search (tinder thing)


**Zach Join the Snowflake, I uploaded all the data**



## .env variables
Set these environment variables before running the backend:

- SNOWFLAKE_ACCOUNT
- SNOWFLAKE_USER
- SNOWFLAKE_PASSWORD
- SNOWFLAKE_WAREHOUSE (default: COMPUTE_WH)
- SNOWFLAKE_DATABASE (default: DATA_LAKE)
- SNOWFLAKE_SCHEMA (default: PUBLIC)
- SNOWFLAKE_INSECURE (optional; set to true to relax SSL/OCSP checks if you hit cert errors)
- KUMO_KEY (required for Kumo link-prediction API access)
- JWT_SECRET (set to a strong random string)
- JWT_ISS (default: college-matcher)
- JWT_AUD (default: college-matcher-web)

Example (PowerShell):

```
$env:SNOWFLAKE_ACCOUNT="your_account"
$env:SNOWFLAKE_USER="your_user"
$env:SNOWFLAKE_PASSWORD="your_password"
$env:SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
$env:SNOWFLAKE_DATABASE="DATA_LAKE"
$env:SNOWFLAKE_SCHEMA="PUBLIC"
$env:SNOWFLAKE_INSECURE="false"
$env:KUMO_KEY="your_kumo_api_key"
$env:JWT_SECRET="dev-secret-change-me"
$env:JWT_ISS="college-matcher"
$env:JWT_AUD="college-matcher-web"
```

Example (bash):

```
export SNOWFLAKE_ACCOUNT=your_account
export SNOWFLAKE_USER=your_user
export SNOWFLAKE_PASSWORD=your_password
export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
export SNOWFLAKE_DATABASE=DATA_LAKE
export SNOWFLAKE_SCHEMA=PUBLIC
export SNOWFLAKE_INSECURE=false
export KUMO_API_KEY=your_kumo_api_key
export JWT_SECRET=dev-secret-change-me
export JWT_ISS=college-matcher
export JWT_AUD=college-matcher-web
```

Note: Passwords are salted and hashed (bcrypt) in the backend.

## Run locally

Backend (FastAPI):
- cd `backend`
- Create venv and install deps:
  - Windows PowerShell:
    - `python -m venv .venv`
    - `.\.venv\Scripts\Activate.ps1`
    - `pip install -r requirements.txt`
  - macOS/Linux:
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`
    - `pip install -r requirements.txt`
- Set the environment variables (above)
- Start API: `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`

Frontend (Vite + React):
- cd `frontend`
- `npm install`
- `npm run dev`
- Open `http://localhost:5173`

Notes:
- The Vite dev server proxies `/api/*` to `http://127.0.0.1:8000` (see `frontend/vite.config.ts`).
- Required Snowflake privileges: USAGE on database/schema and SELECT/INSERT/MERGE on `DATA_LAKE.PUBLIC` tables.