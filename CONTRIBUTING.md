# Contributing to MT5 Trading System

Obrigado pelo interesse em contribuir! 🎉

## Como Contribuir

### Reportar Bugs

Use GitHub Issues com o template de bug report. Inclua:
- Descrição clara do problema
- Passos para reproduzir
- Comportamento esperado vs atual
- Environment (OS, Docker version, Python version)
- Logs relevantes

### Sugerir Features

Abra uma Issue com o template de feature request explicando:
- Problema que a feature resolve
- Proposta de solução
- Alternativas consideradas
- Impacto esperado

### Submeter Pull Requests

1. **Fork** o repositório
2. **Clone** seu fork:
   ```bash
   git clone https://github.com/your-username/mt5-trading-db.git
   cd mt5-trading-db
   ```

3. **Crie uma branch** para sua feature/fix:
   ```bash
   git checkout -b feature/my-feature
   # ou
   git checkout -b fix/bug-description
   ```

4. **Configure o ambiente**:
   ```bash
   # Instalar pre-commit hooks
   pip install pre-commit
   pre-commit install
   
   # Subir stack local
   docker compose up -d
   ```

5. **Faça suas mudanças** seguindo as guidelines:
   - Código Python deve passar por ruff, black, isort e mypy
   - Adicione testes para novas features
   - Atualize documentação relevante
   - Commits devem ser claros e descritivos

6. **Rode os checks localmente**:
   ```bash
   # Formatação
   make format
   
   # Lint
   make lint
   
   # Type check
   make typecheck
   
   # Testes
   pytest api/tests
   pytest ml/tests
   pytest scripts/tests
   ```

7. **Pre-commit hooks**: Rodam automaticamente no commit
   ```bash
   git add .
   git commit -m "feat: add awesome feature"
   ```

8. **Push** para seu fork:
   ```bash
   git push origin feature/my-feature
   ```

9. **Abra um Pull Request**:
   - Use o template de PR
   - Descreva as mudanças claramente
   - Referencie issues relacionadas (#123)
   - Aguarde review

## Style Guide

### Python

- **Formatação**: Black (line-length 88), isort (profile black)
- **Linting**: Ruff com regras E, F, I, W, UP, C90, N
- **Type Hints**: Tipagem estrita com mypy em `api/` e `ml/`
- **Naming**: PEP 8 (snake_case para funções/variáveis, PascalCase para classes)

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: Nova feature
- `fix`: Bug fix
- `docs`: Apenas documentação
- `style`: Formatação, sem mudanças de código
- `refactor`: Refatoração sem mudar comportamento
- `perf`: Melhoria de performance
- `test`: Adicionar/corrigir testes
- `chore`: Manutenção, deps, config

**Exemplos:**
```
feat(api): add endpoint for bulk signal retrieval
fix(ml): correct feature calculation for RSI
docs(readme): update installation instructions
```

### Testes

- **Coverage mínima**: 70% para novos módulos
- **Teste unitário**: Para lógica de negócio isolada
- **Teste de integração**: Para fluxos completos (ingest → DB → signal)
- **Mocks**: Use mocks para dependências externas (DB em unit tests)

Exemplo de teste:
```python
def test_signal_generation():
    """Test signal generation from market data."""
    # Arrange
    data = create_test_candles()
    
    # Act
    signal = generate_signal(data)
    
    # Assert
    assert signal.side in ["BUY", "SELL", "FLAT"]
    assert 0.0 <= signal.confidence <= 1.0
```

### Documentação

- **Docstrings**: Google style para funções/classes públicas
- **README**: Atualizar se adicionar features/endpoints
- **CHANGELOG**: Adicionar entry para breaking changes
- **ADRs**: Documentar decisões arquiteturais importantes em `docs/adr/`

## Code Review Process

1. **Automated checks**: CI deve passar (lint, typecheck, tests)
2. **Review**: Pelo menos 1 aprovação de maintainer
3. **Feedback**: Endereçar comentários e re-push
4. **Merge**: Squash & merge para manter histórico limpo

## Prioridades Atuais

Veja [GitHub Projects](https://github.com/Lysk-dot/mt5-trading-db/projects) e Issues com labels:
- `good first issue`: Ideal para novos contribuidores
- `help wanted`: Precisamos de ajuda
- `priority: high`: Urgente

## Código de Conduta

Seguimos o [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). Comportamento inadequado pode ser reportado para kuramopr@gmail.com.

## Dúvidas?

- 📚 Documentação completa: `docs/DOCUMENTATION.md`
- 🆕 Novo no projeto: `docs/ONBOARDING.md`
- ❓ FAQ: `docs/FAQ.md`
- 💬 Discussões: GitHub Discussions
- 📧 Email: kuramopr@gmail.com

---

**Obrigado por contribuir!** 🚀
