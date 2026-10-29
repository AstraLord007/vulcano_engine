import argparse
import time
import json
import requests
import uvicorn
from vulcano_telemetry.sanitizer import (
    parse_queue_name,
    parse_wait_time,
    parse_webhook_url,
    parse_secret_key,
)
from vulcano_telemetry.core_sqs import get_sqs_client, produce_event, consume_events
from vulcano_telemetry.webhook_crypto import generate_signature
from vulcano_telemetry.logging_engine import setup_vulcano_logging
from vulcano_telemetry.exceptions import (
    SQSConnectionError,
    WebhookSignatureError,
    WebhookTimestampError,
    WebhookDeliveryError,
)

logger = setup_vulcano_logging()


def dispatch_webhook(target_url: str, secret: str, payload_dict: dict) -> None:
    """Firma el payload JSON y realiza el envío HTTP POST inyectando la cabecera X-Webhook-Signature."""
    try:
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        timestamp = int(time.time())
        signature = generate_signature(secret, timestamp, payload_bytes)
        header_val = f"t={timestamp},v1={signature}"

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": header_val,
        }
        response = requests.post(target_url, data=payload_bytes, headers=headers, timeout=5)
        
        if response.status_code not in (200, 202):
            raise WebhookDeliveryError(
                f"Fallo en entrega de webhook a {target_url}. Código HTTP: {response.status_code}"
            )
        
        logger.info(
            f"Webhook despachado exitosamente a {target_url}. Status: {response.status_code}",
            extra={"target_url": target_url}
        )
    except requests.RequestException as err:
        delivery_err = WebhookDeliveryError(f"Error de red al despachar webhook hacia {target_url}")
        delivery_err.add_note(str(err))
        raise delivery_err from err


def build_parser() -> argparse.ArgumentParser:
    """Configura el CLI con subcomandos y validadores sanitizadores."""
    parser = argparse.ArgumentParser(
        prog="VulcanoCLI", description="Motor de Eventos SQS y Webhooks HMAC para Vulcano Pay"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Subcomandos operativos")

    # Subcomando: produce-sqs
    p_produce = subparsers.add_parser("produce-sqs", help="Publica evento directamente a SQS LocalStack")
    p_produce.add_argument("-q", "--queue", type=parse_queue_name, default="vulcano-events-queue")
    p_produce.add_argument("--payload", type=str, default='{"event": "payment.completed", "amount": 150.0}', help="Carga útil en JSON")

    # Subcomando: start-receiver
    p_recv = subparsers.add_parser("start-receiver", help="Inicia el servidor receptor de Webhooks HTTP local")
    p_recv.add_argument("--host", type=str, default="127.0.0.1")
    p_recv.add_argument("--port", type=int, default=8000)

    # Subcomando: start-dispatcher
    p_disp = subparsers.add_parser("start-dispatcher", help="Ejecuta el consumidor SQS que despacha webhooks")
    p_disp.add_argument("-q", "--queue", type=parse_queue_name, default="vulcano-events-queue")
    p_disp.add_argument("-w", "--wait-time", type=parse_wait_time, default=10)
    p_disp.add_argument("--url", type=parse_webhook_url, default="http://localhost:8000/webhook")
    p_disp.add_argument("--secret", type=parse_secret_key, default="mi_clave_secreta_super_segura_vulcano_123")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    logger.info(f"Iniciando VulcanoCLI en subcomando '{args.mode}'")

    try:
        if args.mode == "produce-sqs":
            sqs = get_sqs_client()
            queue_url = f"http://localhost:4566/000000000000/{args.queue}"
            try:
                payload_dict = json.loads(args.payload)
            except json.JSONDecodeError:
                payload_dict = {"raw_payload": args.payload}
            msg_id = produce_event(sqs, queue_url, payload_dict)
            logger.info(f"Evento publicado con éxito en SQS. ID: {msg_id}")

        elif args.mode == "start-receiver":
            logger.info(f"Iniciando servidor FastAPI en {args.host}:{args.port}...")
            uvicorn.run("vulcano_telemetry.webhook_receiver:app", host=args.host, port=args.port, reload=False)

        elif args.mode == "start-dispatcher":
            sqs = get_sqs_client()
            queue_url = f"http://localhost:4566/000000000000/{args.queue}"
            logger.info("Iniciando despachador SQS -> Webhooks...")
            events = consume_events(sqs, queue_url, wait_time=args.wait_time)
            for ev in events:
                dispatch_webhook(args.url, args.secret, ev["body"])
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=ev["receipt_handle"])
                logger.info(f"Mensaje SQS procesado y eliminado: {ev['message_id']}")

    except* WebhookSignatureError as group:
        logger.error(f"Errores de firma HMAC en Webhooks ({len(group.exceptions)}):")
        for exc in group.exceptions:
            logger.error(f"  • {exc}")
    except* WebhookTimestampError as group:
        logger.error(f"Errores de timestamp/replay ({len(group.exceptions)}):")
        for exc in group.exceptions:
            logger.error(f"  • {exc}")
    except* SQSConnectionError as group:
        logger.error(f"Errores de comunicación con SQS LocalStack ({len(group.exceptions)}):")
        for exc in group.exceptions:
            logger.error(f"  • {exc}")
    finally:
        # Cumplimiento PEP 765: Apagado ordenado sin return, break o continue
        logger.info("Liberando recursos de observabilidad (QueueListener)...")
        if hasattr(logger, "listener") and logger.listener:
            logger.listener.stop()


if __name__ == "__main__":
    main()
