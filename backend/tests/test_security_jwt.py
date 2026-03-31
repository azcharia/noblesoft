import types

from app.core import security


def test_verify_jwt_token_disables_iat_check_for_hs_tokens(monkeypatch):
    captured = {}

    monkeypatch.setattr(security.jwt, "get_unverified_header", lambda token: {"alg": "HS256"})

    def fake_decode(token, key, algorithms, audience, options=None, **kwargs):
        captured["options"] = options
        return {
            "sub": "user-1",
            "exp": 4102444800,  # 2100-01-01 UTC
        }

    monkeypatch.setattr(security.jwt, "decode", fake_decode)

    payload = security.verify_jwt_token("fake-token")

    assert payload["sub"] == "user-1"
    assert captured["options"] == {"verify_iat": False}


def test_verify_jwt_token_disables_iat_check_for_asymmetric_tokens(monkeypatch):
    captured = {}

    monkeypatch.setattr(security.jwt, "get_unverified_header", lambda token: {"alg": "RS256"})

    class FakeSigningKey:
        key = "public-key"

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, token):
            return FakeSigningKey()

    monkeypatch.setattr(security, "_get_jwks_client", lambda: FakeJwksClient())

    def fake_decode(token, key, algorithms, audience, issuer=None, options=None, **kwargs):
        captured["options"] = options
        captured["issuer"] = issuer
        return {
            "sub": "user-2",
            "exp": 4102444800,
        }

    monkeypatch.setattr(security.jwt, "decode", fake_decode)

    payload = security.verify_jwt_token("fake-token")

    assert payload["sub"] == "user-2"
    assert captured["issuer"] == f"{security.settings.SUPABASE_URL}/auth/v1"
    assert captured["options"] == {"verify_iat": False}
