"""
Dashboard HTML templates for QuickBooks Online data visualization.
"""
import json

DASHBOARD_CSS = """
:root { --gbg: #0f172a; --gcard: #1e293b; --gtext: #e2e8f0; --gmuted: #94a3b8; --gborder: #334155; --gprimary: #2ca01c; --gdanger: #ef4444; --gwarn: #eab308; --gsuccess: #22c55e; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--gbg); color: var(--gtext); line-height: 1.6; }
.header { background: linear-gradient(135deg, #1a3a1a, #0f172a); padding: 40px 20px 30px; border-bottom: 1px solid var(--gborder); }
.header h1 { font-size: 28px; margin-bottom: 4px; }
.header .sub { color: var(--gmuted); font-size: 14px; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.card { background: var(--gcard); border-radius: 12px; padding: 20px; border: 1px solid var(--gborder); }
.card h3 { color: var(--gmuted); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.card .num { font-size: 28px; font-weight: 700; }
.card .sublabel { font-size: 12px; color: var(--gmuted); margin-top: 2px; }
.grid { display: grid; gap: 15px; margin-bottom: 25px; }
.grid-4 { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.grid-2 { grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); }
.green { color: var(--gsuccess); }
.red { color: var(--gdanger); }
.yellow { color: var(--gwarn); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 10px 8px; color: var(--gmuted); border-bottom: 1px solid var(--gborder); font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 10px 8px; border-bottom: 1px solid #1e293b; }
tr:hover td { background: rgba(255,255,255,0.03); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; }
.badge-banks { background: #1e3a5f; color: #60a5fa; }
.badge-income { background: #166534; color: #4ade80; }
.badge-expense { background: #7f1d1d; color: #f87171; }
.badge-asset { background: #1e3a5f; color: #60a5fa; }
.badge-liability { background: #713f12; color: #fbbf24; }
.badge-equity { background: #164e63; color: #67e8f9; }
.badge-revenue { background: #166534; color: #4ade80; }
.badge-expenses { background: #7f1d1d; color: #f87171; }
.badge-other { background: #374151; color: #9ca3af; }
.alert { padding: 15px; border-radius: 8px; margin-bottom: 15px; }
.alert-warn { background: #713f12; color: #fbbf24; border: 1px solid #92400e; }
.alert-err { background: #7f1d1d; color: #f87171; border: 1px solid #991b1b; }
.alert-ok { background: #166534; color: #4ade80; border: 1px solid #15803d; }
.mb-15 { margin-bottom: 15px; }
.mb-25 { margin-bottom: 25px; }
@media (max-width: 768px) { .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } }
"""


def render_dashboard(data: dict) -> str:
    """Render a dark-themed QBO dashboard from analyzed data."""
    coa = data.get("coa", {}) or {}
    pl = data.get("pl", {}) or {}

    # Company info
    company_raw = data.get("company", {})
    qr = company_raw.get("QueryResponse") or {}
    ci = (qr.get("CompanyInfo") or [{}])[0] if qr.get("CompanyInfo") else {}
    company_name = ci.get("CompanyName") or "QuickBooks Company"
    country = ci.get("Country") or ""

    # P&L
    income = _safe_float(pl.get("income"))
    expenses = _safe_float(pl.get("expenses"))
    net_income = _safe_float(pl.get("net_income")) or (income - expenses)
    margin_pct = (net_income / income * 100) if income else 0

    # Balance sheet
    total_assets = _safe_float(coa.get("total_assets"))
    total_liabilities = _safe_float(coa.get("total_liabilities"))
    total_equity = _safe_float(coa.get("total_equity"))

    # Accounts
    total_revenue_coa = _safe_float(coa.get("total_revenue"))
    total_expenses_coa = _safe_float(coa.get("total_expenses"))
    account_types = coa.get("account_types", {})
    if not account_types and not total_assets and not total_liabilities:
        # Fallback: coa might be empty
        account_types = {}

    # Invoices
    inv = data.get("invoices", {}) or {}
    total_invoiced = _safe_float(inv.get("total_amount"))
    unpaid = _safe_float(inv.get("unpaid"))
    paid_pct = ((total_invoiced - unpaid) / total_invoiced * 100) if total_invoiced else 0
    monthly = inv.get("monthly_counts", {})
    monthly_labels = json.dumps(list(monthly.items())[-12:])
    monthly_vals = json.dumps(list(monthly.values())[-12:])
    monthly_keys = json.dumps(list(monthly.keys())[-12:])

    # Items
    itm = data.get("items", {}) or {}
    inv_value = _safe_float(itm.get("total_inv_value"))
    low_stock = itm.get("low_stock", 0)

    profit_status = "green" if net_income > 0 else "red"
    profit_label = "Profitable" if net_income > 0 else "Net Loss"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QBO Dashboard — {company_name}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>{DASHBOARD_CSS}</style>
</head>
<body>
<div class="header">
    <h1>📊 {company_name}</h1>
    <div class="sub">QuickBooks Online · {country}</div>
</div>
<div class="container">

