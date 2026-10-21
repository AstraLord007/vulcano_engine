"""Script de prueba local para validar el módulo core_sqs con LocalStack."""

from src.vulcano_telemetry.core_sqs import (
    consume_events,
    delete_event,
    get_sqs_client,
    produce_event,
)


def main():
    print("1. Conectando a LocalStack SQS...")
    client = get_sqs_client()

    print("2. Creando una cola de prueba ('vulcano-queue-dev')...")
    response = client.create_queue(QueueName="vulcano-queue-dev")
    queue_url = response["QueueUrl"]
    print(f"   -> Cola creada con éxito. URL: {queue_url}")

    print("3. Publicando un evento de prueba...")
    event_payload = {
        "payment_id": "pay_12345",
        "amount": 1500.50,
        "status": "PENDING",
    }
    msg_id = produce_event(client, queue_url, event_payload)
    print(f"   -> Evento publicado. MessageId: {msg_id}")

    print("4. Consumiendo el evento desde la cola...")
    messages = consume_events(client, queue_url, wait_time=2, max_messages=5)
    print(f"   -> Mensajes recibidos: {len(messages)}")

    for msg in messages:
        print(f"   -> Cuerpo del mensaje: {msg['body']}")
        print(f"   -> ReceiptHandle obtenido: {msg['receipt_handle'][:30]}...")

        print("5. Borrando el mensaje explícitamente de la cola...")
        delete_event(client, queue_url, msg["receipt_handle"])
        print("   -> ¡Mensaje borrado con éxito!")

    print("\n¡Prueba de integración local completada con éxito!")


if __name__ == "__main__":
    main()
