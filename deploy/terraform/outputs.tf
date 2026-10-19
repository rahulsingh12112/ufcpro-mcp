output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "pod_role_arn" {
  value = aws_iam_role.app.arn
}

output "account_id" {
  value = local.account_id
}
