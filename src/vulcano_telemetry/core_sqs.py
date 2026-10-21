"""Cliente Boto3 y operaciones de mensajería SQS con soporte para LocalStack."""

import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

from .exceptions import CorruptedMessageError, SQSConnectionError

logger = logging.getLogger("vulcano_engine")


def get_sqs_client(endpoint_url: str | None = None, region_name: str = "us-east-1"):
    """Crea una instancia del cliente Boto3 SQS configurada para LocalStack o AWS."""
    url = endpoint_url or os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    aws_region = os.getenv("AWS_DEFAULT_REGION", region_name)

    return boto3.client(
        "sqs",
        endpoint_url=url,
        region_name=aws_region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def produce_event(sqs_client, queue_url: str, event_data: dict) -> str:
    """Publica un evento estructurado en la cola de SQS usando Boto3."""
    try:
        payload = json.dumps(event_data)
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=payload,
            MessageAttributes={
                "Source": {
                    "DataType": "String",
                    "StringValue": "VulcanoWebhookEngine",
                }
            },
        )
        msg_id = response.get("MessageId", "N/A")
        logger.info(
            f"Evento publicado en SQS. MessageId: {msg_id}",
            extra={"message_id": msg_id, "queue_url": queue_url},
        )
        return msg_id
    except ClientError as err:
        sqs_err = SQSConnectionError("Error al enviar mensaje a AWS SQS LocalStack.")
        sqs_err.add_note(f"QueueUrl: {queue_url}")
        raise sqs_err from err


def consume_events(
    sqs_client,
    queue_url: str,
    wait_time: int = 10,
    max_messages: int = 5,
) -> list[dict]:
    """Consume mensajes de SQS aplicando Long Polling y validación de payload."""
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            MessageAttributeNames=["All"],
        )
        messages = response.get("Messages", [])
        processed = []

        for msg in messages:
            msg_id = msg.get("MessageId", "UNKNOWN")
            raw_body = msg.get("Body")

            if not raw_body:
                corrupt_err = CorruptedMessageError(
                    f"Mensaje SQS vacío/corrupto ID {msg_id}"
                )
                corrupt_err.add_note(f"MessageId: {msg_id}")
                raise corrupt_err

            try:
                body = json.loads(raw_body)
                processed.append(
                    {
                        "receipt_handle": msg["ReceiptHandle"],
                        "message_id": msg_id,
                        "body": body,
                        "attributes": msg.get("MessageAttributes", {}),
                    }
                )
            except json.JSONDecodeError as err:
                corrupt_err = CorruptedMessageError(
                    f"Mensaje SQS con JSON inválido ID {msg_id}"
                )
                corrupt_err.add_note(f"RawBody: {raw_body}")
                raise corrupt_err from err

        return processed
    except ClientError as err:
        sqs_err = SQSConnectionError("Error en recepción de mensajes SQS.")
        sqs_err.add_note(f"QueueUrl: {queue_url}")
        raise sqs_err from err


def delete_event(sqs_client, queue_url: str, receipt_handle: str) -> bool:
    """Elimina explícitamente un mensaje procesado de la cola SQS usando su ReceiptHandle."""
    try:
        sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        logger.info(
            "Mensaje eliminado de SQS con éxito.",
            extra={"receipt_handle": receipt_handle},
        )
        return True
    except ClientError as err:
        logger.error(f"Error al eliminar mensaje de SQS: {err}")
        sqs_err = SQSConnectionError("No se pudo eliminar el mensaje procesado de SQS.")
        sqs_err.add_note(f"ReceiptHandle: {receipt_handle}")
        raise sqs_err from err
