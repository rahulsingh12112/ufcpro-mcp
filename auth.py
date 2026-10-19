#!/usr/bin/env python3
"""Cognito OAuth2 (authorization-code) login and JWT verification for the chat app."""

import os
import time
import json
import base64
import urllib.parse
import urllib.request

import jwt
from jwt import PyJWKClient

REGION = os.environ.get("AWS_REGION", "us-east-1")
USER_POOL_ID = os.environ.get("COGNITO_POOL_ID", "us-east-1_5m6YFk458")
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "49uc5q4r2lm1bckj7uk8s8mjfh")
CLIENT_SECRET = os.environ.get("COGNITO_CLIENT_SECRET", "")
DOMAIN = os.environ.get(
    "COGNITO_DOMAIN",
    "https://us-east-15m6yfk458.auth.us-east-1.amazoncognito.com",
).rstrip("/")
REDIRECT_URI = os.environ.get("COGNITO_REDIRECT_URI", "http://localhost:8800/callback")

ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"

_jwk_client = PyJWKClient(JWKS_URL)


def login_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid email",
        "redirect_uri": REDIRECT_URI,
    }
    return f"{DOMAIN}/login?" + urllib.parse.urlencode(params)


def logout_url(return_to: str) -> str:
    params = {"client_id": CLIENT_ID, "logout_uri": return_to}
    return f"{DOMAIN}/logout?" + urllib.parse.urlencode(params)


def exchange_code_for_tokens(code: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }).encode()

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if CLIENT_SECRET:
        basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"

    req = urllib.request.Request(f"{DOMAIN}/oauth2/token", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def verify_token(token: str) -> dict:
    signing_key = _jwk_client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=ISSUER,
        options={"verify_aud": False},
    )
    if claims.get("token_use") == "id" and claims.get("aud") != CLIENT_ID:
        raise jwt.InvalidTokenError("audience mismatch")
    return claims
