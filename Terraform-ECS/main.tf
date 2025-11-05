
# --- 1. ECR Repository ---
resource "aws_ecr_repository" "adk_repo" {
  name = "adk-mcp-demo-ecr"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

# --- 2. Secrets Manager Secret ---
resource "aws_secretsmanager_secret" "adk_envs" {
  name = "adk-mcp-demo-sm"
}

resource "aws_secretsmanager_secret_version" "adk_envs_value" {
  secret_id     = aws_secretsmanager_secret.adk_envs.id
  secret_string = jsonencode({
    GOOGLE_API_KEY           = "abc123"
    AWS_REGION               = "us-west-2"
    AWS_ENVIRONMENT          = "dev"
    ADK_MCP_REQUEST_TIMEOUT  = "60"
  })
}

# --- 3. ECS Cluster ---
resource "aws_ecs_cluster" "adk_cluster" {
  name = "adk-mcp-demo-cluster"
}

# --- 3a. CloudWatch Logs ---
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/adk-mcp-demo"
  retention_in_days = 14
}

# --- 4a. Security Group for ECS Service in specified VPC ---
resource "aws_security_group" "adk_sg" {
  name        = "adk-mcp-demo-sg"
  description = "Security group for ECS service"
  vpc_id      = "vpc-00f4005d09cee9f00"

  # Allow all egress
  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

# --- 4. IAM Role for ECS Task Execution ---
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole-adk-mcp-demo"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# Attach AWS-managed ECS execution policy
resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow ECS task to read Secrets Manager secrets
resource "aws_iam_role_policy" "ecs_secrets_policy" {
  name = "ecsSecretsAccessPolicy-adk-mcp-demo"
  role = aws_iam_role.ecs_task_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.adk_envs.arn
      }
    ]
  })
}

# --- 5. ECS Task Definition ---
resource "aws_ecs_task_definition" "adk_task" {
  family                   = "adk-mcp-demo-family"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }
  container_definitions = jsonencode([
    {
      name      = "adk-mcp-demo-container"
      image     = "${aws_ecr_repository.adk_repo.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
      secrets = [
        {
          name      = "GOOGLE_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.adk_envs.arn}:GOOGLE_API_KEY::"
        },
        {
          name      = "AWS_REGION"
          valueFrom = "${aws_secretsmanager_secret.adk_envs.arn}:AWS_REGION::"
        },
        {
          name      = "AWS_ENVIRONMENT"
          valueFrom = "${aws_secretsmanager_secret.adk_envs.arn}:AWS_ENVIRONMENT::"
        },
        {
          name      = "ADK_MCP_REQUEST_TIMEOUT"
          valueFrom = "${aws_secretsmanager_secret.adk_envs.arn}:ADK_MCP_REQUEST_TIMEOUT::"
        },
        {
          name      = "AWS_ACCESS_KEY_ID"
          valueFrom = "${aws_secretsmanager_secret.adk_envs.arn}:AWS_ACCESS_KEY_ID::"
        },
        {
          name      = "AWS_SECRET_ACCESS_KEY"
          valueFrom = "${aws_secretsmanager_secret.adk_envs.arn}:AWS_SECRET_ACCESS_KEY::"
        }
      ]
    }
  ])
}

# --- 6. ECS Service (Fargate) ---
resource "aws_ecs_service" "adk_service" {
  name            = "adk-test-service"
  cluster         = aws_ecs_cluster.adk_cluster.id
  task_definition = aws_ecs_task_definition.adk_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [
      "subnet-098dab37403fcc61a",
      "subnet-00614293c63117563"
    ]
    security_groups  = [aws_security_group.adk_sg.id]
    assign_public_ip = true
  }
}
