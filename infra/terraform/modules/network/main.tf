data "aws_region" "current" {}

locals {
  interface_services = var.enable_vpc_endpoints ? toset([
    "sagemaker.api",
    "sagemaker.runtime",
    "ecr.api",
    "ecr.dkr",
    "logs",
    "sts",
    "monitoring",
  ]) : toset([])
}

data "aws_route_table" "subnet" {
  for_each  = var.enable_vpc_endpoints ? toset(var.subnet_ids) : toset([])
  subnet_id = each.value
}

locals {
  route_table_ids = distinct([for rt in data.aws_route_table.subnet : rt.id])
}

resource "aws_security_group" "sagemaker" {
  name        = "${var.name_prefix}-sagemaker"
  description = "SageMaker pipeline, training, and endpoint traffic"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-sagemaker" })
}

resource "aws_security_group" "vpc_endpoints" {
  count       = var.enable_vpc_endpoints ? 1 : 0
  name        = "${var.name_prefix}-vpce"
  description = "Interface VPC endpoints for SageMaker / ECR / Logs / STS"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTPS from SageMaker SG"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.sagemaker.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-vpce" })
}

resource "aws_vpc_endpoint" "s3" {
  count             = var.enable_vpc_endpoints ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = local.route_table_ids
  tags              = merge(var.tags, { Name = "${var.name_prefix}-s3" })
}

resource "aws_vpc_endpoint" "interface" {
  for_each = local.interface_services

  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = [aws_security_group.vpc_endpoints[0].id]
  private_dns_enabled = true
  tags                = merge(var.tags, { Name = "${var.name_prefix}-${replace(each.value, ".", "-")}" })
}
