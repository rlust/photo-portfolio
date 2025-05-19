# Create the Cloud Storage bucket
resource "google_storage_bucket" "bucket" {
  name                        = var.bucket_name
  location                    = var.location
  project                     = var.project_id
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy
  storage_class               = var.storage_class
  
  versioning {
    enabled = var.versioning_enabled
  }
  
  dynamic "cors" {
    for_each = var.cors == null ? [] : [var.cors]
    content {
      origin          = lookup(cors.value, "origin", null)
      method          = lookup(cors.value, "method", null)
      response_header = lookup(cors.value, "response_header", null)
      max_age_seconds = lookup(cors.value, "max_age_seconds", null)
    }
  }
  
  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_rules
    content {
      action {
        type          = lifecycle_rule.value.action.type
        storage_class = lookup(lifecycle_rule.value.action, "storage_class", null)
      }
      condition {
        age                   = lookup(lifecycle_rule.value.condition, "age", null)
        created_before        = lookup(lifecycle_rule.value.condition, "created_before", null)
        with_state            = lookup(lifecycle_rule.value.condition, "with_state", null)
        matches_storage_class = lookup(lifecycle_rule.value.condition, "matches_storage_class", null)
        num_newer_versions    = lookup(lifecycle_rule.value.condition, "num_newer_versions", null)
      }
    }
  }
}

# IAM bindings
resource "google_storage_bucket_iam_member" "members" {
  for_each = var.iam_members
  
  bucket = google_storage_bucket.bucket.name
  role   = each.value.role
  member = each.value.member
}

# Object ACLs if needed
resource "google_storage_default_object_acl" "default_acl" {
  count = var.default_acl != null ? 1 : 0
  
  bucket      = google_storage_bucket.bucket.name
  role_entity = var.default_acl
}

# Public access prevention
resource "google_storage_bucket_iam_policy" "policy" {
  count = var.prevent_public_access ? 1 : 0
  
  bucket      = google_storage_bucket.bucket.name
  policy_data  = data.google_iam_policy.prevent_public_access[0].policy_data
}

data "google_iam_policy" "prevent_public_access" {
  count = var.prevent_public_access ? 1 : 0
  
  binding {
    role = "roles/storage.admin"
    members = [
      "serviceAccount:${var.service_account_email}",
    ]
  }
  
  binding {
    role = "roles/storage.objectViewer"
    members = var.additional_viewers
  }
}
