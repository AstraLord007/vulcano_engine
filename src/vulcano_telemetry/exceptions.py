"""Excepciones personalizadas para el motor de telemetría y pagos de Vulcano."""

class VulcanoError(Exception):
    """Excepción base para todos los errores del ecosistema Vulcano."""
    pass

VulcanoEngineError = VulcanoError


class SQSConnectionError(VulcanoError):
    """Se lanza cuando ocurre un fallo al conectar o interactuar con AWS SQS / LocalStack."""
    pass


class QueueTimeoutError(VulcanoError):
    """Lanzada cuando expira el tiempo de espera de la cola SQS."""
    pass


class CorruptedMessageError(VulcanoError):
    """Se lanza cuando un mensaje recibido de SQS está vacío, malformado o no es un JSON válido."""
    pass


class WebhookSignatureError(VulcanoError):
    """Lanzada cuando la firma criptográfica HMAC-SHA256 es inválida o ausente."""
    pass


class WebhookTimestampError(VulcanoError):
    """Lanzada cuando el timestamp del Webhook está fuera de la ventana de tolerancia (Replay Attack)."""
    pass


class WebhookDeliveryError(VulcanoError):
    """Lanzada cuando el envío HTTP del Webhook falla tras los reintentos."""
    pass
