# FastAPI classroom project — Authentication basics

**Class time** 30–35 minutes. Students log in as a demo user, receive a short-lived JWT, and use it to access a protected profile route.

**Scope** The OAuth2 resource owner password credentials grant is a legacy flow. It asks the client to collect the user's password. RFC 9700 prohibits this grant for real deployments. Use this demo on localhost with the supplied fictional credentials. For new user-facing applications, use Authorization Code with PKCE through an identity provider.

## 1. Run on Windows

Open PowerShell in this folder with Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app
```

Open [Swagger UI](http://127.0.0.1:8000/docs). Use the demo username `student` and password `classroom-pass`.

## 2. Walk through the flow

1. **Verify the password.** The client sends a URL-encoded form to `POST /token` with `grant_type=password`, `username`, and `password`. Argon2id verifies the submitted password against the stored salted hash. The account record stores the hash. The readable password in the source only seeds the fictional account.
2. **Issue a signed token.** After a successful login, PyJWT signs an access token with HS256. The `sub` claim identifies the user, `iat` records when it was issued, and `exp` sets its expiration 15 minutes later. JWT claims are readable, so keep passwords and other secrets out of them.
3. **Send the bearer token.** The client includes `Authorization: Bearer <token>` on a request to `GET /me`. `OAuth2PasswordBearer` extracts the token. The `get_current_user` dependency checks the signature, required claims, expiration, and user before FastAPI calls the route.

The signing key is generated in memory for this demo. Restarting the server invalidates previously issued tokens.

| Method and path | What to show | Expected status |
| --- | --- | --- |
| `GET /public` | Works without credentials | `200` |
| `POST /token` | Form credentials produce a JWT | `200` on success, `400 invalid_grant` for wrong credentials, `422` for invalid form data |
| `GET /me` | A valid bearer token unlocks the profile | `200` with a valid token, `401` for a missing, invalid, or expired token |

## 3. Demo in Swagger UI

1. Execute `GET /public` and then `GET /me`. Compare the `200` and `401` responses.
2. Execute `POST /token` with the demo username, an incorrect password, and `grant_type` set to `password`. Look for `{"error": "invalid_grant"}`.
3. Click **Authorize**, enter the demo username and password, and leave the client ID and secret empty. Swagger UI requests a token and adds it to protected requests.
4. Execute `GET /me` again. Expect `{"username": "student"}`. Find the bearer header in Swagger UI's generated request.
5. Use **Authorize → Logout** and run `GET /me` again. Expect `401` because Swagger UI has stopped sending the bearer token. An issued token remains usable until it expires or the signing key changes in this demo.

## 4. Student exercise

Add `GET /grades` and protect it with the same `Depends(get_current_user)` pattern used by `GET /me`. Confirm it returns `401` before authorization and `200` after authorization.

For a quick expiration demo, temporarily change `TOKEN_LIFETIME` to five seconds, restart the server, and authorize again. Wait more than five seconds, then call `GET /me` with the expired token.

[FastAPI JWT tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) · [RFC 9700 on the password grant](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.4) · [Argon2 password hashing](https://argon2-cffi.readthedocs.io/en/stable/howto.html)
