output "service_url" {
  value = google_cloud_run_service.api.status[0].url
}

output "service_name" {
  value = google_cloud_run_service.api.name
}

output "media_bucket_name" {
  value       = google_storage_bucket.media.name
  description = "Bucket GCS único por ambiente; mídia isolada por prefixo por gym."
}

output "tenant_storage_key_pattern" {
  value       = "gs://${google_storage_bucket.media.name}/${var.gcs_tenant_prefix}/<gym_id>/{students,feed_items,marketplace}/"
  description = "Layout de chaves por tenant (bucket compartilhado)."
}