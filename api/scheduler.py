# api/app/services/scheduler.py
from __future__ import annotations

import logging
from threading import Event, Thread
from time import sleep

log = logging.getLogger(__name__)


class DummyScheduler:
    """Scheduler simples para placeholders. Substitua por APScheduler se quiser."""
    def __init__(self) -> None:
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("Scheduler iniciado.")

    def _loop(self) -> None:
        while not self._stop.is_set():
            # coloque aqui tarefas periódicas (ex: métricas, limpeza, etc.)
            sleep(60)

    def shutdown(self) -> None:
        self._stop.set()
        log.info("Scheduler finalizado.")


scheduler = DummyScheduler()
