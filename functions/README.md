# Grading Cloud Function

Python 3.12 HTTPS function that backs the website's `/api/grade` endpoint.
Firebase Hosting rewrites `/api/**` here (see `../firebase.json`).

## What lives where

- `main.py` — the authenticated `api` HTTPS function. It verifies the Firebase
  ID token, enforces account quotas, resolves the trusted question record,
  shapes the browser's wasm parse into `parsed-answer/v1`, and calls the grader.
- `rate_limit.py` — pure fixed-window quota logic. The function stores each
  account's counters under a server-only Realtime Database path in one atomic
  transaction.
- `requirements.txt` — Firebase SDKs only; the grading code is pure stdlib.
- `sync_pipeline.py` — copies `src/pipeline/grading/*` and the trusted question
  records into `functions/` so the upload is self-contained. Runs automatically
  via the `predeploy` hook.
- `grading/` — **generated** (gitignored). Do not edit; edit the source under
  `src/pipeline/grading/` and re-run the sync.

## The secret

The OpenRouter key is never in code or in the client bundle. Set it once:

```bash
firebase functions:secrets:set OPENROUTER_API_KEY
```

Without the secret, grading returns a deterministic dry-run result.

## Account quotas

AI grading defaults to 8 submissions per 10 minutes and 50 per day, per
authenticated Firebase account. Override these runtime environment values when
needed:

- `GRADE_BURST_LIMIT` (default `8`)
- `GRADE_BURST_WINDOW_SECONDS` (default `600`)
- `GRADE_DAILY_LIMIT` (default `50`)
- `GRADE_DAILY_WINDOW_SECONDS` (default `86400`)

Rate-limit state is not client-readable or client-writable; Admin SDK access
bypasses the database's default-deny rules. A limited response uses HTTP 429
with `Retry-After`, `RateLimit-Policy`, and remaining-quota headers.

Run the boundary and quota tests inside the Functions virtual environment:

```bash
functions/venv/bin/python -m unittest functions.test_main tests.test_rate_limit
```

## Local run

The Functions emulator needs a virtual environment with the SDK installed at
`functions/venv` (gitignored). One-time setup:

```bash
cd functions
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
cd ..
```

Then, from the repo root:

```bash
python3 functions/sync_pipeline.py          # populate functions/grading/
# grading key for the emulator (gitignored): functions/.secret.local
#   OPENROUTER_API_KEY=sk-or-...
firebase emulators:start --only functions,hosting
```

`npm run emulate` wraps the sync + build + full suite (but not the venv setup).

## Deploy

```bash
firebase deploy --only functions
```
