terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }

  cloud {
    organization = "lucasbahr12"
    workspaces {
      name = "meuct-api-prod"
    }
  }
  
}

provider "google" {
  project = var.project_id
  region  = var.region
  credentials = var.google_credentials
}

module "api" {
  source = "../../modules/cloud_run"

  service_name      = "meuct-api"
  environment       = "prod"
  region            = var.region
  project_id        = var.project_id
  image             = var.image

  database_url      = var.database_url
  secret_key        = var.secret_key
  algorithm         = var.algorithm

  ci_service_account = var.ci_service_account
}