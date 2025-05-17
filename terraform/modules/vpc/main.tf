# Create VPC
resource "google_compute_network" "vpc" {
  name                    = var.vpc_name
  project                 = var.project_id
  auto_create_subnetworks = false
  mtu                     = 1460
}

# Create Subnet
resource "google_compute_subnetwork" "subnet" {
  name                     = "${var.vpc_name}-subnet"
  project                  = var.project_id
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.vpc.self_link
  private_ip_google_access = true
  
  dynamic "log_config" {
    for_each = var.flow_logs ? [1] : []
    content {
      aggregation_interval = "INTERVAL_10_MIN"
      flow_sampling        = 0.5
      metadata             = "INCLUDE_ALL_METADATA"
    }
  }
}

# Router for Cloud NAT
resource "google_compute_router" "router" {
  name    = "${var.vpc_name}-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.vpc.self_link
}

# Cloud NAT
resource "google_compute_router_nat" "nat" {
  name                               = "${var.vpc_name}-nat"
  project                            = var.project_id
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall Rules
resource "google_compute_firewall" "allow_ssh" {
  name          = "${var.vpc_name}-allow-ssh"
  project       = var.project_id
  network       = google_compute_network.vpc.name
  direction     = "INGRESS"
  source_ranges = var.allowed_ssh_ips
  
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  
  target_tags = ["ssh"]
}

resource "google_compute_firewall" "allow_http" {
  name          = "${var.vpc_name}-allow-http"
  project       = var.project_id
  network       = google_compute_network.vpc.name
  direction     = "INGRESS"
  source_ranges = ["0.0.0.0/0"]
  
  allow {
    protocol = "tcp"
    ports    = ["80"]
  }
  
  target_tags = ["http-server"]
}

resource "google_compute_firewall" "allow_https" {
  name          = "${var.vpc_name}-allow-https"
  project       = var.project_id
  network       = google_compute_network.vpc.name
  direction     = "INGRESS"
  source_ranges = ["0.0.0.0/0"]
  
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
  
  target_tags = ["https-server"]
}

# VPC Access Connector for Serverless VPC Access
resource "google_vpc_access_connector" "connector" {
  name          = "${var.vpc_name}-connector"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.vpc_connector_cidr
  
  min_throughput = 200
  max_throughput = 1000
}
