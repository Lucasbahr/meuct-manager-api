variable "project_id" {
  type = string
}

variable "region" {
  default = "us-central1"
}

variable "service_name" {
  default = "meuct-api"
}

variable "image" {
  description = "Docker image URL"
  type        = string
}

variable "database_url" {
  description = "Neon database URL"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment (prod or hml)"
  type        = string
}