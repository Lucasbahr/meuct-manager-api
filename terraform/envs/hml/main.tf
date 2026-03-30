resource "google_service_account" "run_sa" {
  account_id   = "meuct-run-${var.environment}"
  display_name = "Cloud Run Service Account (${var.environment})"
}


resource "google_service_account_iam_member" "ci_act_as" {
  service_account_id = google_service_account.run_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.ci_service_account}"
}

locals {
  media_bucket_name = "${var.service_name}-media-${var.environment}-${substr(replace(var.project_id, "_", "-"), 0, 12)}"
}

resource "google_storage_bucket" "media" {
  name                        = local.media_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "run_sa_media_admin" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.run_sa.email}"
}


resource "google_cloud_run_service" "api" {
  name     = "${var.service_name}-${var.environment}"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.run_sa.email

      containers {
        image = var.image

        env {
          name  = "DATABASE_URL"
          value = var.database_url
        }

        env {
          name  = "ENV"
          value = var.environment
        }

        env {
          name  = "SECRET_KEY"
          value = var.secret_key
        }

        env {
          name  = "ALGORITHM"
          value = var.algorithm
        }
        
        env {
          name  = "SMTP_HOST"
          value = var.smtp_host
        }

        env {
          name  = "SMTP_PORT"
          value = tostring(var.smtp_port)
        }

        env {
          name  = "SMTP_USER"
          value = var.smtp_user
        }

        env {
          name  = "SMTP_PASSWORD"
          value = var.smtp_password
        }

        env {
          name  = "BASE_URL"
          value = var.base_url
        }

        env {
          name  = "STORAGE_PROVIDER"
          value = "gcs"
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.media.name
        }

        ports {
          container_port = 8080
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.api.name
  location = google_cloud_run_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}