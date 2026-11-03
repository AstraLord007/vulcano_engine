"""Excepciones personalizadas para el motor de telemetría y pagos de Vulcano."""

class VulcanoError(Exception):
    """Excepción base para todos los errores del ecosistema Vulcano."""

VulcanoEngineError = VulcanoError


class SQSConnectionError(VulcanoError):
    """Se lanza cuando ocurre un fallo al conectar o interactuar con AWS SQS / LocalStack."""


class QueueTimeoutError(VulcanoError):
    """Lanzada cuando expira el tiempo de espera de la cola SQS."""


class CorruptedMessageError(VulcanoError):
    """Se lanza cuando un mensaje recibido de SQS está vacío, malformado o no es un JSON válido."""


class WebhookSignatureError(VulcanoError):
    """Lanzada cuando la firma criptográfica HMAC-SHA256 es inválida o ausente."""


class WebhookTimestampError(VulcanoError):
    """Lanzada cuando el timestamp del Webhook está fuera de la ventana de tolerancia (Replay Attack)."""


class WebhookDeliveryError(VulcanoError):
    """Lanzada cuando el envío HTTP del Webhook falla tras los reintentos."""
