"""
Lightweight rule-based transaction categorization, applied at Plaid sync time.

This is a precursor to Phase 3's automated nightly job (which will also handle
subscription and anomaly detection) — this module only covers categorization,
via simple keyword matching on merchant name. Good enough to unblock testing
of category-dependent features (spend chart, what-if simulator) without manual
tagging; a real ML/rules-engine categorizer can replace this in Phase 3.
"""

# Ordered so more specific keywords are checked before generic ones.
CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Subscriptions", ["netflix", "spotify", "hulu", "disney+", "hbo", "apple music", "youtube premium"]),
    ("Dining", ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "kfc", "chipotle",
                "pizza", "doordash", "grubhub", "uber eats", "burger"]),
    ("Groceries", ["whole foods", "safeway", "kroger", "trader joe", "grocery", "supermarket"]),
    ("Transportation", ["uber", "lyft", "united airlines", "delta", "southwest", "airlines",
                         "gas station", "shell", "chevron", "parking", "transit"]),
    ("Housing", ["rent", "mortgage", "landlord", "property management"]),
    ("Utilities", ["electric", "comcast", "at&t", "verizon", "water bill", "pg&e", "utility"]),
    ("Entertainment", ["cinema", "amc", "movie", "concert", "ticketmaster", "steam"]),
    ("Healthcare", ["cvs", "walgreens", "pharmacy", "medical", "doctor", "dental", "clinic"]),
    ("Shopping", ["amazon", "walmart", "target", "best buy", "sparkfun", "bicycle shop"]),
    ("Travel", ["hotel", "airbnb", "marriott", "hilton", "expedia"]),
    ("Income", ["payroll", "salary", "direct deposit", "interest payment", "intrst pymnt"]),
]


def categorize(merchant_name: str | None) -> str | None:
    """Return a category name for a merchant, or None if no rule matches (stays Uncategorized)."""
    if not merchant_name:
        return None
    name = merchant_name.lower()
    for category_name, keywords in CATEGORY_KEYWORDS:
        if any(keyword in name for keyword in keywords):
            return category_name
    return None
