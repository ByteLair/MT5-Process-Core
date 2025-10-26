terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Networks
resource "docker_network" "mt5_network" {
  name   = "mt5_network"
  driver = "bridge"
}

# Volumes
resource "docker_volume" "postgres_data" {
  name = "mt5_postgres_data"
}

resource "docker_volume" "grafana_data" {
  name = "mt5_grafana_data"
}

resource "docker_volume" "prometheus_data" {
  name = "mt5_prometheus_data"
}

resource "docker_volume" "models" {
  name = "mt5_models"
}

# PostgreSQL/TimescaleDB Container
resource "docker_container" "postgres" {
  name  = "mt5_db"
  image = "timescale/timescaledb:2.14.2-pg16"

  networks_advanced {
    name = docker_network.mt5_network.name
    aliases = ["db"]
  }

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_DB=${var.postgres_db}"
  ]

  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ${var.postgres_user}"]
    interval = "10s"
    timeout  = "5s"
    retries  = 5
  }

  restart = "unless-stopped"
}

# API Container
resource "docker_image" "api" {
  name = "mt5-api:latest"
  build {
    context    = "../api"
    dockerfile = "Dockerfile"
  }
}

resource "docker_container" "api" {
  name  = "mt5_api"
  image = docker_image.api.image_id

  networks_advanced {
    name = docker_network.mt5_network.name
    aliases = ["api"]
  }

  ports {
    internal = 8001
    external = var.api_port
  }

  env = [
    "DATABASE_URL=postgresql://${var.postgres_user}:${var.postgres_password}@db:5432/${var.postgres_db}",
    "API_KEY=${var.api_key}",
    "MODELS_DIR=/models"
  ]

  volumes {
    volume_name    = docker_volume.models.name
    container_path = "/models"
  }

  healthcheck {
    test     = ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval = "30s"
    timeout  = "10s"
    retries  = 3
  }

  depends_on = [docker_container.postgres]
  restart    = "unless-stopped"
}

# Prometheus Container
resource "docker_container" "prometheus" {
  name  = "mt5_prometheus"
  image = "prom/prometheus:v2.52.0"

  networks_advanced {
    name = docker_network.mt5_network.name
    aliases = ["prometheus"]
  }

  ports {
    internal = 9090
    external = 9090
  }

  volumes {
    volume_name    = docker_volume.prometheus_data.name
    container_path = "/prometheus"
  }

  volumes {
    host_path      = abspath("${path.module}/../prometheus.yml")
    container_path = "/etc/prometheus/prometheus.yml"
    read_only      = true
  }

  command = [
    "--config.file=/etc/prometheus/prometheus.yml",
    "--storage.tsdb.path=/prometheus",
    "--web.console.libraries=/usr/share/prometheus/console_libraries",
    "--web.console.templates=/usr/share/prometheus/consoles"
  ]

  restart = "unless-stopped"
}

# Grafana Container
resource "docker_container" "grafana" {
  name  = "mt5_grafana"
  image = "grafana/grafana-oss:11.0.0"

  networks_advanced {
    name = docker_network.mt5_network.name
    aliases = ["grafana"]
  }

  ports {
    internal = 3000
    external = 3000
  }

  env = [
    "GF_SECURITY_ADMIN_USER=${var.grafana_admin_user}",
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_admin_password}",
    "GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource"
  ]

  volumes {
    volume_name    = docker_volume.grafana_data.name
    container_path = "/var/lib/grafana"
  }

  volumes {
    host_path      = abspath("${path.module}/../grafana/provisioning")
    container_path = "/etc/grafana/provisioning"
    read_only      = true
  }

  depends_on = [docker_container.prometheus]
  restart    = "unless-stopped"
}

# ML Scheduler Container (optional, can be scaled)
resource "docker_image" "ml" {
  name = "mt5-ml:latest"
  build {
    context    = "../ml"
    dockerfile = "Dockerfile"
  }
}

resource "docker_container" "ml_scheduler" {
  name  = "mt5_ml_scheduler"
  image = docker_image.ml.image_id

  networks_advanced {
    name = docker_network.mt5_network.name
  }

  env = [
    "DATABASE_URL=postgresql://${var.postgres_user}:${var.postgres_password}@db:5432/${var.postgres_db}",
    "MODELS_DIR=/models"
  ]

  volumes {
    volume_name    = docker_volume.models.name
    container_path = "/models"
  }

  command = ["python", "-u", "ml/scheduler.py"]

  depends_on = [docker_container.postgres, docker_container.api]
  restart    = "unless-stopped"
}
