# browser-agent

Playwright-based browser automation HTTP API for the Rachael autonomous assistant.

Runs on the **Linux host** (not inside Docker) so Playwright can control a real Chromium instance with a dedicated user profile.

---

## Quick start (host)

### 1. Install Python dependencies

```bash
cd browser-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Playwright's Chromium browser

```bash
playwright install chromium
```

### 3. Configure (optional)

```bash
cp .env.example .env
# Edit .env to set domain allowlist, max steps, etc.
```

### 4. Run

```bash
python main.py
# Service starts on http://127.0.0.1:8001
```

Interactive API docs available at: <http://127.0.0.1:8001/docs>

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/browser/open` | Open browser and navigate to URL |
| `POST` | `/v1/browser/navigate` | Navigate to a new URL |
| `GET`  | `/v1/browser/snapshot` | Page state: URL, title, text, interactive elements |
| `POST` | `/v1/browser/click` | Click an element by selector |
| `POST` | `/v1/browser/type` | Type text into a form field |
| `POST` | `/v1/browser/extract` | Extract text / HTML / links / table data |
| `GET`  | `/v1/browser/screenshot` | Full-page PNG screenshot (base64) |
| `POST` | `/v1/browser/close` | Close browser (profile preserved) |
| `GET`  | `/v1/browser/status` | Current browser state |
| `GET`  | `/health` | Health check |

### Stop-points

When a `click` request targets an element whose text or selector contains a stop-point keyword (e.g. `checkout`, `pay now`, `delete`), the API returns **HTTP 423 Locked** with:

```json
{
  "status": "stop_point",
  "message": "Stop-point detected…",
  "element_info": "selector='#checkout-btn', text='Proceed to Checkout'",
  "hint": "Re-send the request with force=true after obtaining user approval."
}
```

The caller (`api-core`) must obtain explicit user approval and re-send the request with `"force": true`.

### Domain allowlist

Set `BROWSER_DOMAIN_ALLOWLIST=domain1.com,domain2.com` to restrict navigation to those domains. Requests to unlisted domains return **HTTP 403 Forbidden**. Leave empty to allow all domains (development mode).

---

## Running with Docker (CI / reproducible env)

> The Docker image runs Chromium headless. Use this for CI or environment reproducibility only — for full Rachael operation, run on the host.

```bash
docker build -t rachael-browser-agent .
docker run --rm -p 8001:8001 \
  -v "$(pwd)/chromium-profile:/app/chromium-profile" \
  -e BROWSER_HEADLESS=true \
  rachael-browser-agent
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BROWSER_HOST` | `127.0.0.1` | Bind address |
| `BROWSER_PORT` | `8001` | Listen port |
| `BROWSER_CHROMIUM_PROFILE_DIR` | `./chromium-profile` | Persistent profile path |
| `BROWSER_HEADLESS` | `false` | Headless Chromium |
| `BROWSER_SLOW_MO` | `100` | ms delay between actions |
| `BROWSER_DOMAIN_ALLOWLIST` | `` | Comma-separated allowed domains (empty = all) |
| `BROWSER_MAX_STEPS_PER_TASK` | `50` | Max browser actions per task |
| `BROWSER_STOP_POINT_KEYWORDS` | see `.env.example` | Stop-point trigger keywords |
