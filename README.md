# QBO Reconciliation

QuickBooks Online ↔ FlowAccount reconciliation system.

**Deployed at:** https://qbo-reconciliation-jade.vercel.app

## Setup Instructions

### 1. GitHub Repo
- **URL:** https://github.com/henryandpartners/qbo-reconciliation
- Clone: `git clone git@github.com:henryandpartners/qbo-reconciliation.git`

### 2. Intuit Developer Portal — Go Live Form

Fill in these URLs on the [Intuit Developer Portal](https://developer.intuit.com):

| Field | Value |
|-------|-------|
| **App Description** | Accounting reconciliation between QuickBooks and FlowAccount |
| **Host Domain** | `qbo-reconciliation-jade.vercel.app` |
| **Launch URL** | `https://qbo-reconciliation-jade.vercel.app/auth/callback` |
| **Disconnect URL** | `https://qbo-reconciliation-jade.vercel.app/disconnect` |
| **Connect/Reconnect URL** | `https://qbo-reconciliation-jade.vercel.app/reconnect` |
| **End-User License Agreement** | `https://qbo-reconciliation-jade.vercel.app/terms` |
| **Privacy Policy** | `https://qbo-reconciliation-jade.vercel.app/privacy` |
| **App Category** | Business Management or Accounting |
| **Hosting Country** | Thailand |
| **OAuth Redirect URI** | `https://qbo-reconciliation-jade.vercel.app/auth/callback` |

### 3. Environment Variables

Set these in Vercel:
- `QBO_CLIENT_ID` — from Intuit Developer Portal Keys tab
- `QBO_CLIENT_SECRET` — from Intuit Developer Portal Keys tab
- `QBO_REDIRECT_URI` — `https://qbo-reconciliation-jade.vercel.app/auth/callback`

### 4. OAuth Flow

1. Go to https://qbo-reconciliation-jade.vercel.app
2. Click "Connect QuickBooks"
3. Authorize with your QuickBooks account
4. Share the tokens with Hermes

## Tech Stack
- **Backend:** FastAPI (Python)
- **Hosting:** Vercel (Serverless Functions)
- **OAuth:** QuickBooks Online OAuth 2.0
