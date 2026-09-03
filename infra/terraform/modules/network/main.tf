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
