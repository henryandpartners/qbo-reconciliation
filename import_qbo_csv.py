"""
QBO CSV Import Pipeline
========================
Place QBO CSV exports in data/quickbooks/ and run this script.
It detects file type by filename patterns and merges with API report data.

How to export from QuickBooks Online:
1. Go to any list/report (Chart of Accounts, Customers, etc.)
2. Click the "Export" button → "Export to Excel"
3. Save as CSV to data/quickbooks/

Supported CSV files (auto-detected by name):
- *Chart*of*Accounts*.csv or *COA*.csv → Chart of Accounts
- *Customer*.csv → Customer list
- *Vendor*.csv → Vendor list
- *Item*.csv or *Product*.csv → Items/Inventory
- *Invoice*.csv → Sales Invoices
- *Bill*.csv → Bills/Purchases
- *Trial*Balance*.csv → Trial Balance
- *General*Ledger*.csv → GL Detail
"""

import csv
import json
import os
import glob
import re
from collections import defaultdict

DATA_DIR = "data/quickbooks"
OUTPUT_DIR = "output"
API_DATA_PATH = os.path.join(OUTPUT_DIR, "qbo_all_data.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def detect_csv_type(filename):
    """Detect QBO CSV type from filename (case-insensitive)."""
    name = filename.lower()
    if "chart" in name and "account" in name:
        return "chart_of_accounts"
    if "coa" in name:
        return "chart_of_accounts"
    if "customer" in name:
        return "customers"
    if "vendor" in name:
        return "vendors"
    if "item" in name or "product" in name or "inventory" in name:
        return "items"
    if "invoice" in name:
        return "invoices"
    if "bill" in name:
        return "bills"
    if "trial" in name and "balance" in name:
        return "trial_balance"
    if "general" in name and "ledger" in name:
        return "general_ledger"
    if "profit" in name and "loss" in name:
        return "profit_and_loss"
    if "balance" in name and "sheet" in name:
        return "balance_sheet"
    return "unknown"


def parse_csv(filepath):
    """Parse a CSV file and return list of dicts.
    Handles SaasAnt/Transaction Pro format (SVP metadata rows + blank line + real headers)."""
    rows = []
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
        
        # SaasAnt format: skip SVP metadata rows (lines 0-2), find real header
        # Pattern: [SVP row] [Title row] [Date row OR blank] [blank] [Real headers]
        header_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip().strip('"').strip()
            # Skip SVP rows, title rows, date rows, blank lines
            if not stripped:
                continue
            if stripped.startswith("SVP"):
                continue
            if stripped in lines[1].strip().strip('"').strip() if len(lines) > 1 else "":
                continue  # Skip the title row
            # Try to detect if this is a blank/title row by checking if it has a date pattern
            if any(m in stripped.lower() for m in ["january", "february", "march", "april", "may", "june", 
                                                     "july", "august", "september", "october", "november", "december",
                                                     "all dates", "this month", "this quarter", "this year"]):
                continue
            # Candidate for real header
            if line.count(',') >= 2 or '"' in line:
                header_idx = i
                break
            header_idx = i
        
        # Parse from the detected header line
        content = "".join(lines[header_idx:])
        reader = csv.DictReader(content.splitlines())
        for row in reader:
            cleaned = {}
            for k, v in row.items():
                if k and k.strip():
                    key = k.strip().strip("\ufeff").strip()
                    val = v.strip() if v else ""
                    cleaned[key] = val
            if cleaned and any(v for v in cleaned.values()):  # Only add rows with at least one value
                rows.append(cleaned)
    except Exception as e:
        print(f"  ❌ Error parsing {filepath}: {e}")
    return rows


def main():
    print("=" * 60)
    print("📊 QBO CSV DATA IMPORT")
    print("=" * 60)

    # Find all CSV files
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not csv_files:
        print(f"\n❌ No CSV files found in {DATA_DIR}/")
        print("\n📋 How to export from QuickBooks Online:")
        print("  1. Go to any list (Chart of Accounts, Customers, etc.)")
        print("  2. Click the gear icon → Export → Export to Excel")
        print("  3. Save as CSV to:", os.path.abspath(DATA_DIR) + "/")
        print("\n   Supported: Chart of Accounts, Customers, Vendors, Items,")
        print("              Invoices, Bills, Trial Balance, General Ledger")
        return

    # Load existing API data
    api_data = {}
    if os.path.exists(API_DATA_PATH):
        with open(API_DATA_PATH) as f:
            api_data = json.load(f)
        print(f"\n✅ Loaded existing API data ({len(api_data)} sections)")

    all_data = {"api": api_data, "csv": {}}

    for filepath in sorted(csv_files):
        filename = os.path.basename(filepath)
        csv_type = detect_csv_type(filename)
        rows = parse_csv(filepath)

        if rows:
            all_data["csv"][csv_type] = {
                "source": filename,
                "count": len(rows),
                "columns": list(rows[0].keys()),
                "data": rows,
            }
            print(f"\n✅ {csv_type.upper():20s} | {filename:40s} | {len(rows):4d} rows")
            print(f"   Columns: {', '.join(list(rows[0].keys())[:6])}{'...' if len(rows[0]) > 6 else ''}")
        else:
            print(f"\n⚠️  {csv_type.upper():20s} | {filename:40s} | 0 rows (empty or unreadable)")

    # Save combined data
    combined_path = os.path.join(OUTPUT_DIR, "qbo_combined_data.json")
    with open(combined_path, "w") as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"\n✅ Combined data saved to {combined_path}")

    # Summary
    total_csv_rows = sum(v["count"] for v in all_data["csv"].values())
    print(f"\n{'='*60}")
    print(f"📊 IMPORT SUMMARY: {len(csv_files)} files, {total_csv_rows} total rows")
    print(f"{'='*60}")
    print(f"\nNext step: python3 generate_dashboard.py  →  rebuild dashboard with CSV data")


if __name__ == "__main__":
    main()
