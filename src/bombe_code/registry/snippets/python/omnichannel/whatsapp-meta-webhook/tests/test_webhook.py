import hmac
import hashlib
from webhook import verify_signature, verify_challenge

def test_verify_signature():
    secret = "secret-key"
    payload = b'{"object":"whatsapp_business_account"}'
    mac = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_signature(payload, f"sha256={mac}", secret) is True
    assert verify_signature(payload, "sha256=tampered", secret) is False
