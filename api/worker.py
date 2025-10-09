import os
import asyncio
import orjson
import time
import pathlib
from typing import Dict, Any, List
from .db import insert_batch

BATCH_MAX = int(os.getenv("BATCH_MAX", "1000"))
BATCH_MAX_DELAY_MS = int(os.getenv("BATCH_MAX_DELAY_MS", "150"))
WAL_DIR = pathlib.Path(os.getenv("WAL_DIR", "/wal"))
WAL_DIR.mkdir(parents=True, exist_ok=True)

# Fila em memória
_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

# Contador simples de falhas de DB (telemetria mínima)
_db_fail = 0


def wal_append(records: List[Dict[str, Any]]) -> None:
    """Grava os registros em JSONL (write-ahead) para não perder dados."""
    if not records:
        return
    fname = WAL_DIR / f"ingest_{int(time.time() * 1000)}.jsonl"
    with fname.open("ab") as f:
        for r in records:
            f.write(orjson.dumps(r))
            f.write(b"\n")


async def enqueue(item: Dict[str, Any]) -> None:
    """Enfileira um item validado pelo endpoint /ingest."""
    await _queue.put(item)


async def _flush_batch(batch: List[Dict[str, Any]]) -> None:
    """Persiste no WAL e tenta inserir em batch no Postgres (UPSERT)."""
    global _db_fail
    if not batch:
        return

    # 1) Persistência primeiro (WAL)
    wal_append(batch)

    # 2) Tentativa de inserir no DB
    try:
        await insert_batch(batch)
        _db_fail = 0
        # print(f"[WAL][DB][OK] flushed={len(batch)}")
    except Exception as e:
        _db_fail += 1
        # Mantém os dados no WAL para reprocessar depois
        print(f"[WAL][DB][ERROR] fails={_db_fail} err={e}")


async def consumer_loop() -> None:
    """
    Consumidor que agrega itens em lote e faz flush por tamanho (BATCH_MAX)
    ou por tempo (BATCH_MAX_DELAY_MS).
    """
    batch: List[Dict[str, Any]] = []
    deadline = time.monotonic() + (BATCH_MAX_DELAY_MS / 1000.0)

    while True:
        timeout = max(0.0, deadline - time.monotonic())
        try:
            item = await asyncio.wait_for(_queue.get(), timeout=timeout)
            batch.append(item)

            # Flush por tamanho
            if len(batch) >= BATCH_MAX:
                await _flush_batch(batch)
                batch.clear()
                deadline = time.monotonic() + (BATCH_MAX_DELAY_MS / 1000.0)

        except asyncio.TimeoutError:
            # Flush por tempo
            if batch:
                await _flush_batch(batch)
                batch.clear()
            deadline = time.monotonic() + (BATCH_MAX_DELAY_MS / 1000.0)
