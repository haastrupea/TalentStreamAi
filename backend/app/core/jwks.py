from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=8)
def _jwk_client(jwks_url: str):
    import jwt

    return jwt.PyJWKClient(jwks_url)


class ClerkJwtVerifier:
    def verify(self, token: str) -> dict[str, Any]:
        print("======================================")
        print(token)
        print("======================================")
        try:
            import jwt
        except Exception as e:
            raise ValueError("PyJWT is required for Clerk JWT verification") from e

        from app.core.config import settings

        if not settings.clerk_jwks_url:
            raise ValueError("CLERK_JWKS_URL is required when AUTH_MODE=clerk_jwks")
        if not settings.clerk_issuer:
            raise ValueError("CLERK_ISSUER is required when AUTH_MODE=clerk_jwks")

        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_nbf": True,
            "verify_iss": True,
            "verify_aud": bool(settings.clerk_audience),
        }

        try:
            jwk_client = _jwk_client(settings.clerk_jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
        except Exception as e:
            raise ValueError("Unable to load signing key") from e

        try:
            claims = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=["RS256"],
                options=options,
                issuer=settings.clerk_issuer,
                audience=settings.clerk_audience,
            )
        except Exception as e:
            raise ValueError("Invalid or expired token") from e

        return dict(claims or {})
