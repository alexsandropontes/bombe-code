import hmac
import hashlib

def verify_signature(payload: bytes, signature_header: str, app_secret: str) -> bool:
    if not payload or not signature_header or not app_secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    
    expected_hash = signature_header[len("sha256="):].strip()
    mac = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256)
    actual_hash = mac.hexdigest()
    return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())

def verify_challenge(mode: str, token: str, challenge: str, expected_token: str) -> str | None:
    if mode == "subscribe" and token == expected_token:
        return challenge
    return None
