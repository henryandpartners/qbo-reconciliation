"""
QBO Business Analysis Dashboard Generator
Creates a dark-themed HTML dashboard from QBO data
Supports both API report data + CSV entity data
"""
import json
import os

# Try combined data first (API + CSV), fall back to API-only
COMBINED_PATH = "/Users/fathomers/workspace/qbo-oauth-callback/output/qbo_combined_data.json"
API_PATH = "/Users/fathomers/workspace/qbo-oauth-callback/output/qbo_all_data.json"
OUTPUT_PATH = "/Users/fathomers/workspace/qbo-oauth-callback/output/qbo_dashboard.html"

csv_data = {}
if os.path.exists(COMBINED_PATH):
    with open(COMBINED_PATH) as f:
        combined = json.load(f)
    data = combined.get("api", {})
    csv_data = combined.get("csv", {})
    print(f"✅ Loaded combined data ({len(csv_data)} CSV tables)")
else:
    with open(API_PATH) as f:
        data = json.load(f)
    print("✅ Loaded API data only")

# ── Parse Reports ──────────────────────────────────────────────────────────

def parse_report(report):
    """Parse QBO report rows into sections dict."""
    sections = {}
    rows = report.get('Rows', {}).get('Row', [])
    for item in rows:
        if item.get('type') == 'Section':
            header = item.get('Header', {}).get('ColData', [{}])[0].get('value', '')
            children = item.get('Rows', {}).get('Row', [])
            summary = item.get('Summary', {}).get('ColData', [])
            summary_val = summary[1].get('value', '0') if len(summary) > 1 else '0'
            items_list = []
            for child in children:
                if child.get('type') == 'Data':
                    cols = child.get('ColData', [])
                    name = cols[0].get('value', '') if len(cols) > 0 else ''
                    amt = cols[1].get('value', '0') if len(cols) > 1 else '0'
                    items_list.append({'name': name, 'amount': amt})
            sections[header] = {'items': items_list, 'total': summary_val}
    return sections

def fmt(n):
    """Format number as THB."""
    try:
        v = float(n)
        if abs(v) >= 1_000_000_000:
            return f"฿{v/1_000_000_000:.2f}B"
        if abs(v) >= 1_000_000:
            return f"฿{v/1_000_000:.2f}M"
        if abs(v) >= 1_000:
            return f"฿{v:,.0f}"
        return f"฿{v:,.2f}"
    except (ValueError, TypeError):
        return "฿0"

def sf(n):
    """Safe float."""
    try:
        return float(n)
    except (ValueError, TypeError):
        return 0.0

pl = parse_report(data.get('profit_and_loss', {}))
bs = parse_report(data.get('balance_sheet', {}))

# ── Extract Key Figures ────────────────────────────────────────────────────

income = sf(pl.get('Income', {}).get('total', 0))
cogs = sf(pl.get('Cost of Sales', {}).get('total', 0))
gross_profit = sf(pl.get('', {}).get('total', 0) or (income - cogs))
expenses_total = sf(pl.get('Expenses', {}).get('total', 0))
net_earnings = sf(pl.get('', {}).get('total', 0) if 'Income' in str(pl) else (income - cogs - expenses_total))

# Find net earnings from the last section
all_sections = list(pl.keys())
for s in reversed(all_sections):
    v = sf(pl[s].get('total', 0))
    if v != 0 and s not in ('', 'Income', 'Cost of Sales', 'Expenses'):
        net_earnings = v
        break

if net_earnings == 0 and expenses_total == 0:
    net_earnings = gross_profit

# Income items
income_items = pl.get('Income', {}).get('items', [])
cogs_items = pl.get('Cost of Sales', {}).get('items', [])

# Balance Sheet
total_assets = sf(bs.get('Assets', {}).get('total', 0))
current_assets = sf(bs.get('Current Assets', {}).get('total', 0))
ar = sf(bs.get('Accounts receivable', {}).get('total', 0))
inventory_val = sum(sf(i['amount']) for i in bs.get('Current Assets', {}).get('items', []) if 'Inventory' in i['name'] or 'Finish Goods' in i['name'])
total_liabilities = sf(bs.get("Liabilities and shareholder's equity", {}).get('total', 0))
current_liabilities = sf(bs.get('Current liabilities:', {}).get('total', 0))
ap = sf(bs.get('Accounts payable', {}).get('total', 0))
equity = sf(bs.get("Shareholders' equity::", {}).get('total', 0))

margin_pct = (gross_profit / income * 100) if income else 0
net_margin_pct = (net_earnings / income * 100) if income else 0

# ── Build P&L Table rows ───────────────────────────────────────────────────

def pl_rows(items):
    rows_html = ""
    for item in items:
        amt = sf(item['amount'])
        if amt != 0:
            rows_html += f'<tr><td>{item["name"]}</td><td style="text-align:right">{fmt(amt)}</td></tr>\n'
    return rows_html

income_rows = pl_rows(income_items)
cogs_rows = pl_rows(cogs_items)

# ── Generate CSV Data Sections ──────────────────────────────────────────────

