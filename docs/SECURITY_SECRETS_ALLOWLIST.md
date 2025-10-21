# Secrets Baseline & Allowlist

## Status

- Nenhum segredo detectado atualmente no baseline (`.secrets.baseline`).
- Todos os falsos positivos já estão filtrados pelos plugins e filtros configurados.
- Última geração: 2025-10-20

## Plugins Ativos

- Artifactory, AWS, Azure, Base64, BasicAuth, Cloudant, Discord, GitHub, Hex, IBM, JWT, Keyword, Mailchimp, Npm, PrivateKey, SendGrid, Slack, Softlayer, Square, Stripe, Twilio

## Filtros Ativos

- Allowlist, policies, heuristics, lock files, UUID, Swagger, templated secrets, etc.

## Como marcar falsos positivos

- Se algum segredo for detectado e for falso positivo, adicione ao allowlist usando o comando:

```bash
detect-secrets allowlist --baseline .secrets.baseline --add <linha>
```

## Referência

- Documentação oficial: <https://github.com/Yelp/detect-secrets>

---

**ENGLISH**

- No secrets currently detected in baseline (`.secrets.baseline`).
- All false positives are already filtered by plugins and filters.
- Last generated: 2025-10-20

**How to allowlist false positives:**

- If a secret is detected and is a false positive, add to allowlist:

```bash
detect-secrets allowlist --baseline .secrets.baseline --add <line>
```

---

Arquivo `.secrets.baseline` validado e documentado.
