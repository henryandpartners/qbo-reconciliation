"""
QuickBooks Online API Client

Fetches accounting data from QBO API v3 using OAuth2 tokens.
Handles token refresh, error handling, and data transformation.
"""
import httpx
import json
from typing import Optional


QB_BASE = "https://quickbooks.api.intuit.com/v3/company"
QB_SANDBOX = "https://sandbox-quickbooks.api.intuit.com/v3/company"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"


class QBOClient:
    def __init__(self, company_id: str, access_token: str, refresh_token: str = "",
                 client_id: str = "", client_secret: str = "",
                 sandbox: bool = False):
        self.company_id = company_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        base = QB_SANDBOX if sandbox else QB_BASE
        self.base = f"{base}/{company_id}"

    def _query(self, sql: str) -> dict:
        """Execute a QBO query."""
        token = self.access_token.strip()
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base}/query",
                params={"query": sql},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=30,
            )
        if resp.status_code == 401 and self.refresh_token and self.client_id:
            raise PermissionError("Token expired — needs refresh")
        if resp.status_code != 200:
            fault = resp.json().get("fault", {})
            return {"error": fault, "status": resp.status_code}
        return resp.json()

    def _get_report(self, report_name: str, params: dict = None) -> dict:
        url = f"{self.base}/reports/{report_name}"
        token = self.access_token.strip()
        with httpx.Client() as client:
            resp = client.get(
                url,
                params=params or {},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=30,
            )
        if resp.status_code != 200:
            return {"error": resp.json().get("fault", {}), "status": resp.status_code}
        return resp.json()

    def get_company_info(self) -> dict:
        return self._query("select * from CompanyInfo maxresults 1")

    def get_chart_of_accounts(self) -> list:
        result = self._query("select * from Account maxresults 200")
        return (result.get("QueryResponse", {}) or {}).get("Account", [])

    def get_profit_and_loss(self) -> dict:
        return self._get_report("ProfitAndLoss", {"date_macro": "This Fiscal Year"})

    def get_balance_sheet(self) -> dict:
        return self._get_report("BalanceSheet", {"date_macro": "Today"})

    def get_invoices(self, max_results: int = 200) -> list:
        result = self._query(f"select * from Invoice where TxnDate >= '2025-01-01' maxresults {max_results}")
        return (result.get("QueryResponse", {}) or {}).get("Invoice", [])

    def get_customers(self) -> list:
        result = self._query("select * from Customer maxresults 200")
        return (result.get("QueryResponse", {}) or {}).get("Customer", [])

    def get_vendors(self) -> list:
        result = self._query("select * from Vendor maxresults 200")
        return (result.get("QueryResponse", {}) or {}).get("Vendor", [])

    def get_items(self) -> list:
        result = self._query("select * from Item maxresults 200")
        return (result.get("QueryResponse", {}) or {}).get("Item", [])

    def get_bills(self, max_results: int = 200) -> list:
        result = self._query(f"select * from Bill where TxnDate >= '2025-01-01' maxresults {max_results}")
        return (result.get("QueryResponse", {}) or {}).get("Bill", [])

    def get_purchases(self, max_results: int = 200) -> list:
        result = self._query(f"select * from Purchase where TxnDate >= '2025-01-01' maxresults {max_results}")
        return (result.get("QueryResponse", {}) or {}).get("Purchase", [])

    def get_estimates(self, max_results: int = 200) -> list:
        result = self._query(f"select * from Estimate where TxnDate >= '2025-01-01' maxresults {max_results}")
        return (result.get("QueryResponse", {}) or {}).get("Estimate", [])

    def refresh_access_token(self) -> dict:
        """Exchange refresh token for new access token."""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return {"error": "Missing refresh credentials"}
        with httpx.Client() as client:
            resp = client.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                auth=(self.client_id, self.client_secret),
                timeout=30,
            )
        data = resp.json()
        if resp.status_code == 200:
            self.access_token = data.get("access_token", self.access_token)
            self.refresh_token = data.get("refresh_token", self.refresh_token)
        return data


