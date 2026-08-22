# Putting this online

Backend on **Railway**, web app on **Vercel**. Two services, one GitHub repo
(`krishpinto/Sanhita`, private — both hosts can read it once you connect your
GitHub account).

Do the steps in this order. Each host needs the other's URL, so the order is
what stops you going round in circles.

---

## Before you start — two things to know

**There is no login.** Anyone with the web app's URL can start an encounter.
That is fine for sending a link to one doctor for a day; it is not fine as a
permanent state. CORS does not change this — it only governs browsers, and
the API is reachable directly regardless.

**Tell your friend to use fake patient names.** This is a prototype on
shared infrastructure with no access control and no consent flow. Clinical
findings are fine; identifiers are not.

---

## Step 1 — push the code

```bash
cd C:/projects/medicalstartup/sanhita && git push origin main
```

## Step 2 — Neon (the database)

1. <https://neon.tech> → new project.
2. Copy the **connection string**. It looks like
   `postgresql://user:password@ep-something.aws.neon.tech/neondb?sslmode=require`.
3. That is all. Paste it in as-is at step 3 — the prefix is normalised in
   `app/config.py`, and the tables create themselves on first boot.

Keep `?sslmode=require` on the end. Neon refuses unencrypted connections, and
without it you get a connection error that does not mention TLS.

Use the **pooled** connection string if Neon offers you a choice (the host has
`-pooler` in it). A web service opens and closes connections constantly, which
is what the pooler is for.

## Step 3 — Railway (the backend)

1. <https://railway.app> → **New Project** → **Deploy from GitHub repo** →
   `krishpinto/Sanhita`.
2. Open the service → **Settings**:
   - **Root Directory**: `engine/backend`
   - Leave the build and start commands alone — `railway.toml` in that folder
     already sets them.
3. **Variables**, add:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | your Neon connection string |
   | `CORS_ORIGINS` | `*` (tighten in step 5) |

   **No volume needed.** The data lives in Neon, not on the container. That is
   the point of using it: Railway containers are wiped on every redeploy,
   including ones Railway does by itself.
4. **Settings → Networking → Generate Domain**, port `8080`. Copy the URL.
5. Check it: opening `https://<your-railway-url>/health` should show
   `{"status":"ok"}`.

## Step 4 — Vercel (the web app)

1. <https://vercel.com> → **Add New → Project** → import `krishpinto/Sanhita`.
2. **Root Directory**: `engine/frontend`. Framework preset: Vite (it should
   detect this itself).
3. **Environment Variables**, add:

   | Name | Value |
   |---|---|
   | `VITE_API_BASE` | your Railway URL, no trailing slash |

   The API URL is compiled into the JavaScript at build time — it cannot be
   changed afterwards without rebuilding. The build **fails on purpose** if
   this variable is missing, so a broken bundle never reaches your friend.
4. **Deploy.** Copy the URL it gives you.

## Step 5 — go back to Railway and close CORS

In Railway → **Variables**, replace what you set in step 3:

| Name | Value |
|---|---|
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://sanhita.vercel.app` |
| `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` |

The regex is so Vercel's preview builds keep working — every preview gets its
own hostname, so they cannot be listed one at a time.

Railway redeploys on save. Wait for it, then open the Vercel URL and run one
encounter end to end.

---

## The link to send

The **Vercel** URL. That is the whole product as far as your friend is
concerned; the Railway URL is plumbing and does not need to be shared.

---

## When something does not work

**Blank page, or "Failed to fetch" on the first click**
CORS. Open the browser console (F12) — if it mentions `Access-Control-Allow-Origin`,
`CORS_ORIGINS` on Railway does not match the Vercel URL exactly. Copy it again,
including `https://` and with no trailing slash.

**Every request fails, console says `localhost:8000`**
`VITE_API_BASE` was not set when Vercel built. Set it, then **Redeploy** —
changing the variable alone does nothing, because the old build still has the
old URL baked in.

**Railway build fails**
Root Directory is not `engine/backend`. Without it, Railway looks at the repo
root, finds the Expo app, and tries to build the wrong thing.

**It worked, then the past consultations vanished**
`DATABASE_URL` is not pointing at Neon, so the app fell back to a SQLite file
inside the container — which Railway wipes on every redeploy.

**"server closed the connection unexpectedly", usually after a quiet spell**
Neon suspends an idle compute. The connection pool checks each connection
before use (`pool_pre_ping`), so this should not surface — if it does, the
pooled Neon connection string (`-pooler` in the host) is the next thing to try.

**"Can't load plugin: sqlalchemy.dialects:postgres"**
An old-style `postgres://` URL reached SQLAlchemy unnormalised. `config.py`
rewrites both `postgres://` and `postgresql://`, so this means the variable is
being read from somewhere else — check for a stray `.env`.

**Railway says the app is not responding**
The start command must bind `0.0.0.0`, not `127.0.0.1`. `railway.toml`
already does; check nothing overrode it in the dashboard.

---

## What to do after the pitch

- **A way in.** Even a single shared password would do. Right now the URL is
  the only thing standing between the app and the internet.
- **Migrations.** The schema is created by `create_all()` on boot, which adds
  new tables and silently ignores a column that has changed on an existing
  one. That is fine while the schema only grows. Before real patient data has
  to survive a column change, this needs Alembic.
- **Backups.** Neon keeps point-in-time history on its own, but check the
  retention window on the plan you are on rather than assuming it.
