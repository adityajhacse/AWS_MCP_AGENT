output "ecr_repo_url" {
  value = aws_ecr_repository.adk_repo.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.adk_cluster.name
}

output "ecs_service_name" {
  value = aws_ecs_service.adk_service.name
}
