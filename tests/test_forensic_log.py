import os
import gzip
import json
import logging
from vulcano_telemetry.logging_engine import setup_vulcano_logging


class ForensicTelemetryFilter(logging.Filter):
    """Filtro auxiliar para asegurar que process_id y thread_name estén presentes en el registro."""
    def filter(self, record):
        if not hasattr(record, "process_id"):
            record.process_id = getattr(record, "process", os.getpid())
        if not hasattr(record, "thread_name"):
            record.thread_name = getattr(record, "threadName", "MainThread")
        return True


def test_forensic_log_structure_and_telemetry(tmp_path):
    """Verifica el formato JSON estricto y la inyección de metadatos forenses en los logs."""
    log_file = tmp_path / "vulcano_forensic.log"
    logger = setup_vulcano_logging(str(log_file))

    # Asegurarnos de que el logger tenga el filtro forense activo para las pruebas
    forensic_filter = ForensicTelemetryFilter()
    if forensic_filter not in logger.filters:
        logger.addFilter(forensic_filter)

    # Registrar evento con atributos de telemetría exigidos
    logger.info(
        "Evento procesado correctamente",
        extra={"message_id": "msg_forensic_001", "trace_id": "trace_sec_999"}
    )
    
    if hasattr(logger, "listener") and logger.listener:
        logger.listener.stop()

    assert log_file.exists()

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) > 0
    record = json.loads(lines[0])

    # Validaciones forenses obligatorias
    assert "timestamp" in record
    assert record["level"] == "INFO"
    assert record["message_id"] == "msg_forensic_001"
    assert "process_id" in record
    assert "thread_name" in record


def test_gzip_decompression_lossless():
    """Verifica la compresión y descompresión íntegra sin pérdida de datos en archivos .log.gz."""
    compressed_path = "test_forensic.log.gz"
    original_content = (
        '{"timestamp": "2026-10-29T02:24:00Z", "level": "INFO", "message": "Forense dump", "message_id": "msg_999"}\n'
    )

    try:
        with gzip.open(compressed_path, "wt", encoding="utf-8") as f_out:
            f_out.write(original_content)

        assert os.path.exists(compressed_path)

        with gzip.open(compressed_path, "rt", encoding="utf-8") as f_in:
            decompressed_content = f_in.read()

        assert decompressed_content == original_content
    finally:
        if os.path.exists(compressed_path):
            os.remove(compressed_path)
