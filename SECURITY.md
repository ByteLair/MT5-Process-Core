# Security Policy

## Supported Versions

Atualmente estamos dando suporte de segurança para as seguintes versões:

| Version | Supported          |
| ------- | ------------------ |
| 2.1.x   | :white_check_mark: |
| 2.0.x   | :white_check_mark: |
| 1.x.x   | :x:                |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Se você descobrir uma vulnerabilidade de segurança, **NÃO abra uma issue pública**.

### Como Reportar

1. **Email**: Envie detalhes para **<kuramopr@gmail.com>** com:
   - Descrição da vulnerabilidade
   - Passos para reproduzir
   - Impacto potencial
   - Sugestões de mitigação (opcional)

2. **Resposta**: Você receberá confirmação em até **48 horas**

3. **Timeline**:
   - **7 dias**: Análise e validação
   - **14-30 dias**: Fix e release de patch
   - **30+ dias**: Disclosure coordenada (CVE se aplicável)

### O que NÃO fazer

- ❌ Não abra issue pública
- ❌ Não explore a vulnerabilidade em produção
- ❌ Não compartilhe publicamente antes do fix

## Vulnerabilidades Conhecidas

Nenhuma vulnerabilidade conhecida no momento.

## Security Best Practices

### Deployment

1. **Secrets Management**:

   ```bash
   # NUNCA commite arquivos .env
   # Use secrets manager em produção (AWS Secrets Manager, Vault, etc.)
   cp .env.example .env
   vim .env  # Configure secrets
   ```

2. **Database**:
   - Sempre use senhas fortes para `POSTGRES_PASSWORD`
   - Mude senha padrão do Grafana (`GRAFANA_PASSWORD`)
   - Configure firewall para expor apenas portas necessárias

3. **API**:
   - Configure `API_KEY` forte
   - Use HTTPS em produção (TLS/SSL)
   - Configure rate limiting
   - Implemente autenticação JWT (roadmap)

4. **Docker**:
   - Não rode containers como root (já configurado)
   - Mantenha imagens atualizadas
   - Use `.dockerignore` para evitar vazar secrets

5. **Network**:

   ```yaml
   # docker-compose.yml
   # Não exponha serviços internos publicamente
   # Apenas API (8001), Grafana (3000), Prometheus (9090)
   ```

### Atualizações de Segurança

O sistema possui automação para:

- **Verificação de vulnerabilidades**: Diariamente às 04:00 via `scripts/check_vulnerabilities.sh`
- **Dependabot**: Atualiza dependências automaticamente
- **CodeQL**: Análise de segurança estática no CI

### Monitoramento

Alertas configurados para:

- API down (indisponibilidade)
- Latência alta (possível DoS)
- Erro rate elevado (possível exploit)
- Disk usage crítico (possível exfiltração de dados)

Verifique Grafana: <http://localhost:3000/alerting>

### Hardening Checklist

- [ ] Senhas fortes em `.env`
- [ ] Firewall configurado (apenas portas necessárias)
- [ ] HTTPS habilitado (produção)
- [ ] Backup remoto configurado
- [ ] Logs centralizados (Loki)
- [ ] Alertas de segurança ativos
- [ ] Scans de vulnerabilidade automatizados
- [ ] Rate limiting na API
- [ ] Autenticação JWT (futuro)

## Security Scanning

### Automated Scans

```bash
# Python dependencies
safety check -r api/requirements.txt

# Container images (Trivy)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image mt5_api:latest

# Secrets scanning (gitleaks)
docker run --rm -v $(pwd):/repo zricethezav/gitleaks:latest detect --source /repo
```

### Manual Review

Antes de fazer deploy:

```bash
# Verificar secrets
grep -r "password\|secret\|key" --exclude-dir=.git --exclude-dir=venv

# Verificar permissions
find . -type f -perm /o+x

# Verificar .env
cat .env | grep -v "^#"
```

## Security Updates

- **Critical**: Patch liberado em até 24h
- **High**: Patch liberado em até 7 dias
- **Medium**: Patch liberado em até 30 dias
- **Low**: Incluído no próximo release

Patches de segurança são lançados como **hotfixes** fora do ciclo normal de releases.

## Contact

- **Security issues**: <kuramopr@gmail.com>
- **General questions**: GitHub Discussions
- **Bug reports** (não-segurança): GitHub Issues

---

**Obrigado por manter o sistema seguro!** 🔒
