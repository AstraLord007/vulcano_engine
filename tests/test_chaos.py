import time
import pytest
from fastapi.testclient import TestClient
from vulcano_telemetry.webhook_receiver import app, WEBHOOK_SECRET
from vulcano_telemetry.webhook_crypto import generate_signature, verify_signature
from vulcano_telemetry.exceptions import WebhookTimestampError, CorruptedMessageError
from vulcano_telemetry.core_sqs import get_sqs_client, consume_events
from botocore.exceptions import ClientError

client = TestClient(app)


def test_invalid_signature_webhook():
    """Simula webhook con firma alterada o clave incorrecta -> HTTP 401 Unauthorized."""
    payload = b'{"transaction_id": "tx_chaos_01", "amount": 500.0}'
    timestamp = int(time.time())
    wrong_sig = generate_signature("clave_falsa_invalida_9999", timestamp, payload)
    header_val = f"t={timestamp},v1={wrong_sig}"

    response = client.post(
        "/webhook",
        data=payload,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": header_val}
    )
    assert response.status_code == 401
    assert "Firma" in response.json().get("detail", "") or "signature" in response.json().get("detail", "").lower()


def test_replay_attack_old_timestamp():
    """Simula webhook con timestamp de hace 1 hora (fuera de tolerancia) -> WebhookTimestampError."""
    payload = b'{"transaction_id": "tx_chaos_02", "amount": 150.0}'
    old_timestamp = int(time.time()) - 3600  # -1 hora
    signature = generate_signature(WEBHOOK_SECRET, old_timestamp, payload)
    header_val = f"t={old_timestamp},v1={signature}"

    with pytest.raises(WebhookTimestampError):
        verify_signature(WEBHOOK_SECRET, header_val, payload, tolerance_sec=300)


def test_poison_message_handling():
    """Envía cargas dañadas (poison messages) a SQS y valida la excepción CorruptedMessageError."""
    sqs = get_sqs_client()
    queue_url = "http://localhost:4566/000000000000/vulcano-events-queue"
    
    try:
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody="{ malformed_json_body... }"
        )
        with pytest.raises(CorruptedMessageError):
            consume_events(sqs, queue_url, wait_time=1, max_messages=1)
    except ClientError:
        pytest.skip("LocalStack SQS no se encuentra activo en este entorno de prueba unitaria.")
