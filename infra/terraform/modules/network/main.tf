data "aws_region" "current" {}

data "aws_vpc" "this" {
  id = var.vpc_id
}

locals {
  # Design v7 endpoint sets. The control plane trains (POC), registers, approves and
  # serves the private management API; BU accounts pull images and serve endpoints.
  default_interface_services = {
    control_plane = [
      "sagemaker.api", "sagemaker.runtime", "ecr.api", "ecr.dkr", "logs", "sts",
      "monitoring", "events", "lambda", "execute-api",
    ]
    bu = [
      "ecr.api", "ecr.dkr", "sagemaker.api", "sagemaker.runtime", "sts", "logs", "events", "lambda",
    ]
  }
  interface_services = var.enable_vpc_endpoints ? toset(
    var.interface_services != null ? var.interface_services : local.default_interface_services[var.plane]
  ) : toset([])
  enable_dynamodb_gateway = var.enable_vpc_endpoints && coalesce(var.enable_dynamodb_gateway, var.plane == "control_plane")
}

data "aws_route_table" "subnet" {
  for_each  = var.enable_vpc_endpoints ? toset(var.subnet_ids) : toset([])
  subnet_id = each.value
}

locals {
  route_table_ids = distinct([for rt in data.aws_route_table.subnet : rt.id])
  gateway_prefix_lists = compact([
    try(aws_vpc_endpoint.s3[0].prefix_list_id, ""),
    try(aws_vpc_endpoint.dynamodb[0].prefix_list_id, ""),
  ])
}

resource "aws_vpc_endpoint" "s3" {
  count             = var.enable_vpc_endpoints ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = local.route_table_ids
  tags              = merge(var.tags, { Name = "${var.name_prefix}-s3" })
}

resource "aws_vpc_endpoint" "dynamodb" {
  count             = local.enable_dynamodb_gateway ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = local.route_table_ids
  tags              = merge(var.tags, { Name = "${var.name_prefix}-dynamodb" })
}

# Workloads (training, processing, endpoints, VPC Lambdas): HTTPS to endpoints inside the
# VPC and to the S3/DynamoDB gateways, plus traffic within the group (distributed jobs).
resource "aws_security_group" "sagemaker" {
  name        = "${var.name_prefix}-sagemaker"
  description = "SageMaker pipeline, training, endpoint and platform Lambda traffic"
  vpc_id      = var.vpc_id

  egress {
    description = "Within the workload group"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "HTTPS to interface endpoints in the VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.this.cidr_block]
  }

  dynamic "egress" {
    for_each = length(local.gateway_prefix_lists) > 0 ? [1] : []
    content {
      description     = "HTTPS to S3/DynamoDB gateway endpoints"
      from_port       = 443
      to_port         = 443
      protocol        = "tcp"
      prefix_list_ids = local.gateway_prefix_lists
    }
  }

  dynamic "egress" {
    for_each = var.enable_vpc_endpoints ? [] : [1]
    content {
      description = "HTTPS via NAT when VPC endpoints are disabled"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  ingress {
    description = "Within the workload group"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-sagemaker" })
}

resource "aws_security_group" "vpc_endpoints" {
  count       = var.enable_vpc_endpoints ? 1 : 0
  name        = "${var.name_prefix}-vpce"
  description = "Interface VPC endpoints (HTTPS from the VPC only)"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from the VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.this.cidr_block]
  }

  egress = []

  tags = merge(var.tags, { Name = "${var.name_prefix}-vpce" })
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
