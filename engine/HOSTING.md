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

## Step 2 — Railway (the backend)

1. <https://railway.app> → **New Project** → **Deploy from GitHub repo** →
   `krishpinto/Sanhita`.
2. Open the service → **Settings**:
   - **Root Directory**: `engine/backend`
   - Leave the build and start commands alone — `railway.toml` in that folder
     already sets them.
3. **Settings → Volumes → Add Volume**, mount path `/data`.

   **Do not skip this.** Without a volume the database lives on the
   container's own disk, and every redeploy — including ones Railway does by
   itself — starts from an empty file. Every consultation your friend records
   would be gone, which is exactly what you wanted to be able to review.
4. **Variables**, add:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | `sqlite:////data/vitalis.db` |
   | `CORS_ORIGINS` | `*` (tighten in step 4) |

   Four slashes in the database URL. Three means "relative path", four means
   "absolute" — with three you get a file inside the container again and the
   volume sits there empty.
5. **Settings → Networking → Generate Domain.** Copy the URL.
6. Check it: opening `https://<your-railway-url>/health` should show
   `{"status":"ok"}`.

## Step 3 — Vercel (the web app)

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

## Step 4 — go back to Railway and close CORS

In Railway → **Variables**, replace what you set in step 2:

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
No volume, or `DATABASE_URL` has three slashes instead of four. Both mean the
database is on disposable storage.

**Railway says the app is not responding**
The start command must bind `0.0.0.0`, not `127.0.0.1`. `railway.toml`
already does; check nothing overrode it in the dashboard.

---

## What to do after the pitch

- **A way in.** Even a single shared password would do. Right now the URL is
  the only thing standing between the app and the internet.
- **Postgres instead of SQLite on a volume.** Railway provides one in a click.
  SQLite on a single volume is fine for one doctor at a time and stops being
  fine the moment two people use it at once.
- **Migrations.** The schema is created by `create_all()` on boot, which
  handles new tables and silently ignores changed columns. Before real
  patient data goes in, this needs Alembic or an equivalent.
