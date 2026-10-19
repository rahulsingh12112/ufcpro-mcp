terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

data "aws_eks_cluster" "this" {
  name = var.cluster_name
}

locals {
  account_id = data.aws_caller_identity.current.account_id
}

# ---------------------------------------------------------------------------
# 1. ECR repository for the app image
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "app" {
  name                 = var.app_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ---------------------------------------------------------------------------
# NOTE: eks-pod-identity-agent addon is ALREADY installed on the cluster,
# so we do NOT manage it here (avoids an "already exists" error).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 2. IAM role the pod will assume — trusted by Pod Identity (not OIDC)
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "pod_identity_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole", "sts:TagSession"]

    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${var.app_name}-pod-role"
  assume_role_policy = data.aws_iam_policy_document.pod_identity_trust.json
}

data "aws_iam_policy_document" "bedrock_access" {
  statement {
    sid    = "InvokeBedrockClaude"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = [
      "arn:aws:bedrock:${var.region}::foundation-model/anthropic.*",
      "arn:aws:bedrock:${var.region}:${local.account_id}:inference-profile/*",
    ]
  }
}

resource "aws_iam_role_policy" "bedrock" {
  name   = "bedrock-invoke"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.bedrock_access.json
}

# ---------------------------------------------------------------------------
# 3. Pod Identity association — ties the role to the K8s ServiceAccount
#    (the pod-identity-agent addon is already present on the cluster)
# ---------------------------------------------------------------------------
resource "aws_eks_pod_identity_association" "app" {
  cluster_name    = var.cluster_name
  namespace       = var.namespace
  service_account = var.service_account
  role_arn        = aws_iam_role.app.arn
}
