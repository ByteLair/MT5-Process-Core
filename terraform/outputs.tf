output "api_url" {
  description = "URL to access the MT5 Trading API"
  value       = "http://localhost:${var.api_port}"
}

output "prometheus_url" {
  description = "URL to access Prometheus"
  value       = "http://localhost:9090"
}

output "grafana_url" {
  description = "URL to access Grafana"
  value       = "http://localhost:3000"
}

output "grafana_credentials" {
  description = "Grafana login credentials"
  value = {
    username = var.grafana_admin_user
    password = var.grafana_admin_password
  }
  sensitive = true
}

output "network_name" {
  description = "Docker network name"
  value       = docker_network.mt5_network.name
}

output "postgres_connection" {
  description = "PostgreSQL connection string (internal)"
  value       = "postgresql://${var.postgres_user}:${var.postgres_password}@db:5432/${var.postgres_db}"
  sensitive   = true
}
