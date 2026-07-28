# Gradient Birthday Loader

Static loading screen for the Gradient Birthday Poster Generator.

Hosted on **Vercel** at `birthday.gradientclub.in`.  
Polls the Flask backend at `birthday-api.gradientclub.in` until it wakes up,
then redirects the user to `/login` automatically.

---

## Architecture

```
User
 │
 ▼
https://birthday.gradientclub.in          ← Vercel (this project, static)
 │
 │  polls GET /health every 2 s
 ▼
https://birthday-api.gradientclub.in      ← Cloudflare DNS proxy
 │
 ▼
Render Web Service (Flask)                ← actual compute
```

The frontend has **zero knowledge** of Render.  
To migrate backends, change only the Cloudflare DNS record for
`birthday-api.gradientclub.in` — no code changes required.

---

## Project structure

```
birthday-loader/
├── index.html        # semantic HTML shell — no inline styles or JS
├── style.css         # all visual styles and animations
├── script.js         # polling logic, config constant, redirect
├── assets/
│   └── logo.svg      # replace with the real Gradient logo SVG
└── README.md
```

---

## Configuration

Open `script.js` and update the `CONFIG` block at the top:

```js
var CONFIG = {
  BACKEND_URL: 'https://birthday-api.gradientclub.in',
  // ... other timing constants
};
```

`BACKEND_URL` is the **only** place a URL appears.  
Every fetch and every redirect derives from this single constant.

---

## Deployment — Vercel

### 1. Push this folder to GitHub

Create a new repository (or a subdirectory in a monorepo) containing
only the files in this folder.

### 2. Import into Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import the repository
3. Framework preset: **Other** (plain static)
4. Build command: *(leave empty)*
5. Output directory: *(leave empty / `.`)*
6. Click **Deploy**

Vercel detects `index.html` at the root and serves it as a static site
with no build step required.

### 3. Add the custom domain

In your Vercel project → **Settings → Domains**:

```
birthday.gradientclub.in
```

Vercel will show you a DNS record to add. See the Cloudflare section below.

---

## DNS setup — Cloudflare

You need **two** DNS records in the Cloudflare dashboard for `gradientclub.in`.

### Record 1 — Frontend (Vercel)

| Field  | Value                        |
|--------|------------------------------|
| Type   | `CNAME`                      |
| Name   | `birthday`                   |
| Target | `cname.vercel-dns.com`       |
| Proxy  | **DNS only** (grey cloud)    |

> Vercel requires DNS-only (not proxied) for custom domains.
> Vercel handles TLS automatically via their own certificate.

### Record 2 — Backend API (Render → Cloudflare proxy)

| Field  | Value                                        |
|--------|----------------------------------------------|
| Type   | `CNAME`                                      |
| Name   | `birthday-api`                               |
| Target | `<your-service>.onrender.com`                |
| Proxy  | **Proxied** (orange cloud) ✓                 |

Replace `<your-service>` with the actual Render subdomain
(e.g. `gradient-birthday.onrender.com`).

Proxying through Cloudflare means:
- Users never see a `*.onrender.com` URL
- Cloudflare provides TLS for `birthday-api.gradientclub.in`
- If you migrate away from Render, only this target value changes

### Record 3 — Tell Render about the custom domain

In the Render dashboard → your service → **Settings → Custom Domains**:

```
birthday-api.gradientclub.in
```

Render will verify the CNAME and provision its own TLS certificate.

---

## CORS — Flask must allow the Vercel origin

The loading page fetches `https://birthday-api.gradientclub.in/health`
from `https://birthday-posters.gradientclub.in`.

Because these are different origins, Flask needs to return the correct
CORS header on `/health` responses.

Add this to `app.py` in the Flask project:

```python
@app.get("/health")
def health():
    response = jsonify({"status": "ok"})
    response.headers["Access-Control-Allow-Origin"] = "https://birthday-posters.gradientclub.in"
    return response
```

Or install `flask-cors` for a project-wide solution:

```
pip install flask-cors==4.0.1
```

```python
from flask_cors import CORS
CORS(app, origins=["https://birthday-posters.gradientclub.in"])
```

> Without this header the browser will block the `/health` fetch and
> the loader will never redirect.

---

## Replacing the logo

The placeholder `assets/logo.svg` contains a simple "G" mark.

To use the real Gradient logo:

1. Export the logo as an SVG (preferred) or PNG
2. Replace `assets/logo.svg` (or add a `.png` and update the `src`
   attribute in `index.html`)
3. Commit and push — Vercel redeploys automatically

---

## Local development

No build tools required. Open `index.html` directly in a browser:

```
# macOS / Linux
open index.html

# Windows
start index.html
```

While testing locally the `/health` fetch will fail (different origin,
backend not running). That is expected — the timeout warning will appear
after 90 seconds. To test the success flow, temporarily change
`BACKEND_URL` in `script.js` to `http://localhost:5000` and run the
Flask app locally.

---

## Future migrations

If you ever move the backend from Render to another host (Railway, Fly.io,
a VPS, etc.):

1. Update the **Cloudflare CNAME target** for `birthday-api` to point at
   the new host
2. That is the only change needed
3. The Vercel frontend, `script.js`, and all user-facing URLs remain
   identical
