# Architecture Decision Records (ADRs)

Este diretório contém os registros de decisões arquiteturais importantes do sistema MT5 Trading System.

## O que é um ADR?

Um Architecture Decision Record (ADR) documenta uma decisão significativa relacionada à arquitetura de software, incluindo:

- **Contexto**: Por que a decisão foi necessária
- **Decisão**: O que foi decidido
- **Consequências**: Impactos positivos e negativos da decisão
- **Alternativas**: Outras opções consideradas

## Status dos ADRs

- ✅ **Aceito**: Decisão implementada e em uso
- 🔄 **Em Progresso**: Decisão aprovada mas ainda não implementada
- ❌ **Rejeitado**: Decisão não aprovada
- ⚠️ **Depreciado**: Decisão substituída por outra

## Lista de ADRs

| #   | Título | Status | Data |
|-----|--------|--------|------|
| 001 | [Uso de TimescaleDB para Dados de Trading](./001-timescaledb.md) | ✅ Aceito | 2025-01-15 |
| 002 | [Arquitetura de Microserviços com Docker Compose](./002-docker-compose.md) | ✅ Aceito | 2025-01-20 |
| 003 | [FastAPI como Framework Web](./003-fastapi.md) | ✅ Aceito | 2025-01-25 |
| 004 | [Prometheus + Grafana para Observabilidade](./004-observability-stack.md) | ✅ Aceito | 2025-02-01 |
| 005 | [Random Forest como Modelo ML Base](./005-random-forest.md) | ✅ Aceito | 2025-02-10 |
| 006 | [PgBouncer para Connection Pooling](./006-pgbouncer.md) | ✅ Aceito | 2025-02-15 |
| 007 | [Loki para Centralized Logging](./007-loki-logging.md) | ✅ Aceito | 2025-03-01 |
| 008 | [Systemd Timers para Automação](./008-systemd-timers.md) | ✅ Aceito | 2025-03-10 |

## Template para Novos ADRs

Use o template abaixo ao criar novos ADRs:

```markdown
# ADR-XXX: [Título da Decisão]

**Status**: [Proposto | Aceito | Rejeitado | Depreciado]
**Data**: YYYY-MM-DD
**Autor**: [Nome]
**Decisores**: [Lista de pessoas envolvidas]

## Contexto

[Descreva o problema ou situação que motivou esta decisão]

## Decisão

[Descreva a decisão tomada]

## Alternativas Consideradas

### Alternativa 1: [Nome]
- **Prós**: ...
- **Contras**: ...

### Alternativa 2: [Nome]
- **Prós**: ...
- **Contras**: ...

## Consequências

### Positivas
- ...

### Negativas
- ...

### Riscos
- ...

## Detalhes de Implementação

[Informações técnicas sobre como implementar esta decisão]

## Referências

- [Links relevantes]
```

## Como Contribuir

1. Crie um novo arquivo ADR usando o template
2. Numere sequencialmente (ex: `009-nome-descritivo.md`)
3. Adicione à tabela acima
4. Submeta via pull request para revisão
