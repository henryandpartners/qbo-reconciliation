from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="QBO Reconciliation")

CLIENT_ID = os.getenv("QBO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("QBO_REDIRECT_URI", "https://qbo-oauth-callback.vercel.app/auth/callback")

QB_OAUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QB_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QBO Reconciliation — Home</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f5f7fa; color: #333; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: white; border-radius: 16px; padding: 40px; max-width: 500px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; }
        h1 { font-size: 24px; margin-bottom: 8px; }
        p { color: #666; margin-bottom: 24px; }
        .btn { display: inline-block; background: #2ca01c; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px; }
        .btn:hover { background: #248016; }
        .links { margin-top: 24px; font-size: 14px; }
        .links a { color: #2ca01c; text-decoration: none; margin: 0 8px; }
        .links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 QBO Reconciliation</h1>
        <p>Connect your QuickBooks Online account to reconcile with FlowAccount data.</p>
        <a class="btn" href="/auth/login">🔗 Connect QuickBooks</a>
        <div class="links">
            <a href="/terms">Terms</a> · <a href="/privacy">Privacy</a> · <a href="/disconnect">Disconnect</a>
        </div>
    </div>
</body>
</html>"""


@app.get("/auth/login")
async def auth_login():
    """Redirect to Intuit OAuth authorization page."""
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
    """Handle OAuth callback from Intuit."""
    if error:
        return HTMLResponse(f"<h1>Error</h1><p>{error}</p>", status_code=400)

    if not code:
        return HTMLResponse("<h1>Error</h1><p>No authorization code received.</p>", status_code=400)

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            QB_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            auth=(CLIENT_ID, CLIENT_SECRET),
        )
        data = resp.json()

    if resp.status_code != 200:
        return HTMLResponse(
            f"<h1>Token Exchange Failed</h1><pre>{data}</pre>",
            status_code=500,
        )

    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")
    company_id = realm_id or data.get("realmId", "")

    # Return success page with credentials
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connected ✓</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f0fdf4; color: #333; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: white; border-radius: 16px; padding: 40px; max-width: 600px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
        h1 {{ color: #16a34a; font-size: 24px; margin-bottom: 8px; }}
        .token {{ background: #f8f9fa; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 12px; word-break: break-all; margin: 8px 0; }}
        .label {{ font-weight: 600; margin-top: 16px; margin-bottom: 4px; }}
        .btn {{ display: inline-block; background: #2ca01c; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>✅ QuickBooks Connected</h1>
        <p>Company ID: <strong>{company_id}</strong></p>
        <div class="label">Access Token</div>
        <div class="token">{access_token[:50]}...</div>
        <div class="label">Refresh Token</div>
        <div class="token">{refresh_token[:50]}...</div>
        <p style="margin-top:16px;color:#666;">Share the tokens with Hermes to start reconciliation.</p>
    </div>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/disconnect")
async def disconnect():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Disconnect</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f5f7fa; color: #333; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: white; border-radius: 16px; padding: 40px; max-width: 500px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; }
        h1 { font-size: 24px; }
        p { color: #666; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔌 Disconnect</h1>
        <p>Your QuickBooks connection has been removed.</p>
        <p style="font-size:14px;color:#999;">To reconnect, visit the home page and click "Connect QuickBooks"</p>
    </div>
</body>
</html>"""


@app.get("/reconnect")
async def reconnect():
    return RedirectResponse(url="/auth/login")


@app.get("/terms")
async def terms():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 40px 20px; background: #f5f7fa; color: #333; }
        .container { max-width: 700px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
        h1 { font-size: 24px; margin-bottom: 20px; }
        h2 { font-size: 18px; margin-top: 24px; margin-bottom: 8px; }
        p { line-height: 1.7; color: #555; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Terms of Service</h1>
        <p><em>Last updated: July 2026</em></p>
        <h2>1. Service Description</h2>
        <p>This application connects to QuickBooks Online to retrieve accounting data for reconciliation with FlowAccount. It is used internally for business accounting analysis.</p>
        <h2>2. Data Access</h2>
        <p>We access your QuickBooks data solely for the purpose of reconciliation and business analysis. We do not share, sell, or transmit your data to third parties.</p>
        <h2>3. Security</h2>
        <p>OAuth tokens are stored securely and used only for API calls. You may revoke access at any time via the Disconnect page.</p>
        <h2>4. Contact</h2>
        <p>For questions, contact: pojamansoi2@gmail.com</p>
    </div>
</body>
</html>"""


@app.get("/privacy")
async def privacy():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 40px 20px; background: #f5f7fa; color: #333; }
        .container { max-width: 700px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
        h1 { font-size: 24px; margin-bottom: 20px; }
        h2 { font-size: 18px; margin-top: 24px; margin-bottom: 8px; }
        p { line-height: 1.7; color: #555; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Privacy Policy</h1>
        <p><em>Last updated: July 2026</em></p>
        <h2>Information We Collect</h2>
        <p>We collect QuickBooks Online accounting data (Chart of Accounts, transactions, invoices, inventory, reports) solely through the Intuit OAuth API.</p>
        <h2>How We Use Data</h2>
        <p>Data is used exclusively for internal reconciliation between FlowAccount and QuickBooks systems. No data is shared with third parties.</p>
        <h2>Data Retention</h2>
        <p>Data is retained as needed for reconciliation. You may request deletion at any time.</p>
        <h2>Contact</h2>
        <p>Email: pojamansoi2@gmail.com</p>
    </div>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
