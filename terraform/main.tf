resource "google_cloud_run_service" "api" {
  name     = "${var.service_name}-${var.environment}"
  location = var.region

  template {
    spec {
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