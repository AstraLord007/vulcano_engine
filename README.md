# Proyecto Vulcano Pay 🌋
Sistema de Procesamiento de Eventos, Webhooks HMAC y Observabilidad Asíncrona con Boto3 y LocalStack.

## Integrantes (Grupo: Los Chavos del 8)
- **Integrante 1**: Robustez de Entradas, Excepciones y Sanitización (`sanitizer.py`, `exceptions.py`)
- **Integrante 2**: Mensajería Asíncrona SQS con Boto3 y LocalStack (`core_sqs.py`)
- **Integrante 3**: Seguridad Criptográfica HMAC y Receptor Webhook (`webhook_crypto.py`, `webhook_receiver.py`)
- **Integrante 4**: Almacenamiento y Observabilidad JSON (`logging_engine.py`)
- **Integrante 5**: Coordinador de Integración y CLI (`app_operator.py`)
- **Integrante 6**: Simulación de Caos y Pruebas Forenses (`tests/`)

## Requisitos Previos
- Python 3.11+
- LocalStack corriendo en el puerto `4566` (`docker run --rm -it -p 4566:4566 localstack/localstack`)

## Instalación y Ejecución
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt