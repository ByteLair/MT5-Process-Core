# LOG DE ALTERAÇÕES NAS CAMADAS DE IA

## 2025-10-17

### 1. Padronização do nome do modelo
- Alterado `ml/train_model.py` para salvar o modelo como `rf_m1.pkl`.
- Compatível com o scheduler (`ml/scheduler.py`).

### 2. Pipeline automatizado de ML
- Criado script `ml/pipeline_train.sh`.
- Pipeline executa: preparação de dataset → treino de modelo → validação de thresholds.
- Todos os logs da pipeline são salvos em `logs/pipeline_train.log`.

### 3. Padronização de commit e versionamento
- Criado script `scripts/commit_version.sh` para commits padronizados e versionamento semântico (v0.1, v0.2, ...).
- O script incrementa versão, faz commit e cria tag automaticamente.

### 4. Automação de log diário da IA
- Criado script `scripts/log_diario_ia.sh` para registrar diariamente erros e ações da IA.
- Log é salvo em `logs/log_diario_ia_YYYY-MM-DD.log`.
- Inclui erros do pipeline, últimas ações, logs do scheduler e sinais gerados.

### 5. Documentação das alterações
- Todas as mudanças estão registradas neste arquivo.
- Scripts possuem comentários explicativos e podem ser agendados via cron ou systemd timer.

---

**Próximos passos sugeridos:**
- Agendar execução diária do log via cron ou systemd.
- Usar o script de commit para todos os commits futuros.
- Validar logs para garantir rastreabilidade das ações da IA.
