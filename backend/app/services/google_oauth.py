from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def build_authorize_url(state: str) -> str:
    """The URL we redirect the browser to so the user can approve Wallit on Google."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> str:
    """Trade the one-time authorization code for an access token."""
    response = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_userinfo(access_token: str) -> dict:
    """Google's own profile for whoever just authorized us — id, email, name."""
    response = httpx.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
