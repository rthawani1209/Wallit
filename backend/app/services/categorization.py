"""
Transaction categorization, applied at Plaid sync time.

Every transaction is guaranteed a category — required for the spend chart and
what-if simulator to reflect real totals. Resolution order:
  1. Plaid's own `personal_finance_category` (real bank data, high coverage,
     ML-based — far more reliable than string-matching a merchant name)
  2. Keyword matching on merchant name (fallback for sparse/missing Plaid data)
  3. "Fees/Other" (guaranteed catch-all — a transaction is never left uncategorized)

This is a precursor to Phase 3's automated nightly job (which will also handle
subscription and anomaly detection) — this module only covers categorization.
"""

FALLBACK_CATEGORY = "Fees/Other"

# Plaid's `personal_finance_category.primary` -> our category taxonomy.
# See https://plaid.com/docs/api/products/transactions/#personal-finance-category
PLAID_PRIMARY_MAP: dict[str, str] = {
    "INCOME": "Income",
    "TRANSFER_IN": "Income",
    "TRANSFER_OUT": "Fees/Other",
    "LOAN_PAYMENTS": "Debt",
    "BANK_FEES": "Fees/Other",
    "ENTERTAINMENT": "Entertainment",
    "FOOD_AND_DRINK": "Food",
    "GENERAL_MERCHANDISE": "Shopping",
    "HOME_IMPROVEMENT": "Housing",
    "MEDICAL": "Health",
    "PERSONAL_CARE": "Health",
    "GENERAL_SERVICES": "Fees/Other",
    "GOVERNMENT_AND_NON_PROFIT": "Giving",
    "TRANSPORTATION": "Transportation",
    "TRAVEL": "Transportation",
    "RENT_AND_UTILITIES": "Housing",  # refined below via `detailed`
    # Deliberately no "OTHER" entry: that's Plaid's own "I don't know" signal, not a
    # confident classification — treating it as unmapped lets keyword/Claude fallback
    # tiers take a real shot instead of dumping it straight into Fees/Other.
}

# RENT_AND_UTILITIES covers both rent/mortgage and utility bills under one Plaid
# primary category — split it using the detailed subcategory instead.
UTILITIES_DETAILED = {
    "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY",
    "RENT_AND_UTILITIES_INTERNET_AND_CABLE",
    "RENT_AND_UTILITIES_SEWAGE_AND_WASTE_MANAGEMENT",
    "RENT_AND_UTILITIES_TELEPHONE",
    "RENT_AND_UTILITIES_WATER",
    "RENT_AND_UTILITIES_OTHER_UTILITIES",
}

# TRANSFER_OUT/TRANSFER_IN are generic "money moved between accounts" primaries —
# when the detailed subcategory identifies it as going to/from savings or investment,
# that's a much better fit for our "Savings" category than the Fees/Other catch-all.
SAVINGS_DETAILED = {
    "TRANSFER_OUT_SAVINGS",
    "TRANSFER_OUT_INVESTMENT_AND_RETIREMENT_FUNDS",
    "TRANSFER_IN_SAVINGS",
    "TRANSFER_IN_INVESTMENT_AND_RETIREMENT_FUNDS",
}

# Keyword fallback for when Plaid's category is missing (rare) or unmapped.
# Ordered so more specific keywords are checked before generic ones.
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Subscriptions", ["netflix", "spotify", "hulu", "disney+", "hbo", "apple music", "youtube premium"]),
    ("Food", ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "kfc", "chipotle",
              "pizza", "doordash", "grubhub", "uber eats", "burger", "whole foods",
              "safeway", "kroger", "trader joe", "grocery", "supermarket"]),
    ("Transportation", ["uber", "lyft", "airlines", "delta", "southwest", "gas station",
                         "shell", "chevron", "parking", "transit", "hotel", "airbnb"]),
    ("Housing", ["rent", "mortgage", "landlord", "property management"]),
    ("Utilities", ["electric", "comcast", "at&t", "verizon", "water bill", "pg&e", "utility"]),
    ("Entertainment", ["cinema", "amc", "movie", "concert", "ticketmaster", "steam"]),
    ("Health", ["cvs", "walgreens", "pharmacy", "medical", "doctor", "dental", "clinic", "gym"]),
    ("Shopping", ["amazon", "walmart", "target", "best buy", "sparkfun", "bicycle shop"]),
    ("Debt", ["loan payment", "student loan", "credit card payment", "auto loan"]),
    ("Savings", ["savings transfer", "investment", "brokerage", "401k", "ira contribution"]),
    ("Giving", ["donation", "charity", "nonprofit", "church", "gofundme"]),
    ("Income", ["payroll", "salary", "direct deposit", "interest payment", "intrst pymnt"]),
]


def categorize_from_plaid(personal_finance_category: dict | None) -> str | None:
    """Map Plaid's personal_finance_category onto our taxonomy. Returns None if absent/unmapped."""
    if not personal_finance_category:
        return None
    primary = personal_finance_category.get("primary")
    detailed = personal_finance_category.get("detailed")
    if detailed in SAVINGS_DETAILED:
        return "Savings"
    if primary == "RENT_AND_UTILITIES":
        return "Utilities" if detailed in UTILITIES_DETAILED else "Housing"
    return PLAID_PRIMARY_MAP.get(primary)


def categorize_from_keywords(merchant_name: str | None) -> str | None:
    """Substring match on merchant name. Returns None if nothing matches."""
    if not merchant_name:
        return None
    name = merchant_name.lower()
    for category_name, keywords in CATEGORY_KEYWORDS:
        if any(keyword in name for keyword in keywords):
            return category_name
    return None


def resolve_category(merchant_name: str | None, personal_finance_category: dict | None) -> str:
    """
    Always returns a category name — Plaid data first, keyword fallback second,
    guaranteed "Fees/Other" catch-all last. A transaction is never left uncategorized.
    """
    return (
        categorize_from_plaid(personal_finance_category)
        or categorize_from_keywords(merchant_name)
        or FALLBACK_CATEGORY
    )