def analyze_qbo_data(client: QBOClient) -> dict:
    """Fetch and analyze all QBO data for the dashboard."""
    result = {"status": "ok", "error": None, "data": {}}

    try:
        result["data"]["company"] = client.get_company_info()
    except Exception as e:
        result["data"]["company"] = {"error": str(e)}

    # Chart of Accounts
    try:
        accounts = client.get_chart_of_accounts()
        total_assets = sum(a.get("CurrentBalance", 0) for a in accounts
                          if a.get("Classification") == "Asset")
        total_liabilities = sum(a.get("CurrentBalance", 0) for a in accounts
                               if a.get("Classification") == "Liability")
        total_equity = sum(a.get("CurrentBalance", 0) for a in accounts
                          if a.get("Classification") == "Equity")
        total_revenue = sum(a.get("CurrentBalance", 0) for a in accounts
                           if a.get("Classification") == "Revenue")
        total_expenses = sum(a.get("CurrentBalance", 0) for a in accounts
                            if a.get("Classification") == "Expense")

        # Account types breakdown
        account_types = {}
        for a in accounts:
            at = a.get("AccountType", "Other")
            account_types[at] = account_types.get(at, 0) + 1

        result["data"]["coa"] = {
            "total_accounts": len(accounts),
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "account_types": account_types,
        }
    except Exception as e:
        result["data"]["coa"] = {"error": str(e)}

    # P&L
    try:
        pl = client.get_profit_and_loss()
        rows = pl.get("Rows", {}).get("Row", [])
        income = 0
        expenses = 0
        net = 0
        for row in rows:
            if row.get("type") == "Section":
                for cell in row.get("Rows", {}).get("Row", []):
                    cols = cell.get("ColData", [])
                    if len(cols) >= 2:
                        val = _parse_amount(cols[-1].get("value", "0"))
                        header = cols[0].get("value", "").lower()
                        if "total income" in header or "total revenue" in header:
                            income = val
                        elif "total expense" in header or "net ordinary" in header and "income" not in header:
                            expenses = val
                        elif "net income" in header or "net profit" in header:
                            net = val
        result["data"]["pl"] = {
            "income": income,
            "expenses": expenses,
            "net_income": net or (income - expenses),
        }
    except Exception as e:
        result["data"]["pl"] = {"error": str(e)}

    # Invoices
    try:
        invoices = client.get_invoices()
        total_invoiced = sum(i.get("TotalAmt", 0) for i in invoices)
        paid = sum(i.get("TotalAmt", 0) for i in invoices
                   if i.get("Balance", 0) == 0)
        unpaid = sum(i.get("Balance", 0) for i in invoices)
        overdue = sum(i.get("Balance", 0) for i in invoices
                      if i.get("Balance", 0) > 0)

        # Monthly invoice summary
        from collections import Counter
        monthly = Counter()
        for inv in invoices:
            date = inv.get("TxnDate", "")[:7]  # YYYY-MM
            monthly[date] += 1

        result["data"]["invoices"] = {
            "total": len(invoices),
            "total_amount": total_invoiced,
            "paid": paid,
            "unpaid": unpaid,
            "overdue": overdue,
            "monthly_counts": dict(sorted(monthly.items())),
        }
    except Exception as e:
        result["data"]["invoices"] = {"error": str(e)}

    # Customers
    try:
        customers = client.get_customers()
        result["data"]["customers"] = {
            "total": len(customers),
        }
    except Exception as e:
        result["data"]["customers"] = {"error": str(e)}

    # Items/Inventory
    try:
        items = client.get_items()
        inventory_count = sum(1 for i in items if i.get("Type") == "Inventory")
        service_count = sum(1 for i in items if i.get("Type") == "Service")
        non_inventory = sum(1 for i in items if i.get("Type") == "NonInventory")

        total_inv_value = 0
        low_stock = 0
        for i in items:
            if i.get("Type") == "Inventory":
                qty = i.get("QtyOnHand", 0)
                cost = i.get("PurchaseCost", 0) or 0
                total_inv_value += qty * cost
                if qty <= 5:
                    low_stock += 1

        result["data"]["items"] = {
            "total": len(items),
            "inventory": inventory_count,
            "service": service_count,
            "non_inventory": non_inventory,
            "total_inv_value": total_inv_value,
            "low_stock": low_stock,
        }
    except Exception as e:
        result["data"]["items"] = {"error": str(e)}

    return result


def _parse_amount(val: str) -> float:
    if not val:
        return 0.0
    try:
        return float(val.replace(",", "").replace("$", "").replace("(", "-").replace(")", "").strip())
    except (ValueError, AttributeError):
        return 0.0
