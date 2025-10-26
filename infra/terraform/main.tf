# main.tf
# Exemplo de provisionamento local com Docker provider

terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
      version = "2.25.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "postgres" {
  name = "timescale/timescaledb:2.14.2-pg16"
}

resource "docker_container" "db" {
  name  = "mt5_db_tf"
  image = docker_image.postgres.latest
  ports {
    internal = 5432
    external = 5433
  }
  env = [
    "POSTGRES_USER=trader",
    "POSTGRES_PASSWORD=trader123",
    "POSTGRES_DB=mt5_trading"
  ]
}
