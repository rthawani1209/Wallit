import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

from app.config import settings


def _get_client() -> plaid_api.PlaidApi:
    env_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development,
        "production": plaid.Environment.Production,
    }
    configuration = plaid.Configuration(
        host=env_map[settings.plaid_env],
        api_key={
            "clientId": settings.plaid_client_id,
            "secret": settings.plaid_secret,
        },
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def create_link_token(user_id: str) -> str:
    """Create a Plaid Link token — the frontend uses this to open the bank-connect UI."""
    client = _get_client()
    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
        client_name="Wallit",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    response = client.link_token_create(request)
    return response["link_token"]


def exchange_public_token(public_token: str) -> str:
    """Exchange the short-lived public token from Plaid Link for a permanent access token."""
    client = _get_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)
    return response["access_token"]


def get_accounts(access_token: str) -> list[dict]:
    """Fetch account balances for a connected bank."""
    client = _get_client()
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    return [
        {
            "plaid_account_id": a["account_id"],
            "name": a["name"],
            "type": str(a["type"]),
            "current_balance": float(a["balances"]["current"] or 0),
        }
        for a in response["accounts"]
    ]


def sync_transactions(access_token: str, cursor: str | None = None) -> tuple[list[dict], str]:
    """
    Pull transactions using Plaid's sync API (returns only what's new/changed since last sync).
    Returns a list of transaction dicts and the new cursor to store for next time.
    """
    client = _get_client()
    all_added = []
    has_more = True

    while has_more:
        kwargs = {"access_token": access_token}
        if cursor:
            kwargs["cursor"] = cursor
        request = TransactionsSyncRequest(**kwargs)
        response = client.transactions_sync(request)
        all_added.extend(response["added"])
        cursor = response["next_cursor"]
        has_more = response["has_more"]

    transactions = [
        {
            "plaid_transaction_id": t["transaction_id"],
            "amount": float(t["amount"]),
            "merchant_name": t.get("merchant_name") or t.get("name"),
            "date": t["date"],
            "plaid_account_id": t["account_id"],
        }
        for t in all_added
    ]
    return transactions, cursor