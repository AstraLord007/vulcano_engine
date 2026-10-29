"""Servidor FastAPI receptor de Webhooks con validación HMAC-SHA256 y control de Timestamp."""

import os
import time
from fastapi import FastAPI, Header, HTTPException, Request, status
from .webhook_crypto import verify_signature
from .exceptions import WebhookSignatureError, WebhookTimestampError

app = FastAPI(title="Vulcano Pay Webhook Receiver")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "vulcano-secret-super-segura-12345")

TOLERANCE_SECONDS = 300

@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_webhook_timestamp: str = Header(None)
):
    """Endpoint receptor de webhooks con validación de seguridad obligatoria."""
    if not x_hub_signature_256:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma de webhook ausente (X-Hub-Signature-256)"
        )
    
    if not x_webhook_timestamp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timestamp de webhook ausente (X-Webhook-Timestamp)"
        )

    try:
        incoming_time = int(x_webhook_timestamp)
        current_time = int(time.time())
        if abs(current_time - incoming_time) > TOLERANCE_SECONDS:
            raise WebhookTimestampError("Timestamp fuera de la ventana de tolerancia.")
    except (ValueError, WebhookTimestampError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timestamp inválido o fuera de rango (Replay Attack detectado)"
        )

    body_bytes = await request.body()

    is_valid = verify_signature(WEBHOOK_SECRET, body_bytes, x_hub_signature_256)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma HMAC inválida"
        )

    payload_json = await request.json()
    return {"status": "success", "message": "Webhook procesado correctamente", "data": payload_json}
