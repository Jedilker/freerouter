# FreeRouter

FreeRouter is a small, self-hosted API that selects a configured model name using transparent prompt-complexity rules. It returns a routing decision; it does **not** call OpenAI, Anthropic, or other model providers, forward prompts, provide provider fallback, or calculate cost savings. Your application sends the prompt to the selected provider.

The canonical application is the FastAPI service in `main.py`. The legacy Node/haiku and static starter files in the repository are not part of this API.

## What it provides

- Deterministic budget/quality model selection, configurable with `ROUTER_BUDGET_MODEL` and `ROUTER_QUALITY_MODEL`.
- Supabase Auth registration and login, with randomly generated API keys.
- SHA-256 hashes of API keys at rest; the plaintext key is returned only once at creation.
- Per-user API-key validation and analytics. Prompt text is never written to the database.
- A small dashboard with no third-party JavaScript or CSS dependencies.
- A bounded analytics sample (the most recent 1,000 requests) for model distribution and average routing-decision latency.

The routing rules are a starter heuristic, not a trained classifier or a quality guarantee. Test them against your own workload before relying on their decisions.

## Run locally

Use Python 3.10 or newer:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

Create a Supabase project and apply [`schema.sql`](schema.sql) in its SQL editor. It migrates legacy plaintext API keys to hashes and removes the old plaintext key and prompt columns. Back up the database first if those legacy values must be retained. Configure the project URL, public Auth key, and server-side service-role key (never expose the service-role key in a browser or commit it):

```text
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVER_SIDE_SERVICE_ROLE_KEY
ROUTER_BUDGET_MODEL=your-provider/your-low-cost-model
ROUTER_QUALITY_MODEL=your-provider/your-capable-model
```

For example, set these as environment variables in your shell or deployment platform. Start the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/` for the dashboard and `/docs` for the OpenAPI docs. `/health` is a liveness endpoint; it does not verify Supabase connectivity.

## API flow

1. `POST /auth/register` with `{"email":"you@example.com","password":"at-least-8-characters"}`.
2. `POST /auth/login-and-generate-key` with the same credentials. Keep the returned `api_key` secret; it cannot be retrieved later. Generate another key after losing one, then deactivate the lost key by setting its `is_active` field to `false` in Supabase.
3. Call `POST /route` with `x-api-key: sk_live_...` and a JSON body such as:

```json
{"prompt":"Explain what an HTTP status code is."}
```

The response contains `target_model`, `routing_reason`, and `latency_ms`. The latency measures only the local routing decision, not an inference call or database write. Use `target_model` to select your provider/model and submit the original prompt yourself.
4. Call `GET /analytics` with the same API-key header to retrieve per-user totals and statistics for the latest sample.

## Deployment

The Docker image runs the FastAPI service and uses the platform's `PORT` environment variable (default `8000`). Configure the Supabase settings as deployment secrets. Do not use the Node sample's `process.json` as the API deployment command.

## Development checks

```bash
python -m unittest discover -s tests
```

## License

MIT. See [`LICENSE`](LICENSE).
