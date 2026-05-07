# Render.com Deployment — Step by Step

---

### Prerequisites

- Code pushed to a **GitHub** repository (Render pulls from Git)
- A [render.com](https://render.com) account (free, sign up with GitHub)
- Your `ANTHROPIC_API_KEY` ready

---

## Part 1 — Deploy the Backend (Web Service)

**Step 1 — Create a new Web Service**

1. Log in to Render → click **New +** → select **Web Service**
2. Click **Connect a repository** → authorize GitHub if prompted
3. Select your repository (`ExstreamCompassVectorLessRagAgent`)
4. Click **Connect**

---

**Step 2 — Configure the Web Service**

Fill in these fields:

| Field | Value |
|---|---|
| **Name** | `document-assistant-api` |
| **Region** | Oregon (US West) — closest free region |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements-render.txt` |
| **Start Command** | `PYTHONPATH=src uvicorn compass.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |

---

**Step 3 — Add environment variables**

Scroll down to **Environment Variables** → click **Add Environment Variable**:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your actual key) |
| `DEBUG` | `false` |

---

**Step 4 — Deploy the backend**

1. Click **Create Web Service**
2. Render will clone the repo, run `pip install -r requirements-render.txt`, then start the server
3. Watch the **Logs** tab — wait for:
   ```
   Application startup complete.
   ```
4. Copy your backend URL from the top of the page:
   ```
   https://document-assistant-api.onrender.com
   ```
5. Verify it works — open in browser:
   ```
   https://document-assistant-api.onrender.com/health
   ```
   Should return: `{"status":"healthy",...}`

---

## Part 2 — Deploy the Frontend (Static Site)

**Step 5 — Create a new Static Site**

1. Click **New +** → select **Static Site**
2. Select the same repository
3. Click **Connect**

---

**Step 6 — Configure the Static Site**

| Field | Value |
|---|---|
| **Name** | `document-assistant-ui` |
| **Branch** | `main` |
| **Build Command** | `cd frontend && npm install && npm run build` |
| **Publish Directory** | `./frontend/dist` |

---

**Step 7 — Add environment variable**

Under **Environment Variables**:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://document-assistant-api.onrender.com/api/v1` |

> Replace the URL with the exact backend URL you copied in Step 4. This is baked into the frontend bundle at build time by Vite — must be set **before** the build runs.

---

**Step 8 — Deploy the frontend**

1. Click **Create Static Site**
2. Watch the **Logs** tab — wait for:
   ```
   Build successful
   ```
3. Your frontend URL will appear at the top:
   ```
   https://document-assistant-ui.onrender.com
   ```
4. Open it in a browser and test a query

---

## Part 3 — Verify End-to-End

**Step 9 — Smoke test checklist**

Open `https://document-assistant-ui.onrender.com` and check:

- [ ] Page loads — shows "Document Assistant" header
- [ ] Login works — enter any email + password
- [ ] Variant toggle shows **Cloud Native** and **Server Based**
- [ ] Submit a query — response appears within 10–15 seconds
- [ ] Citations panel opens when clicking a response
- [ ] Switching variant loads that variant's chat history

---

## Common Issues & Fixes

| Symptom | Cause | Fix |
|---|---|---|
| Backend logs `ModuleNotFoundError: compass` | `PYTHONPATH` not set | Confirm start command has `PYTHONPATH=src` prefix |
| Frontend shows network error on query | Wrong `VITE_API_URL` | Check the URL has no trailing slash; trigger a **Manual Deploy** after fixing |
| Backend returns 500 on `/health` | Missing `ANTHROPIC_API_KEY` | Add it in the backend's **Environment** tab → **Save Changes** (triggers redeploy) |
| First request takes 30–60 seconds | Free tier cold start after 15 min idle | Expected behaviour — warn demo viewers |
| Build times out | Too many dependencies | Confirm `requirements-render.txt` is being used, not `requirements.txt` |
| CORS error in browser console | Frontend calling wrong URL | Open browser DevTools → Network tab → check the actual request URL |

---

## Redeployment (after code changes)

Render auto-deploys on every push to `main`. To trigger manually:

1. Go to the service dashboard
2. Click **Manual Deploy** → **Deploy latest commit**

> If you change `VITE_API_URL` or any other env var on the frontend, you must trigger a **Manual Deploy** — env vars are baked at build time, not runtime.
