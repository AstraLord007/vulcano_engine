"""Registro forense en JSON mediante colas y rotación comprimida atómica."""

import gzip
import json
import logging
import logging.handlers
import os
import queue
import shutil
import tempfile
import traceback
from datetime import datetime, timezone


def _exception_tree(error):
    """Serializa cada excepción y los hijos de los grupos concurrentes."""
    result = {
        "type": type(error).__name__,
        "message": str(error),
        "notes": list(getattr(error, "__notes__", ())),
        "traceback": "".join(traceback.format_exception(error)),
    }
    if isinstance(error, ExceptionGroup):
        result["exceptions"] = [_exception_tree(child) for child in error.exceptions]
    return result


class AsyncJSONFormatter(logging.Formatter):
    """Captura fecha UTC, campos del proyecto y árboles de excepciones."""

    def format(self, record):
        """Convierte el registro en JSON antes de su preparación para la cola."""
        event = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "process": record.process,
            "threadName": record.threadName,
        }
        for field in (
            "TraceId", "MessageId", "WebhookId", "X-Webhook-Signature",
            "message_id", "queue_url", "receipt_handle",
        ):
            if hasattr(record, field):
                event[field] = getattr(record, field)
        if record.exc_info and record.exc_info[1] is not None:
            event["exception"] = _exception_tree(record.exc_info[1])
        if record.stack_info:
            event["stack_info"] = record.stack_info
        return json.dumps(event, ensure_ascii=False, default=str)


def gzip_namer(default_name):
    """Conserva los sufijos numerados para permitir la retención de respaldos."""
    return default_name + ".gz"


def gzip_rotator(source, dest):
    """Publica el gzip completo de forma atómica y luego elimina el original."""
    directory = os.path.dirname(os.path.abspath(dest))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=directory, prefix=".vulcano-", suffix=".tmp", delete=False,
        ) as output:
            temporary = output.name
            with open(source, "rb") as input_stream:
                with gzip.GzipFile(fileobj=output, mode="wb") as compressed:
                    shutil.copyfileobj(input_stream, compressed)
        os.replace(temporary, dest)
        temporary = None
        os.remove(source)
    finally:
        if temporary is not None:
            os.unlink(temporary)


def shutdown_vulcano_logging():
    """Vacía la cola y cierra recursos; invocar en finally tras parar productores."""
    logger = logging.getLogger("vulcano_engine")
    listener = getattr(logger, "listener", None)
    if listener is None:
        return
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    listener.stop()
    for target in listener.handlers:
        target.close()
    logger.listener = None


def setup_vulcano_logging(log_filename="vulcano_events.log"):
    """Configura una vez el logger del proyecto, sin otros manejadores adjuntos.

    El productor genera JSON antes de que QueueHandler.prepare retire la
    excepción. Solo el listener escribe en disco; el cierre es explícito.
    """
    logger = logging.getLogger("vulcano_engine")
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=2 * 1024 * 1024, backupCount=3,
        encoding="utf-8", delay=True,
    )
    file_handler.namer = gzip_namer
    file_handler.rotator = gzip_rotator
    queue_handler = logging.handlers.QueueHandler(queue.Queue())
    queue_handler.setFormatter(AsyncJSONFormatter())
    listener = logging.handlers.QueueListener(queue_handler.queue, file_handler)
    listener.start()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.listener = listener
    logger.addHandler(queue_handler)
    return logger
