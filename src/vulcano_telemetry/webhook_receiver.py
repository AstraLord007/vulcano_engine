"""Servidor HTTP Receptor de Webhooks utilizando FastAPI y Boto3 LocalStack."""

import logging
from fastapi import FastAPI, Request, HTTPException, status
from .webhook_crypto import verify_signature
from .core_sqs import get_sqs_client, produce_event
from .exceptions import WebhookSignatureError, WebhookTimestampError

logger = logging.getLogger("vulcano_engine")
app = FastAPI(title="Vulcano Webhook Receiver", description="Servidor receptor de Webhooks con validación HMAC y SQS")

WEBHOOK_SECRET = "mi_clave_secreta_super_segura_vulcano_123"
QUEUE_URL = "http://localhost:4566/000000000000/vulcano-events-queue"
sqs_client = get_sqs_client()

@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(request: Request):
    """
    Endpoint receptor de Webhooks:
    1. Lee los bytes crudos (raw body) para asegurar la integridad criptográfica.
    2. Valida la firma HMAC y la ventana temporal del timestamp.
    3. Responde inmediatamente con HTTP 202 Accepted y encola en LocalStack SQS vía Boto3.
    """
    raw_bytes = await request.body()
    signature_header = request.headers.get("X-Webhook-Signature", "")

    try:
        # Validación obligatoria sobre los raw bytes y cabecera unificada
        verify_signature(WEBHOOK_SECRET, signature_header, raw_bytes)
    except (WebhookSignatureError, WebhookTimestampError) as err:
        logger.warning(f"Rechazado Webhook no autenticado: {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err)
        )

    try:
        payload = await request.json()
    except Exception as err:
        logger.error(f"El cuerpo de la petición no posee un formato JSON válido: {err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El payload del webhook debe ser un JSON válido."
        )

    # Encolamiento asíncrono en SQS LocalStack mediante Boto3
    msg_id = produce_event(sqs_client, QUEUE_URL, payload)
    
    logger.info(f"Webhook verificado y encolado exitosamente en SQS. MessageId: {msg_id}", extra={"message_id": msg_id})
    return {"status": "accepted", "message_id": msg_id}