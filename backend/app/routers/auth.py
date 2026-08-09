import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.linked_identity import LinkedIdentity
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, UserResponse
from app.services import google_oauth
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user_id: str) -> None:
    token = create_access_token(user_id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,   # JS cannot read this — protects against XSS token theft
        samesite=settings.cookie_samesite,
        secure=settings.is_production,
        max_age=60 * 60 * 24,  # 24 hours
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Issue JWT immediately so the user is logged in right after signing up
    _set_auth_cookie(response, str(user.id))
    return user


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _set_auth_cookie(response, str(user.id))
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Returns the currently logged-in user. Frontend calls this to check session state."""
    return current_user


@router.get("/google/start")
def google_start():
    """Step 1 of Google sign-in: send the browser to Google's consent screen."""
    state = secrets.token_urlsafe(24)
    redirect = RedirectResponse(google_oauth.build_authorize_url(state))
    # Short-lived, httpOnly — just needs to survive the round trip to Google and back
    # so /callback can confirm this request actually came from a flow we started.
    redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.is_production,
        max_age=600,
    )
    return redirect


@router.get("/google/callback")
def google_callback(code: str, state: str, request: Request, db: Session = Depends(get_db)):
    """Step 2: Google redirects back here with a one-time authorization code."""
    expected_state = request.cookies.get("oauth_state")
    if not expected_state or expected_state != state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        access_token = google_oauth.exchange_code_for_token(code)
        profile = google_oauth.get_userinfo(access_token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google sign-in failed: {e}")

    google_id = profile["sub"]
    email = profile["email"]

    identity = (
        db.query(LinkedIdentity)
        .filter(LinkedIdentity.provider == "google", LinkedIdentity.provider_user_id == google_id)
        .first()
    )

    if identity:
        user = db.query(User).filter(User.id == identity.user_id).first()
    else:
        # Google vouches for verified emails, so it's safe to attach this Google
        # identity to an existing password-based account with the same address.
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                first_name=profile.get("given_name"),
                last_name=profile.get("family_name"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        db.add(LinkedIdentity(user_id=user.id, provider="google", provider_user_id=google_id))
        db.commit()

    redirect = RedirectResponse(f"{settings.frontend_url}/dashboard")
    _set_auth_cookie(redirect, str(user.id))
    redirect.delete_cookie("oauth_state")
    return redirect