<div class="grid grid-4">
    <div class="card"><h3>Revenue (YTD)</h3><div class="num green">{_fmt(income)}</div></div>
    <div class="card"><h3>Net Profit</h3><div class="num {profit_status}">{_fmt(net_income)}</div><div class="sublabel">{profit_label} · {margin_pct:.1f}% margin</div></div>
    <div class="card"><h3>Expenses</h3><div class="num red">{_fmt(expenses)}</div></div>
    <div class="card"><h3>Total Invoiced</h3><div class="num">{_fmt(total_invoiced)}</div><div class="sublabel">{paid_pct:.0f}% collected</div></div>
</div>

<div class="grid grid-4">
    <div class="card"><h3>Assets</h3><div class="num green">{_fmt(total_assets)}</div></div>
    <div class="card"><h3>Liabilities</h3><div class="num red">{_fmt(total_liabilities)}</div></div>
    <div class="card"><h3>Equity</h3><div class="num">{_fmt(total_equity)}</div></div>
    <div class="card"><h3>Inventory</h3><div class="num">{_fmt(inv_value)}</div><div class="sublabel">{itm.get('total',0)} items · {low_stock} low stock</div></div>
</div>

<div class="grid grid-2">
    <div class="card"><h3 style="margin-bottom:15px;">📈 Monthly Invoices</h3>
    <canvas id="invChart" height="200"></canvas></div>
    <div class="card"><h3 style="margin-bottom:15px;">💰 Balance Sheet</h3>
    <canvas id="balChart" height="200"></canvas></div>
</div>

<div class="grid grid-2">
    <div class="card"><h3 style="margin-bottom:15px;">📋 Account Types</h3>
    <table>
    <tr><th>Type</th><th style="text-align:right">Count</th></tr>
    {_account_types_rows(account_types)}
    </table></div>
    <div class="card"><h3 style="margin-bottom:15px;">🧾 AR & Inventory</h3>
    <table>
    <tr><th>Metric</th><th style="text-align:right">Value</th></tr>
    <tr><td>Outstanding AR</td><td style="text-align:right" class="red">{_fmt(unpaid)}</td></tr>
    <tr><td>Inventory Items</td><td style="text-align:right">{itm.get('inventory',0)}</td></tr>
    <tr><td>Service Items</td><td style="text-align:right">{itm.get('service',0)}</td></tr>
    <tr><td>Total Invoices</td><td style="text-align:right">{inv.get('total',0)}</td></tr>
    </table></div>
</div>

<div style="text-align:center;padding:20px;color:var(--gmuted);font-size:13px;">
    <a href="/" style="color:var(--gprimary);">← Back</a> · <a href="/dashboard" style="color:var(--gprimary);">⟳ Refresh</a>
</div>
</div>

<script>
new Chart(document.getElementById('invChart'), {{
    type: 'bar',
    data: {{ labels: {monthly_keys}, datasets: [{{ label: 'Invoices', data: {monthly_vals}, backgroundColor: '#2ca01c', borderRadius: 4 }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#334155' }} }},
                  x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }} }} }}
}});
new Chart(document.getElementById('balChart'), {{
    type: 'doughnut',
    data: {{ labels: ['Assets','Liabilities','Equity'], datasets: [{{ data: [{abs(total_assets)},{abs(total_liabilities)},{abs(total_equity)}], backgroundColor: ['#22c55e','#ef4444','#3b82f6'], borderWidth: 0 }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }} }}
}});
</script>
</body></html>"""


def render_error(msg: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Error</title>
<style>{DASHBOARD_CSS}</style></head><body>
<div class="container" style="padding-top:80px;text-align:center;">
<div class="card" style="max-width:540px;margin:0 auto;">
<h1 style="color:var(--gdanger);margin-bottom:15px;">⚠️</h1>
<h2 style="margin-bottom:15px;">Dashboard Unavailable</h2>
<div class="alert alert-err">{msg}</div>
<p style="margin-top:15px;"><a href="/" style="color:var(--gprimary);">← Back to Home</a></p>
</div></div></body></html>"""


def _fmt(val) -> str:
    try:
        v = float(val or 0)
        if abs(v) >= 1_000_000_000:
            return f"฿{v/1_000_000_000:.2f}B"
        if abs(v) >= 1_000_000:
            return f"฿{v/1_000_000:.2f}M"
        if abs(v) >= 1_000:
            return f"฿{v:,.0f}"
        return f"฿{v:,.2f}"
    except (ValueError, TypeError):
        return "฿0"


def _safe_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _account_types_rows(types: dict) -> str:
    if not types:
        return '<tr><td colspan="2" style="text-align:center;color:#64748b;">No data</td></tr>'
    rows = ""
    for at, cnt in sorted(types.items(), key=lambda x: -x[1]):
        safe_key = at.lower().replace(" ", "").replace("&", "").replace("/", "")
        rows += f'<tr><td><span class="badge badge-{safe_key}">{at}</span></td><td style="text-align:right">{cnt}</td></tr>\n'
    return rows
