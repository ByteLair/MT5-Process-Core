#!/bin/bash

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER

# Criar grupo docker se não existir
sudo groupadd -f docker

# Ajustar permissões do socket do Docker
sudo chmod 666 /var/run/docker.sock
sudo chown root:docker /var/run/docker.sock

# Garantir que o serviço docker tem permissões corretas
sudo chown -R root:docker /var/lib/docker
sudo chmod -R g+rw /var/lib/docker

# Ajustar permissões do diretório de configuração do Docker
sudo mkdir -p ~/.docker
sudo chown -R $USER:docker ~/.docker
sudo chmod -R g+rw ~/.docker

# Garantir que systemd recarregue as permissões
sudo systemctl daemon-reload
sudo systemctl restart docker

# Mostrar grupos atuais e status
echo "Current groups for $USER:"
groups
echo -e "\nDocker service status:"
sudo systemctl status docker

echo -e "\nIMPORTANTE: Agora você deve:"
echo "1. Fazer logout e login novamente"
echo "2. Reiniciar o VS Code"
echo "3. Se os problemas persistirem, reiniciar o servidor"
