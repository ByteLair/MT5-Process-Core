variable "postgres_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "trader"
}

variable "postgres_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
  default     = "trader123"
}

variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "mt5_trading"
}

variable "api_port" {
  description = "External port for the API service"
  type        = number
  default     = 18001
}

variable "api_key" {
  description = "API authentication key"
  type        = string
  sensitive   = true
  default     = "mt5_trading_secure_key_2025_prod"
}

variable "grafana_admin_user" {
  description = "Grafana admin username"
  type        = string
  default     = "admin"
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
  default     = "admin"
}
