"""
Pull all QBO data and save locally as JSON files.
This script calls the Vercel-deployed dashboard API which has the Client ID/Secret
and can auto-refresh tokens.
"""
import httpx
import json
import urllib.parse
import sys
import os

COMPANY_ID = "9341453354898311"
ACCESS_TOKEN = "ABBbpF7CfFP3xJcZOK7wgKNeginC72MsDip5kyo5vJyjavJF0P"
REFRESH_TOKEN = "BrUWzg5pFlpaFTFctaSOaPlhj8O5Paa13Gcw6cf0"
OUTPUT_DIR = "/Users/fathomers/workspace/qbo-oauth-callback/output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_json(endpoint: str, params: dict = None) -> dict:
    """Call QBO API directly with the access token."""
    url = f"https://quickbooks.api.intuit.com/v3/company/{COMPANY_ID}{endpoint}"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json",
    }
    resp = httpx.get(url, params=params, headers=headers, timeout=30)
    return {"status": resp.status_code, "data": resp.json()}

# 1. Test basic connectivity - try all major QBO endpoints
print("=" * 60)
print("QBO DATA PULL - STEP BY STEP")
print("=" * 60)

endpoints = [
    ("CompanyInfo", f"/companyinfo/{COMPANY_ID}", None),
    ("Chart of Accounts", "/query", {"query": "select * from Account maxresults 200"}),
    ("Customers", "/query", {"query": "select * from Customer maxresults 200"}),
    ("Vendors", "/query", {"query": "select * from Vendor maxresults 200"}),
    ("Items", "/query", {"query": "select * from Item maxresults 200"}),
    ("Invoices", "/query", {"query": "select * from Invoice where TxnDate >= '2025-01-01' maxresults 200"}),
    ("Bills", "/query", {"query": "select * from Bill where TxnDate >= '2025-01-01' maxresults 200"}),
    ("Purchases", "/query", {"query": "select * from Purchase where TxnDate >= '2025-01-01' maxresults 200"}),
]

all_results = {}
for name, endpoint, params in endpoints:
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"https://quickbooks.api.intuit.com/v3/company/{COMPANY_ID}{endpoint}?{qs}"
    else:
        url = f"https://quickbooks.api.intuit.com/v3/company/{COMPANY_ID}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json",
    }
    
    print(f"\n--- {name} ---")
    print(f"URL: {url[:120]}")
    
    resp = httpx.get(url, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    
    data = resp.json()
    
    # Save if successful
    if resp.status_code == 200:
        safe_name = name.lower().replace(" ", "_")
        filepath = f"{OUTPUT_DIR}/{safe_name}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"✅ Saved to {filepath}")
        
        # Show summary
        if name == "CompanyInfo":
            ci = data.get("CompanyInfo", {})
            print(f"   Company Name: {ci.get('CompanyName', 'N/A')}")
            print(f"   Country: {ci.get('Country', 'N/A')}")
        elif name == "Chart of Accounts":
            accounts = (data.get("QueryResponse", {}) or {}).get("Account", [])
            print(f"   Total accounts: {len(accounts)}")
            for a in accounts[:5]:
                print(f"   - {a.get('Name', 'N/A')}: {a.get('CurrentBalance', 0)} ({a.get('Classification', 'N/A')})")
            if len(accounts) > 5:
                print(f"   ... and {len(accounts)-5} more")
        else:
            qr = data.get("QueryResponse", {}) or {}
            for key in qr:
                items = qr[key]
                if isinstance(items, list):
                    print(f"   Total: {len(items)}")
                    if items:
                        print(f"   First: {items[0].get('DisplayName') or items[0].get('DocNumber') or items[0].get('Name', 'N/A')}")
    else:
        fault = data.get("fault", {})
        errs = fault.get("error", [])
        if errs:
            print(f"❌ {errs[0].get('message', resp.text[:200])}")
        else:
            print(f"❌ {resp.text[:200]}")
    
    all_results[name] = {"status": resp.status_code, "data": data}

# Final summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
successes = [n for n, r in all_results.items() if r["status"] == 200]
failures = [n for n, r in all_results.items() if r["status"] != 200]
print(f"✅ Successful: {len(successes)} - {', '.join(successes)}")
print(f"❌ Failed: {len(failures)} - {', '.join(failures)}")
