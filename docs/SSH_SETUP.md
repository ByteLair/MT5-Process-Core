# 🔑 Configuração SSH para Git sem Senha

> **Data de criação**: 15 de Novembro de 2025  
> **Autor**: ByteLair  
> **Status**: ✅ Implementado

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Chave SSH Criada](#chave-ssh-criada)
- [Configuração no GitHub](#configuração-no-github)
- [Teste de Conexão](#teste-de-conexão)
- [SSH-Agent Automático](#ssh-agent-automático)
- [Troubleshooting](#troubleshooting)
- [Segurança](#segurança)

---

## 🎯 Visão Geral

Este documento descreve a configuração SSH implementada no servidor de trading MT5 para permitir operações Git (push/pull) **sem necessidade de senha**.

### ✅ O que foi configurado:

| Item | Status | Localização |
|------|--------|-------------|
| Chave SSH ED25519 | ✅ Criada | `~/.ssh/id_ed25519` |
| Chave Pública | ✅ Gerada | `~/.ssh/id_ed25519.pub` |
| SSH-Agent | ✅ Configurado | Em execução |
| Git Remote | ✅ SSH | `git@github.com:ByteLair/MT5-Process-Core.git` |

---

## 🔑 Chave SSH Criada

### Tipo de Chave: ED25519

Escolhemos **ED25519** por ser:
- ✅ **Mais seguro** que RSA (256 bits = equivalente a RSA 3072 bits)
- ✅ **Mais rápido** (assinatura e verificação)
- ✅ **Mais curto** (chaves menores)
- ✅ **Moderno** (recomendado pelo GitHub)

### Localização das Chaves:

```bash
# Chave PRIVADA (NUNCA compartilhar!)
~/.ssh/id_ed25519

# Chave PÚBLICA (pode compartilhar)
~/.ssh/id_ed25519.pub
```

### Chave Pública Gerada:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICXHSB1Ee+CyhzasJ5vDTJJODSVvKDjRGxwCG9z/k7d5 lair@mt5-trading
```

**Fingerprint:**
```
SHA256:9Suk9pmL2k8dDI2Oezqy0hbN7HXQLuU/BWYWn4PqNZI
```

---

## ⚙️ Configuração no GitHub

### Passo 1: Acessar Configurações

1. Acesse: https://github.com/settings/keys
2. Ou: GitHub → Settings → SSH and GPG keys

### Passo 2: Adicionar Nova Chave

1. Clique em **"New SSH key"**

2. Preencha os campos:
   ```
   Title: MT5 Trading Server
   Key type: Authentication Key
   Key: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICXHSB1Ee+CyhzasJ5vDTJJODSVvKDjRGxwCG9z/k7d5 lair@mt5-trading
   ```

3. Clique em **"Add SSH key"**

4. Digite sua senha do GitHub para confirmar

### Passo 3: Verificar

Após adicionar, você verá a chave listada em:  
https://github.com/settings/keys

---

## 🧪 Teste de Conexão

### Testar Autenticação SSH:

```bash
ssh -T git@github.com
```

**Resultado esperado:**
```
Hi ByteLair! You've successfully authenticated, but GitHub does not provide shell access.
```

Se ver essa mensagem, **está funcionando!** ✅

### Testar Git Push/Pull:

```bash
# Testar pull
git pull

# Testar push (se tiver commits)
git push
```

**Não deve pedir senha!** 🎉

---

## 🤖 SSH-Agent Automático

### Problema:

Por padrão, `ssh-agent` não inicia automaticamente ao fazer login no servidor.

### Solução:

Adicionar ao `~/.bashrc` para iniciar automaticamente:

```bash
# Adicionar SSH-agent automático
echo '' >> ~/.bashrc
echo '# SSH-Agent automático' >> ~/.bashrc
echo 'if [ -z "$SSH_AUTH_SOCK" ]; then' >> ~/.bashrc
echo '    eval "$(ssh-agent -s)" > /dev/null' >> ~/.bashrc
echo '    ssh-add ~/.ssh/id_ed25519 2>/dev/null' >> ~/.bashrc
echo 'fi' >> ~/.bashrc
```

### Aplicar Agora:

```bash
source ~/.bashrc
```

### Verificar:

```bash
ssh-add -l
```

**Resultado esperado:**
```
256 SHA256:9Suk9pmL2k8dDI2Oezqy0hbN7HXQLuU/BWYWn4PqNZI lair@mt5-trading (ED25519)
```

---

## 🔧 Troubleshooting

### Problema 1: "Permission denied (publickey)"

**Causa**: Chave não foi adicionada ao GitHub ou ssh-agent não está rodando.

**Solução**:
```bash
# 1. Verificar se ssh-agent está rodando
eval "$(ssh-agent -s)"

# 2. Adicionar chave ao agent
ssh-add ~/.ssh/id_ed25519

# 3. Testar novamente
ssh -T git@github.com
```

### Problema 2: "Agent admitted failure to sign"

**Causa**: Chave não foi adicionada ao ssh-agent.

**Solução**:
```bash
ssh-add ~/.ssh/id_ed25519
```

### Problema 3: Git ainda pede senha

**Causa**: Remote está configurado para HTTPS ao invés de SSH.

**Solução**:
```bash
# Ver remote atual
git remote -v

# Se mostrar https://github.com/..., mudar para SSH:
git remote set-url origin git@github.com:ByteLair/MT5-Process-Core.git

# Verificar
git remote -v
```

### Problema 4: "Could not open a connection to your authentication agent"

**Causa**: ssh-agent não está rodando.

**Solução**:
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### Problema 5: Chave não funciona após reboot

**Causa**: ssh-agent não foi configurado para iniciar automaticamente.

**Solução**:
Seguir os passos em [SSH-Agent Automático](#ssh-agent-automático)

---

## 🔒 Segurança

### ✅ Boas Práticas Implementadas:

1. **Chave ED25519**: Algoritmo moderno e seguro
2. **Sem senha na chave**: Apropriado para servidor dedicado com acesso restrito
3. **Gitignore**: Chaves privadas NUNCA serão versionadas
4. **Permissões corretas**:
   ```bash
   # Verificar permissões
   ls -la ~/.ssh/
   
   # Deve mostrar:
   # -rw------- id_ed25519       (600 - apenas owner pode ler/escrever)
   # -rw-r--r-- id_ed25519.pub   (644 - todos podem ler)
   ```

### 🚨 NUNCA Faça:

❌ **NÃO compartilhe** a chave privada (`id_ed25519`)  
❌ **NÃO versione** chaves privadas no Git  
❌ **NÃO copie** chaves privadas para locais inseguros  
❌ **NÃO use** a mesma chave em múltiplos servidores (gere uma por servidor)

### ✅ SEMPRE Faça:

✅ **Mantenha** permissões corretas (600 para privada, 644 para pública)  
✅ **Use** chaves diferentes para cada servidor  
✅ **Revogue** chaves antigas no GitHub quando desativar servidor  
✅ **Monitore** as chaves ativas em: https://github.com/settings/keys

---

## 📁 Arquivos Protegidos no .gitignore

As seguintes extensões/arquivos estão protegidos contra versionamento acidental:

```gitignore
# SSH Keys (NUNCA versionar chaves privadas!)
*.pem
*.key
id_rsa
id_rsa.pub
id_ed25519
id_ed25519.pub
*.ppk
known_hosts
authorized_keys
```

---

## 🔄 Rotação de Chaves

### Quando Rotacionar:

- 🔄 Servidor foi comprometido
- 🔄 Chave foi exposta acidentalmente
- 🔄 Funcionário/colaborador saiu do projeto
- 🔄 Periodicamente (recomendado: a cada 6-12 meses)

### Como Rotacionar:

```bash
# 1. Gerar nova chave
ssh-keygen -t ed25519 -C "lair@mt5-trading-new" -f ~/.ssh/id_ed25519_new -N ""

# 2. Adicionar nova chave ao GitHub
cat ~/.ssh/id_ed25519_new.pub
# (Adicionar no GitHub)

# 3. Testar nova chave
ssh-add ~/.ssh/id_ed25519_new
ssh -T git@github.com

# 4. Se funcionar, substituir antiga
mv ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.old
mv ~/.ssh/id_ed25519_new ~/.ssh/id_ed25519
mv ~/.ssh/id_ed25519_new.pub ~/.ssh/id_ed25519.pub

# 5. Remover chave antiga do GitHub
# https://github.com/settings/keys

# 6. Apagar chave antiga do servidor
rm ~/.ssh/id_ed25519.old
```

---

## 📚 Referências

- [GitHub SSH Documentation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [ED25519 vs RSA](https://blog.g3rt.nl/upgrade-your-ssh-keys.html)
- [SSH Best Practices](https://infosec.mozilla.org/guidelines/openssh)

---

## 📝 Changelog

| Data | Versão | Mudanças |
|------|--------|----------|
| 2025-11-15 | 1.0.0 | Configuração inicial SSH ED25519 |

---

**✅ Status**: Configuração ativa e funcional  
**🔒 Segurança**: Chaves protegidas no .gitignore  
**🚀 Resultado**: Git push/pull sem senha funcionando!
