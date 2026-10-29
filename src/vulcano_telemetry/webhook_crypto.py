"""Utilidades criptográficas para la firma y verificación de Webhooks con HMAC-SHA256."""

import hmac
import hashlib

def generate_signature(secret: str, payload: bytes, *args, **kwargs) -> str:
    """Genera una firma HMAC-SHA256 en hexadecimal para el cuerpo del mensaje."""
    if isinstance(secret, str):
        secret_bytes = secret.encode("utf-8")
    else:
        secret_bytes = secret
        
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    signature = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def verify_signature(secret: str, payload: bytes, signature_header: str) -> bool:
    """Compara de forma segura (constant-time) la firma recibida con la calculada localmente."""
    if not signature_header:
        return False
    
    expected_signature = generate_signature(secret, payload)
    return hmac.compare_digest(expected_signature, signature_header)
