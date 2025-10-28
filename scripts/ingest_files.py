#!/usr/bin/env python3
"""
scripts/ingest_files.py

Leia todos os arquivos .jsonl em uma pasta (por padrão `Files/`) e envie-os em batches
para o endpoint `/ingest` da API local. Escreve um arquivo de status por cada arquivo lido.

Uso:
  python3 scripts/ingest_files.py --dir Files --chunk 500 --url http://localhost:18003 --api-key mt5_a8f5c3e1-4d2b-4a9e-8c7f-1b3e5d7a9c2f

O script tenta usar `requests` se disponível, caso contrário usa urllib padrão.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


DEFAULT_API_KEY = os.getenv(
    "API_KEY", "mt5_a8f5c3e1-4d2b-4a9e-8c7f-1b3e5d7a9c2f"
)
DEFAULT_URL = os.getenv("INGEST_URL", "http://localhost:18003")


def chunks(it: Iterable[Any], size: int) -> Iterable[List[Any]]:
    buf: List[Any] = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def post_json(url: str, path: str, payload: Dict[str, Any], headers: Dict[str, str]):
    """Posta JSON para URL. Tenta usar requests, senão urllib."""
    try:
        import requests

        r = requests.post(url, json=payload, headers=headers, timeout=60)
        return r.status_code, r.text
    except Exception:
        # fallback para urllib
        try:
            from urllib import request as _request
            from urllib.error import HTTPError, URLError

            req = _request.Request(path, data=json.dumps(payload).encode("utf-8"))
            for k, v in headers.items():
                req.add_header(k, v)
            req.add_header("Content-Type", "application/json")
            with _request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return resp.getcode(), body
        except Exception as e:
            return 0, f"failed to POST: {e}"


def ingest_file(file: Path, base_url: str, api_key: str, chunk_size: int = 500) -> Dict[str, Any]:
    """Lê um arquivo .jsonl e envia batches para /ingest endpoint.

    Retorna um dicionário resumo com detalhes.
    """
    url = base_url.rstrip("/") + "/ingest"
    headers = {"X-API-Key": api_key}

    inserted_total = 0
    received_total = 0
    errors: List[str] = []

    # Ler linhas JSON válidas
    with file.open("r", encoding="utf-8") as fh:
        lines = [line.strip() for line in fh if line.strip()]

    # Parse JSON lines
    items: List[Dict[str, Any]] = []
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
            # Alguns arquivos usam 'ts' como string ISO (ok para FastAPI pydantic)
            items.append(obj)
        except Exception as e:
            errors.append(f"line {i}: json parse error: {e}")

    received_total = len(items)

    # Enviar em batches
    for batch in chunks(items, chunk_size):
        payload = {"items": batch}
        status, body = post_json(url, url, payload, headers)
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw_body": body}

        if status in (200, 201):
            # tenta inferir quantos inseridos
            ins = parsed.get("inserted") if isinstance(parsed, dict) else None
            if isinstance(ins, int):
                inserted_total += ins
        else:
            errors.append(f"batch POST status={status} body={body}")

    summary = {
        "file": str(file),
        "received": received_total,
        "inserted": inserted_total,
        "errors": errors,
    }

    # escrever arquivo de status ao lado do arquivo original
    status_file = file.with_name(file.stem + "_status.txt")
    with status_file.open("w", encoding="utf-8") as sf:
        sf.write(json.dumps(summary, ensure_ascii=False, indent=2))

    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default="Files", help="Diretório contendo .jsonl (padrão: Files)")
    p.add_argument("--chunk", type=int, default=500, help="Tamanho do batch para envio (default 500)")
    p.add_argument("--url", default=DEFAULT_URL, help="URL base da API (default http://localhost:18003)")
    p.add_argument("--api-key", default=DEFAULT_API_KEY, help="X-API-Key header para autenticação")
    args = p.parse_args()

    dirp = Path(args.dir)
    if not dirp.exists() or not dirp.is_dir():
        print(f"diretório não encontrado: {dirp}")
        return 2

    files = sorted(dirp.glob("history_*_M*.jsonl"))
    if not files:
        print(f"nenhum arquivo history_*.jsonl encontrado em {dirp}")
        return 0

    print(f"Encontrados {len(files)} arquivos em {dirp}. Enviando em batches de {args.chunk} para {args.url}")

    for f in files:
        # pular arquivos temporários e status
        if f.name.endswith("__test_write__.tmp"):
            continue
        print(f"-> processando {f.name}")
        summary = ingest_file(f, args.url, args.api_key, chunk_size=args.chunk)
        print(f"   recebido={summary['received']} inseridos={summary['inserted']} errors={len(summary['errors'])}")

    print("Concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
