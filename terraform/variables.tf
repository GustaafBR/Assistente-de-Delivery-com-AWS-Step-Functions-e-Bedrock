variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Região da AWS para deploy"
}

variable "bedrock_model_id" {
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
  description = "ID do modelo fundacional do Amazon Bedrock"
}
