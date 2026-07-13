"""
QBO Reconciliation + Dashboard Application

Routes:
- /           Home / Connect QuickBooks
- /auth/*     OAuth flow
- /dashboard  Dashboard (requires tokens via session or query params)
- /token-auth Page to paste tokens manually
- /terms, /privacy, /disconnect
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="QBO Reconciliation")

CLIENT_ID = os.getenv("QBO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("QBO_REDIRECT_URI", "https://qbo-reconciliation-jade.vercel.app/auth/callback")

QB_OAUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# In-memory token store (resets on each Vercel cold start — ephemeral)
_tokens = {}
_token_company = {}


# ── Home ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QBO Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #1e293b; border-radius: 16px; padding: 40px; max-width: 480px; width: 90%; border: 1px solid #334155; text-align: center; }
        h1 { font-size: 26px; margin-bottom: 6px; }
        p { color: #94a3b8; margin-bottom: 24px; font-size: 14px; line-height: 1.6; }
        .btn { display: block; padding: 14px 24px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px; margin-bottom: 12px; transition: opacity 0.2s; }
        .btn-primary { background: #2ca01c; color: white; }
        .btn-primary:hover { opacity: 0.9; }
        .btn-secondary { background: #334155; color: #e2e8f0; }
        .btn-secondary:hover { background: #475569; }
        .divider { display: flex; align-items: center; gap: 12px; margin: 20px 0; color: #64748b; font-size: 12px; }
        .divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: #334155; }
        .links { margin-top: 20px; font-size: 13px; }
        .links a { color: #64748b; text-decoration: none; margin: 0 8px; }
        .links a:hover { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 QBO Dashboard</h1>
        <p>QuickBooks Online Business Analysis</p>

        <a class="btn btn-primary" href="/auth/login">🔗 Connect QuickBooks via OAuth</a>

        <div class="divider">OR</div>

        <a class="btn btn-secondary" href="/token-auth">🔑 Paste Tokens Manually</a>

        <div class="links">
            <a href="/terms">Terms</a> · <a href="/privacy">Privacy</a>
        </div>
    </div>
</body>
</html>"""


# ── Token Auth Page ───────────────────────────────────────────────────────────

