# Terraform Infraestrutura

Estrutura inicial para provisionamento futuro da stack (DB, API, Prometheus, Grafana, etc) via Terraform.

## Instalação do Terraform

1. Baixe e instale o Terraform: <https://www.terraform.io/downloads.html>
2. No Linux, pode usar:

   ```bash
   sudo apt-get install unzip
   wget https://releases.hashicorp.com/terraform/1.8.2/terraform_1.8.2_linux_amd64.zip
   unzip terraform_1.8.2_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   terraform -v
   ```

## Como acessar e usar o Terraform

- Navegue até o diretório de infraestrutura:

  ```bash
  cd infra/terraform
  ```

- Inicialize o Terraform:

  ```bash
  terraform init
  ```

- Visualize o plano de execução:

  ```bash
  terraform plan
  ```

- Provisione os recursos:

  ```bash
  terraform apply
  ```

## Exemplo incluído

- O arquivo `main.tf` provisiona um container Docker do TimescaleDB/PostgreSQL localmente.
- Para provisionamento em nuvem, adicione o provider e recursos desejados (AWS, GCP, Azure).

---

# ENGLISH

## Terraform Installation

1. Download and install Terraform: <https://www.terraform.io/downloads.html>
2. On Linux:

   ```bash
   sudo apt-get install unzip
   wget https://releases.hashicorp.com/terraform/1.8.2/terraform_1.8.2_linux_amd64.zip
   unzip terraform_1.8.2_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   terraform -v
   ```

## How to access and use Terraform

- Go to the infrastructure directory:

  ```bash
  cd infra/terraform
  ```

- Initialize Terraform:

  ```bash
  terraform init
  ```

- Preview the execution plan:

  ```bash
  terraform plan
  ```

- Apply the resources:

  ```bash
  terraform apply
  ```

## Example included

- The `main.tf` file provisions a local TimescaleDB/PostgreSQL Docker container.
- For cloud provisioning, add the desired provider and resources (AWS, GCP, Azure).
