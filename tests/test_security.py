from app.core.security import hash_password, verify_password


def test_password_hashing():
    pwd = "123456"
    hashed = hash_password(pwd)

    assert verify_password(pwd, hashed)
    assert not verify_password("errado", hashed)
