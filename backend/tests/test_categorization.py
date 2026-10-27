from app.services import categorization as c


def test_plaid_primary_maps_to_our_category():
    assert c.categorize_from_plaid({"primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_COFFEE"}) == "Food"


def test_rent_and_utilities_split_by_detail():
    assert c.categorize_from_plaid({"primary": "RENT_AND_UTILITIES", "detailed": "RENT_AND_UTILITIES_RENT"}) == "Housing"
    assert (
        c.categorize_from_plaid({"primary": "RENT_AND_UTILITIES", "detailed": "RENT_AND_UTILITIES_WATER"})
        == "Utilities"
    )


def test_savings_transfer_beats_generic_transfer():
    assert c.categorize_from_plaid({"primary": "TRANSFER_OUT", "detailed": "TRANSFER_OUT_SAVINGS"}) == "Savings"
    assert c.categorize_from_plaid({"primary": "TRANSFER_OUT", "detailed": "TRANSFER_OUT_ACCOUNT_TRANSFER"}) == "Transfer"


def test_plaid_other_falls_through():
    assert c.categorize_from_plaid({"primary": "OTHER", "detailed": "OTHER_OTHER"}) is None


def test_keywords_check_specific_before_generic():
    # "uber eats" has to land in Food before the plain "uber" rule sends it to Transportation
    assert c.categorize_from_keywords("UBER EATS 8005928996") == "Food"
    assert c.categorize_from_keywords("Uber Trip") == "Transportation"


def test_resolve_never_returns_nothing():
    # no Plaid category, no keyword hit, no API key configured
    assert c.resolve_category("ZZQX Holdings LLC", None, 12.0) == c.FALLBACK_CATEGORY


def test_resolve_prefers_plaid_over_keywords():
    pfc = {"primary": "GENERAL_MERCHANDISE", "detailed": "GENERAL_MERCHANDISE_OTHER"}
    assert c.resolve_category("Starbucks", pfc, 5.0) == "Shopping"