TOKEN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enter Tokens</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .card { background: #1e293b; border-radius: 16px; padding: 40px; max-width: 520px; width: 100%; border: 1px solid #334155; }
        h1 { font-size: 24px; margin-bottom: 6px; }
        p { color: #94a3b8; font-size: 14px; margin-bottom: 24px; }
        label { display: block; margin-top: 16px; font-size: 13px; font-weight: 500; color: #94a3b8; margin-bottom: 6px; }
        input, textarea { width: 100%; padding: 12px; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; font-family: monospace; font-size: 13px; }
        input:focus, textarea:focus { outline: none; border-color: #2ca01c; }
        .btn { display: block; width: 100%; padding: 14px; background: #2ca01c; color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 24px; }
        .btn:hover { opacity: 0.9; }
        .back { display: block; text-align: center; margin-top: 16px; color: #64748b; font-size: 13px; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔑 Enter Tokens</h1>
        <p>Paste your QuickBooks OAuth tokens to view the dashboard.</p>
        <form action="/dashboard" method="get">
            <label>Company / Realm ID *</label>
            <input type="text" name="company_id" placeholder="e.g. 1234567890" required>

            <label>Access Token *</label>
            <textarea name="access_token" rows="3" placeholder="Paste your QBO access token..." required></textarea>

            <label>Refresh Token (optional, for auto-refresh)</label>
            <textarea name="refresh_token" rows="2" placeholder="Paste refresh token if available..."></textarea>

            <button class="btn" type="submit">🚀 Load Dashboard</button>
        </form>
        <a class="back" href="/">← Back</a>
    </div>
</body>
</html>"""


@app.get("/token-auth", response_class=HTMLResponse)
async def token_auth_page():
    return TOKEN_PAGE


# ── OAuth Login ───────────────────────────────────────────────────────────────

@app.get("/auth/login")
async def auth_login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "com.intuit.quickbooks.accounting openid profile email",
        "redirect_uri": REDIRECT_URI,
        "state": os.urandom(16).hex(),
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{QB_OAUTH_URL}?{qs}")


@app.get("/auth/callback")
async def auth_callback(code: str = "", state: str = "", realm_id: str = "", error: str = ""):
    if error:
        return HTMLResponse(f"<h1>Error</h1><p>{error}</p>", status_code=400)
    if not code:
        return HTMLResponse("<h1>Error</h1><p>No authorization code received.</p>", status_code=400)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            QB_TOKEN_URL,
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
            auth=(CLIENT_ID, CLIENT_SECRET),
        )
        data = resp.json()

    if resp.status_code != 200:
        return HTMLResponse(f"<h1>Token Exchange Failed</h1><pre>{json.dumps(data, indent=2)}</pre>", status_code=500)

    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")
    company_id = realm_id or data.get("realmId", "")

    # Store tokens in memory for dashboard redirect
    session_id = os.urandom(8).hex()
    _tokens[session_id] = {"access": access_token, "refresh": refresh_token}
    _token_company[session_id] = company_id

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Connected ✓</title>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:-apple-system,sans-serif; background:#0f172a; color:#e2e8f0; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px; }}
    .card {{ background:#1e293b; border-radius:16px; padding:40px; max-width:560px; border:1px solid #334155; }}
    h1 {{ color:#22c55e; font-size:24px; margin-bottom:8px; }}
    .label {{ font-weight:600; margin-top:16px; margin-bottom:4px; font-size:13px; color:#94a3b8; }}
    .tok {{ background:#0f172a; padding:10px 12px; border-radius:8px; font-family:monospace; font-size:11px; word-break:break-all; margin:4px 0; color:#94a3b8; }}
    .btn {{ display:inline-block; background:#2ca01c; color:white; padding:14px 28px; border-radius:10px; text-decoration:none; font-weight:600; margin-top:20px; }}
</style>
</head>
<body>
<div class="card">
    <h1>✅ Connected!</h1>
    <p style="color:#94a3b8;">QuickBooks Online — Company ID: <strong>{company_id}</strong></p>
    <div class="label">Access Token</div>
    <div class="tok">{access_token[:80]}...</div>
    <div class="label">Refresh Token</div>
    <div class="tok">{refresh_token[:80]}...</div>
    <div style="margin-top:20px;display:flex;gap:12px;">
        <a class="btn" href="/dashboard?session={session_id}">📊 View Dashboard</a>
    </div>
    <p style="margin-top:16px;font-size:12px;color:#64748b;">Or share the tokens above with Hermes. They're stored temporarily in this browser session.</p>
</div>
</body>
</html>""")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    company_id: str = "",
    access_token: str = "",
    refresh_token: str = "",
    session: str = "",
):
    # If session param provided, use stored tokens
    if session and session in _tokens:
        access_token = _tokens[session].get("access", "")
        refresh_token = _tokens[session].get("refresh", "")
        company_id = _token_company.get(session, company_id)

    # Sanitize inputs — strip whitespace and control chars from tokens
    access_token = access_token.strip()
    refresh_token = refresh_token.strip()
    company_id = company_id.strip()

    if not company_id or not access_token:
        return HTMLResponse(TOKEN_PAGE)

    # Import here so Vercel can load the module
    from qbo_client import QBOClient, analyze_qbo_data
    from dashboard import render_dashboard, render_error

    client = QBOClient(
        company_id=company_id,
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    result = analyze_qbo_data(client)
    if result.get("error"):
        return render_error(str(result["error"]))

    # Check if coa failed (likely token issue)
    coa_data = result["data"].get("coa", {})
    if isinstance(coa_data, dict) and "error" in coa_data:
        err_detail = coa_data["error"]
        if "401" in str(err_detail) or "AuthenticationFailed" in str(err_detail):
            return render_error(
                "Authentication failed. Your token may be expired. "
                "<a href='/auth/login' style='color:#2ca01c;'>Reconnect via OAuth</a> "
                "or <a href='/token-auth' style='color:#2ca01c;'>enter a fresh token</a>."
            )
        return render_error(f"API Error: {err_detail}")

    return render_dashboard(result["data"])


# ── Static Pages ──────────────────────────────────────────────────────────────

DISC_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Disconnect</title><style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#1e293b;border-radius:16px;padding:40px;max-width:480px;border:1px solid #334155;text-align:center}
h1{font-size:24px}p{color:#94a3b8;margin-top:8px}a{color:#2ca01c}</style></head>
<body><div class="card"><h1>🔌 Disconnect</h1><p>Your QuickBooks connection has been removed.</p><p style="margin-top:16px;font-size:13px;"><a href="/">Back to Home</a></p></div></body></html>"""

TERMS_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Terms</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;padding:40px 20px}
.container{max-width:700px;margin:0 auto;background:#1e293b;border-radius:16px;padding:40px;border:1px solid #334155}
h1{font-size:24px;margin-bottom:20px}h2{font-size:18px;margin-top:24px;margin-bottom:8px;color:#e2e8f0}p{line-height:1.7;color:#94a3b8}</style></head>
<body><div class="container">
<h1>Terms of Service</h1><p><em>Last updated: July 2026</em></p>
<h2>1. Service Description</h2><p>This application connects to QuickBooks Online to retrieve accounting data for business analysis and reconciliation with FlowAccount.</p>
<h2>2. Data Access</h2><p>We access your QuickBooks data solely for analysis. We do not share, sell, or transmit your data to third parties.</p>
<h2>3. Security</h2><p>OAuth tokens are used only for API calls and are not stored permanently. You may revoke access at any time.</p>
<h2>4. Contact</h2><p>Email: pojamansoi2@gmail.com</p>
</div></body></html>"""

PRIVACY_PAGE = TERMS_PAGE.replace("Terms of Service", "Privacy Policy").replace(
    "<h2>1. Service Description</h2>", "<h2>Information We Collect</h2>"
).replace(
    "This application connects to QuickBooks Online to retrieve accounting data for business analysis and reconciliation with FlowAccount.",
    "We collect QuickBooks Online accounting data (Chart of Accounts, transactions, invoices, inventory) through the Intuit OAuth API for your internal business analysis."
).replace(
    "<h2>2. Data Access</h2>", "<h2>How We Use Data</h2>"
).replace(
    "We access your QuickBooks data solely for analysis. We do not share, sell, or transmit your data to third parties.",
    "Data is used exclusively for your internal business analysis and reconciliation. No data is shared with third parties."
).replace(
    "<h2>3. Security</h2>", "<h2>Data Retention</h2>"
).replace(
    "OAuth tokens are used only for API calls and are not stored permanently. You may revoke access at any time.",
    "Data is retained only as needed. You may request deletion at any time."
)


@app.get("/disconnect", response_class=HTMLResponse)
async def disconnect():
    return DISC_PAGE


@app.get("/reconnect")
async def reconnect():
    return RedirectResponse(url="/auth/login")


@app.get("/terms", response_class=HTMLResponse)
async def terms():
    return TERMS_PAGE


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    return PRIVACY_PAGE


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
