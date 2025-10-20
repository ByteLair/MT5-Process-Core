# docs/logging.md

- Enable Uvicorn access logs: `--log-level info`.
- Log format JSON (example with `uvicorn --access-log` + structured handlers).
- Emit counters: add a simple `/metrics` or expose counts in logs (requests, ingested rows).
