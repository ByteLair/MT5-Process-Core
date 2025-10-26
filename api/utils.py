import gzip
import json

from fastapi import Request


def maybe_gzip_decode(raw: bytes, content_encoding: str | None):
    if content_encoding and "gzip" in content_encoding.lower():
        return gzip.decompress(raw)
    return raw


async def read_json_body(request: Request):
    raw = await request.body()
    raw = maybe_gzip_decode(raw, request.headers.get("Content-Encoding"))
    return json.loads(raw.decode("utf-8"))
