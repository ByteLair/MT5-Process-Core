# MT5 Trading DB

## Calibração do Modelo e Thresholds

### Avaliação de Thresholds

O projeto inclui uma ferramenta para calibrar o threshold de predição do modelo:

```bash
# Executar avaliação de thresholds
docker-compose run --rm ml-trainer python ml/eval_threshold.py
```

O script `eval_threshold.py` irá:

1. Conectar ao banco de dados
2. Carregar dados históricos
3. Avaliar diferentes thresholds (0.40-0.80)
4. Gerar métricas de performance (precision, recall, f1)

### Configuração do PRED_THRESHOLD

Para atualizar o threshold de predição na API:

1. Edite o arquivo `docker-compose.yml`
2. Localize o serviço `api`
3. Atualize o valor de `PRED_THRESHOLD` no bloco `environment`
4. Reconstrua e reinicie a API:

```bash
docker-compose up -d --build api
```

### Compatibilidade de Versões

Para manter a compatibilidade entre os serviços:

1. Todos os serviços (api, ml-trainer) devem usar scikit-learn==1.5.2
2. Esta versão está especificada nos arquivos:
   - `api/requirements.txt`
   - `ml/requirements.txt`
3. Após qualquer alteração nas dependências, reconstrua os containers:

```bash
docker-compose build --no-cache api ml-trainer
docker-compose up -d
```

### Manutenção e Troubleshooting

#### Docker e Permissões

Se encontrar problemas de permissão:

1. Execute o script de correção de permissões:

```bash
sudo ./setup_docker_permissions.sh
```

2. Faça logout e login novamente
3. Reinicie o VS Code se necessário

Para limpar containers antigos:

```bash
docker-compose down --remove-orphans
docker system prune -f
```

#### Manutenção do Banco de Dados

O sistema inclui rotinas automatizadas de manutenção do banco de dados:

1. **Tarefas Diárias (3:00 AM)**
   - Limpeza do sistema Docker
   - Execução de políticas de retenção
   - Compressão automática de chunks antigos

2. **Tarefas Semanais (Domingo 4:15 AM)**
   - VACUUM ANALYZE completo
   - Compressão de dados > 30 dias
   - Limpeza de dados > 5 anos
   - Atualização de estatísticas

Para mais detalhes sobre manutenção do banco:

- Consulte `docs/db_maintenance.md`
- Verifique os logs em `/var/log/mt5/db_maintenance.log`

#### Monitoramento de Espaço

Verificar uso de espaço do banco:

```sql
SELECT
    hypertable_name,
    pg_size_pretty(total_bytes) as total_size,
    pg_size_pretty(total_compressed_bytes) as compressed_size,
    round(compression_ratio::numeric, 2) as compression_ratio
FROM timescaledb_information.hypertable_compression_stats;
```

## Automação Local de Calibração

O sistema recalibra automaticamente o threshold do modelo às 02:30 todos os dias. A automação é gerenciada via systemd e não requer nenhuma configuração externa de CI/CD.

### Componentes

- Script: `/usr/local/bin/recalibra_threshold.sh`
- Serviço: `/etc/systemd/system/recalibra-threshold.service`
- Timer: `/etc/systemd/system/recalibra-threshold.timer`

### Funcionamento

1. O script avalia diferentes thresholds (0.40-0.80)
2. Seleciona o melhor valor baseado no F1-score
3. Atualiza o arquivo `.env` com o novo threshold
4. Recria o container da API com a nova configuração

### Executar manualmente

```bash
sudo systemctl start recalibra-threshold.service
```

### Verificar próxima execução

```bash
systemctl list-timers | grep recalibra
```

### Ajustar horário

1. Edite o arquivo do timer:

```bash
sudo nano /etc/systemd/system/recalibra-threshold.timer
```

2. Modifique a linha `OnCalendar=*-*-* 02:30:00`

3. Reinicie o timer:

```bash
sudo systemctl daemon-reload
sudo systemctl restart recalibra-threshold.timer
```

### Teste rápido de validação

Após uma recalibração automática ou manual:

```bash
# Verificar o threshold atual aplicado
grep PRED_THRESHOLD .env

# Validar modelo carregado pela API
docker exec -i $(docker ps --filter "ancestor=mt5-api" -q) python - <<'PY'
import joblib
m=joblib.load("/models/latest_model.pkl")
print("Features:", getattr(m,"feature_names_in_",None))
PY

# Testar endpoint
curl -fsS "http://localhost:8001/signals/latest?symbol=EURUSD&period=H1"
````

## Observabilidade: Prometheus e Grafana

- Documentação detalhada: [docs/observabilidade.md](docs/observabilidade.md)
- Suba os serviços:

  ```bash
  docker compose up -d prometheus grafana
  ```

- Acesse:
  - Prometheus: <http://localhost:9090>
  - Grafana: <http://localhost:3000> (login: admin/admin)

## Infraestrutura como Código (Terraform)

- Estrutura inicial para provisionamento: `infra/terraform/`
- Veja `infra/terraform/README.md` para instruções iniciais.
