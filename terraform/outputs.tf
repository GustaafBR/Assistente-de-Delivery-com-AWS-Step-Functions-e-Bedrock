output "state_machine_arn" {
  description = "ARN da State Machine do AWS Step Functions"
  value       = aws_sfn_state_machine.delivery_assistant.arn
}

output "bedrock_handler_lambda_arn" {
  description = "ARN da função Lambda integrada ao Bedrock"
  value       = aws_lambda_function.bedrock_handler.arn
}