csv_section = ""
if csv_data:
    for csv_type, csv_info in csv_data.items():
        if csv_info.get("count", 0) == 0:
            continue
        cols = csv_info.get("columns", [])[:4]
        if not cols:
            continue

        name_key = next((c for c in cols if any(k in c.lower() for k in ["name", "display", "title", "company"])), cols[0])
        val_key = next((c for c in cols if any(k in c.lower() for k in ["balance", "amount", "total", "price"])), None)

        rows_html = ""
        for row in csv_info["data"][:20]:
            name = row.get(name_key, row.get(cols[0], ""))
            val = row.get(val_key, "") if val_key else ""
            try:
                val_fmt = fmt(val) if val else ""
            except:
                val_fmt = val
            rows_html += f'<tr><td>{name}</td><td style="text-align:right">{val_fmt}</td></tr>\n'

        if csv_info["count"] > 20:
            rows_html += f'<tr><td style="color:var(--muted);font-style:italic;">... and {csv_info["count"]-20} more</td><td></td></tr>'

        csv_section += f'''
<div class="card mb-25">
    <h3 style="margin-bottom:15px;">📋 {csv_type.replace("_"," ").title()} ({csv_info["count"]})</h3>
    <table>
    <tr><th>{cols[0]}</th><th style="text-align:right">{"Amount" if val_key else ""}</th></tr>
    {rows_html}
    </table>
</div>
'''

# ── CSS ────────────────────────────────────────────────────────────────────

CSS = """
:root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --muted: #94a3b8; 
        --border: #334155; --green: #22c55e; --red: #ef4444; --amber: #eab308; 
        --blue: #3b82f6; --primary: #2ca01c; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
       background: var(--bg); color: var(--text); line-height: 1.6; }
.header { background: linear-gradient(135deg, #1a3a1a, #0f172a); padding: 40px 20px 30px; 
          border-bottom: 1px solid var(--border); }
.header h1 { font-size: 28px; margin-bottom: 4px; }
.header .sub { color: var(--muted); font-size: 14px; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.card { background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); }
.card h3 { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
.card .num { font-size: 28px; font-weight: 700; }
.card .sublabel { font-size: 12px; color: var(--muted); margin-top: 2px; }
.grid { display: grid; gap: 15px; margin-bottom: 25px; }
.grid-4 { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.grid-2 { grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); }
.grid-3 { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.green { color: var(--green); }
.red { color: var(--red); }
.amber { color: var(--amber); }
.blue { color: var(--blue); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 10px 8px; color: var(--muted); border-bottom: 1px solid var(--border); 
     font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
td { padding: 8px; border-bottom: 1px solid #1e293b; }
tr:hover td { background: rgba(255,255,255,0.03); }
.section-header td { font-weight: 600; color: var(--text); border-top: 2px solid var(--border); padding-top: 12px; }
.section-total td { font-weight: 700; border-top: 2px solid var(--border); color: var(--green); }
.mb-25 { margin-bottom: 25px; }
@media (max-width: 768px) { .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } }
"""

# ── Dashboard HTML ─────────────────────────────────────────────────────────

profit_color = "green" if net_earnings >= 0 else "red"
collection_pct = (income / (income + sf(bs.get('Accounts receivable', {}).get('total', 0)))) * 100 if income else 0

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QBO Dashboard — Business Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>{CSS}</style>
</head>
<body>
<div class="header">
    <h1>📊 QuickBooks Business Dashboard</h1>
    <div class="sub">QBO Online · THB · Accrual · Year to Date 2026</div>
</div>
<div class="container">

<!-- KPI Cards -->
<div class="grid grid-4 mb-25">
    <div class="card">
        <h3>Total Income</h3>
        <div class="num green">{fmt(income)}</div>
        <div class="sublabel">YTD</div>
    </div>
    <div class="card">
        <h3>Gross Profit</h3>
        <div class="num green">{fmt(gross_profit)}</div>
        <div class="sublabel">{margin_pct:.1f}% margin</div>
    </div>
    <div class="card">
        <h3>Net Earnings</h3>
        <div class="num {profit_color}">{fmt(net_earnings)}</div>
        <div class="sublabel">{net_margin_pct:.1f}% net margin</div>
    </div>
    <div class="card">
        <h3>Total Assets</h3>
        <div class="num">{fmt(total_assets)}</div>
        <div class="sublabel">Balance Sheet</div>
    </div>
</div>

<div class="grid grid-4 mb-25">
    <div class="card">
        <h3>Accounts Receivable</h3>
        <div class="num red">{fmt(ar)}</div>
        <div class="sublabel">{collection_pct:.1f}% collected</div>
    </div>
    <div class="card">
        <h3>Inventory Value</h3>
        <div class="num">{fmt(inventory_val)}</div>
        <div class="sublabel">Finished Goods + Raw</div>
    </div>
    <div class="card">
        <h3>Accounts Payable</h3>
        <div class="num red">{fmt(ap)}</div>
        <div class="sublabel">Outstanding</div>
    </div>
    <div class="card">
        <h3>Shareholders' Equity</h3>
        <div class="num blue">{fmt(equity)}</div>
        <div class="sublabel">Net Worth</div>
    </div>
