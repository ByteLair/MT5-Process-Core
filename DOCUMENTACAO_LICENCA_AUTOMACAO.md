# Registro de Automação de Licença e Copyright

**Data:** 20/10/2025
**Responsável:** Felipe Petracco Carmo <kuramopr@gmail.com>

---

## Objetivo

Garantir que todos os arquivos do repositório estejam protegidos por um header de copyright/licença privada, de forma padronizada e automatizada, reforçando a propriedade intelectual e as restrições de uso do código.

---

## Etapas Realizadas

### 1. Criação do Header Bilingue

- Desenvolvido um texto de copyright/licença privada em português e inglês.
- Dados incluídos:
  - Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
  - Todos os direitos reservados / All rights reserved
  - Licença privada: proibida redistribuição, cópia, modificação ou uso comercial sem autorização expressa

### 2. Inclusão Manual nos Principais Arquivos

- Header adicionado manualmente nos principais arquivos Python do projeto:
  - `api/app/ingest.py`
  - `api/app/main.py`
  - `api/app/tick_aggregator.py`
  - `api/app/indicators_worker.py`

### 3. Automação via Pre-commit

- Criado o script `scripts/add_header.py` para inserir o header automaticamente.
- Tipos de arquivos suportados:
  - Python (.py)
  - Shell script (.sh)
  - Dockerfile
  - YAML (.yml, .yaml)
  - Markdown (.md)
  - SQL (.sql)
  - Jupyter Notebook (.ipynb)
  - Configuração (.ini, .toml, .env, .conf)
- Atualizado `.pre-commit-config.yaml` para rodar o script antes de cada commit.
- Para notebooks, é necessário instalar o pacote `nbformat`.
- Para ativar a automação:

  ```bash
  pip install pre-commit nbformat
  pre-commit install
  ```

### 4. Commit das Alterações

- Todos os arquivos modificados e a automação foram commitados e enviados ao repositório.
- Mensagem de commit utilizada:

  ```
  Automação: header de copyright/licença privada inserido em todos os tipos de arquivos via pre-commit
  ```

### 5. Garantia de Padronização

- Todo arquivo novo ou modificado dos tipos suportados receberá o header automaticamente antes do commit.
- Proteção legal, padronização e rastreabilidade garantidas em todo o código do projeto.

---

## Como funciona

- Ao tentar commitar qualquer arquivo dos tipos suportados, o pre-commit executa o script e insere o header no topo do arquivo, caso ainda não exista.
- O header contém todas as informações de copyright e restrição de uso, em português e inglês.
- Isso protege o código contra uso indevido e reforça a autoria do projeto.

---

## Observações

- O processo é transparente e automático para o desenvolvedor.
- Caso novos tipos de arquivos sejam adicionados ao projeto, o script pode ser facilmente adaptado.
- Recomenda-se manter o pre-commit ativado em todos os clones do repositório.

---

**Este documento serve como registro oficial das ações de proteção de propriedade intelectual realizadas no projeto.**
