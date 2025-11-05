variable "region" {
  type    = string
  default = "us-west-2"
}
/*
variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs where ECS tasks will run"
}

variable "security_group_id" {
  type        = string
  description = "Security group for ECS tasks"
}
*/