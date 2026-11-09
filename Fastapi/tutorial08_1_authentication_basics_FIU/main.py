"""Local classroom demo of the legacy OAuth2 password grant and JWTs."""

from datetime import datetime, timedelta, timezone
from secrets import token_bytes
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

app = FastAPI(title="FastAPI Authentication Basics")

ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(minutes=15)
# This local demo uses one server process. Restarting it invalidates old tokens.
SIGNING_KEY = token_bytes(32)

password_hasher = PasswordHasher()
DEMO_USERNAME = "student"
# Seed a fictional account. The runtime user record holds the Argon2id hash.
demo_user = {
    "username": DEMO_USERNAME,
    "password_hash": password_hasher.hash("classroom-pass"),
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
LoginForm = Annotated[OAuth2PasswordRequestFormStrict, Depends()]
BearerToken = Annotated[str, Depends(oauth2_scheme)]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@app.post("/token", response_model=TokenResponse)
def issue_token(form: LoginForm, response: Response) -> TokenResponse | JSONResponse:
    """Verify the form credentials and issue a short-lived access token."""
    # Run the same password check even if the username is unknown.
    try:
        password_hasher.verify(demo_user["password_hash"], form.password)
        password_matches = True
    except VerifyMismatchError:
        password_matches = False

    if form.username != DEMO_USERNAME or not password_matches:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_grant"},
        )

    now = datetime.now(timezone.utc)
    access_token = jwt.encode(
        {"sub": DEMO_USERNAME, "iat": now, "exp": now + TOKEN_LIFETIME},
        SIGNING_KEY,
        algorithm=ALGORITHM,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(access_token=access_token, token_type="bearer")


def get_current_user(token: BearerToken) -> str:
    """Verify the bearer token before a protected handler can run."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = jwt.decode(
            token,
            SIGNING_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
    except InvalidTokenError:
        raise credentials_error from None

    if claims["sub"] != DEMO_USERNAME:
        raise credentials_error
    return DEMO_USERNAME


@app.get("/public")
def public_page() -> dict[str, str]:
    """Show a route that anyone can call."""
    return {"message": "This route is public"}


@app.get("/me")
def read_profile(username: Annotated[str, Depends(get_current_user)]) -> dict[str, str]:
    """Show the authenticated username."""
    return {"username": username}
