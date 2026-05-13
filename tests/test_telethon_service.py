from app.core.security import SessionCipher


def test_session_cipher_roundtrip():
    cipher = SessionCipher("x" * 32)
    encrypted = cipher.encrypt("plain-session")
    assert encrypted != "plain-session"
    assert cipher.decrypt(encrypted) == "plain-session"