</div>

<!-- Charts Row -->
<div class="grid grid-2 mb-25">
    <div class="card">
        <h3 style="margin-bottom:15px;">📈 Revenue vs COGS</h3>
        <canvas id="revCogsChart" height="220"></canvas>
    </div>
    <div class="card">
        <h3 style="margin-bottom:15px;">💰 Balance Sheet Overview</h3>
        <canvas id="bsChart" height="220"></canvas>
    </div>
</div>

<!-- P&L Table -->
<div class="grid grid-2 mb-25">
    <div class="card">
        <h3 style="margin-bottom:15px;">📋 Income Breakdown</h3>
        <table>
        <tr><th>Account</th><th style="text-align:right">Amount</th></tr>
        {income_rows}
        <tr class="section-total"><td>Total Income</td><td style="text-align:right">{fmt(income)}</td></tr>
        </table>
    </div>
    <div class="card">
        <h3 style="margin-bottom:15px;">📋 Cost of Sales</h3>
        <table>
        <tr><th>Account</th><th style="text-align:right">Amount</th></tr>
        {cogs_rows}
        <tr class="section-total"><td>Total COGS</td><td style="text-align:right">{fmt(cogs)}</td></tr>
        </table>
    </div>
</div>

<!-- Balance Sheet Table -->
<div class="card mb-25">
    <h3 style="margin-bottom:15px;">📋 Balance Sheet</h3>
    <table>
    <tr><th>Category</th><th style="text-align:right">Amount</th></tr>
    <tr class="section-header"><td>ASSETS</td><td style="text-align:right">{fmt(total_assets)}</td></tr>
    <tr><td style="padding-left:20px">Current Assets</td><td style="text-align:right">{fmt(current_assets)}</td></tr>
    <tr><td style="padding-left:20px">Accounts Receivable</td><td style="text-align:right;color:var(--red)">{fmt(ar)}</td></tr>
    <tr><td style="padding-left:20px">Inventory</td><td style="text-align:right">{fmt(inventory_val)}</td></tr>
    <tr class="section-header"><td>LIABILITIES</td><td style="text-align:right;color:var(--red)">{fmt(current_liabilities)}</td></tr>
    <tr><td style="padding-left:20px">Accounts Payable</td><td style="text-align:right;color:var(--red)">{fmt(ap)}</td></tr>
    <tr class="section-header"><td>EQUITY</td><td style="text-align:right;color:var(--blue)">{fmt(equity)}</td></tr>
    <tr><td style="padding-left:20px">Net Income</td><td style="text-align:right;color:var(--green)">{fmt(net_earnings)}</td></tr>
    </table>
</div>

<!-- Key Ratios -->
<div class="grid grid-3 mb-25">
    <div class="card">
        <h3>Gross Profit Margin</h3>
        <div class="num green">{margin_pct:.1f}%</div>
        <div class="sublabel">Gross Profit / Revenue</div>
    </div>
    <div class="card">
        <h3>Net Profit Margin</h3>
        <div class="num">{net_margin_pct:.1f}%</div>
        <div class="sublabel">Net Earnings / Revenue</div>
    </div>
    <div class="card">
        <h3>AR to Revenue</h3>
        <div class="num red">{fmt(ar)}</div>
        <div class="sublabel">Outstanding AR / Total Revenue</div>
    </div>
</div>

<!-- CSV Entity Data (when available) -->
{csv_section}

<div style="text-align:center;padding:20px;color:var(--muted);font-size:12px;">
    Generated from QuickBooks Online · Data as of Jul 14, 2026
</div>
</div>

<script>
new Chart(document.getElementById('revCogsChart'), {{
    type: 'bar',
    data: {{
        labels: ['Income', 'COGS', 'Gross Profit', 'Net Earnings'],
        datasets: [{{
            data: [{income}, {cogs}, {gross_profit}, {net_earnings}],
            backgroundColor: ['#22c55e', '#ef4444', '#3b82f6', '#7c3aed'],
            borderRadius: 6
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            y: {{ beginAtZero: true, ticks: {{ color: '#94a3b8', callback: v => '฿' + (v/1000000).toFixed(1) + 'M' }}, grid: {{ color: '#334155' }} }},
            x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ display: false }} }}
        }}
    }}
}});

new Chart(document.getElementById('bsChart'), {{
    type: 'doughnut',
    data: {{
        labels: ['Assets', 'Liabilities', 'Equity'],
        datasets: [{{
            data: [{total_assets}, {current_liabilities}, {equity}],
            backgroundColor: ['#22c55e', '#ef4444', '#3b82f6'],
            borderWidth: 0
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }}
    }}
}});
</script>
</body>
</html>"""

with open(OUTPUT_PATH, "w") as f:
    f.write(html)

print(f"✅ Dashboard saved to {OUTPUT_PATH}")
print(f"   {len(html)} bytes")
