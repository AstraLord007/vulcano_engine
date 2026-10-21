"""Excepciones personalizadas para el motor de telemetría y pagos de Vulcano."""


class VulcanoEngineError(Exception):
    """Excepción base para todos los errores del motor Vulcano."""


class SQSConnectionError(VulcanoEngineError):
    """Se lanza cuando ocurre un fallo al conectar o interactuar con AWS SQS / LocalStack."""


class CorruptedMessageError(VulcanoEngineError):
    """Se lanza cuando un mensaje recibido de SQS está vacío, malformado o no es un JSON válido."""
