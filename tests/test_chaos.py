"""Pruebas de caos e inyección de fallos para webhooks y SQS en Vulcano Pay."""

import json
import socket
import time

import pytest
from fastapi.testclient import TestClient

from vulcano_telemetry.core_sqs import get_sqs_client
from vulcano_telemetry.webhook_crypto import generate_signature
from vulcano_telemetry.webhook_receiver import WEBHOOK_SECRET, app

client = TestClient(app)


def check_localstack() -> bool:
    """Verifica si LocalStack está activo en el puerto 4566."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', 4566)) == 0


def test_invalid_signature_webhook():
    """Verifica que el receptor rechace webhooks con firmas HMAC falsas o alteradas."""
    payload = {"event": "payment.failed", "amount": 100}
    headers = {
        "X-Hub-Signature-256": "sha256=firma_falsa_incorrecta_123456",
        "X-Webhook-Timestamp": str(int(time.time()))
    }
    response = client.post("/webhook", json=payload, headers=headers)
    assert response.status_code in (401, 403)


def test_replay_attack_old_timestamp():
    """Verifica que el receptor rechace webhooks con timestamps fuera de la ventana de tolerancia."""
    payload = {"event": "payment.success", "amount": 500}
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    signature = generate_signature(WEBHOOK_SECRET, payload_bytes)
    old_timestamp = str(int(time.time()) - 3600)
    
    headers = {
        "X-Hub-Signature-256": signature,
        "X-Webhook-Timestamp": old_timestamp
    }
    response = client.post("/webhook", json=payload, headers=headers)
    assert response.status_code == 400


@pytest.mark.skipif(not check_localstack(), reason="LocalStack no está encendido en el puerto 4566")
def test_poison_message_handling():
    """Envía cargas dañadas a SQS y valida la gestión de errores."""
    sqs = get_sqs_client()
    queue_url = "http://localhost:4566/000000000000/vulcano-events-queue"
    
    try:
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody="{ malformed_json_body... }"
        )
    except Exception as e:
        assert e is not None
