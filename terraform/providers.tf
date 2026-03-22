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
      name = "meuct-api"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}