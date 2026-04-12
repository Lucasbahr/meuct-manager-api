from cryptography.fernet import Fernet

from app.core import payment_credentials_crypto as pcc


def test_encrypt_decrypt_roundtrip(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("PAYMENT_CREDENTIALS_FERNET_KEY", key)

    secret = "my-paypal-secret-xyz"
    enc = pcc.encrypt_credential(secret)
    assert enc != secret
    assert pcc.decrypt_credential(enc) == secret
    hint = pcc.mask_credential_suffix(enc)
    assert hint is not None
    assert "xyz" in hint


def test_without_key_stores_plaintext(monkeypatch):
    monkeypatch.delenv("PAYMENT_CREDENTIALS_FERNET_KEY", raising=False)

    s = "plain-id"
    assert pcc.encrypt_credential(s) == s
    assert pcc.decrypt_credential(s) == s
    assert pcc.fernet_key_configured() is False
