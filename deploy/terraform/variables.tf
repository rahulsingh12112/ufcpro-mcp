variable "region" {
  type    = string
  default = "us-east-1"
}

variable "cluster_name" {
  type    = string
  default = "rag-lab"
}

variable "app_name" {
  type    = string
  default = "ufcpro-mcp"
}

variable "namespace" {
  type    = string
  default = "ufcpro"
}

variable "service_account" {
  type    = string
  default = "ufcpro-mcp-sa"
}

variable "gitlab_project_path" {
  type        = string
  description = "GitLab project path, e.g. rahulsingh/ufcpro-mcp"
  default     = "rahulsingh/ufcpro-mcp"
}
