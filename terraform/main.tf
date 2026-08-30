terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ------------------------------------------------------------------
# IAM Role para AWS Step Functions
# ------------------------------------------------------------------
resource "aws_iam_role" "step_functions_role" {
  name = "delivery-assistant-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "sfn_invoke_lambda_policy" {
  name = "delivery-assistant-sfn-invoke-lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sfn_attach" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = aws_iam_policy.sfn_invoke_lambda_policy.arn
}

# ------------------------------------------------------------------
# IAM Role para AWS Lambda com permissões do Amazon Bedrock
# ------------------------------------------------------------------
resource "aws_iam_role" "lambda_exec_role" {
  name = "delivery-assistant-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_bedrock_policy" {
  name = "delivery-assistant-lambda-bedrock-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_bedrock_policy.arn
}

# ------------------------------------------------------------------
# Compactação dos códigos das Lambdas
# ------------------------------------------------------------------
data "archive_file" "validate_order_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/validate_order"
  output_path = "${path.module}/validate_order.zip"
}

data "archive_file" "bedrock_handler_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/bedrock_handler"
  output_path = "${path.module}/bedrock_handler.zip"
}

data "archive_file" "pricing_engine_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/pricing_engine"
  output_path = "${path.module}/pricing_engine.zip"
}

data "archive_file" "payment_processor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/payment_processor"
  output_path = "${path.module}/payment_processor.zip"
}

data "archive_file" "delivery_dispatcher_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/delivery_dispatcher"
  output_path = "${path.module}/delivery_dispatcher.zip"
}

data "archive_file" "notification_sender_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/notification_sender"
  output_path = "${path.module}/notification_sender.zip"
}

# ------------------------------------------------------------------
# Recursos Lambda
# ------------------------------------------------------------------
resource "aws_lambda_function" "validate_order" {
  function_name    = "DeliveryAssistant-ValidateOrder"
  filename         = data.archive_file.validate_order_zip.output_path
  source_code_hash = data.archive_file.validate_order_zip.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec_role.arn
}

resource "aws_lambda_function" "bedrock_handler" {
  function_name    = "DeliveryAssistant-BedrockHandler"
  filename         = data.archive_file.bedrock_handler_zip.output_path
  source_code_hash = data.archive_file.bedrock_handler_zip.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec_role.arn
  timeout          = 30

  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
    }
  }
}

resource "aws_lambda_function" "pricing_engine" {
  function_name    = "DeliveryAssistant-PricingEngine"
  filename         = data.archive_file.pricing_engine_zip.output_path
  source_code_hash = data.archive_file.pricing_engine_zip.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec_role.arn
}

resource "aws_lambda_function" "payment_processor" {
  function_name    = "DeliveryAssistant-PaymentProcessor"
  filename         = data.archive_file.payment_processor_zip.output_path
  source_code_hash = data.archive_file.payment_processor_zip.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec_role.arn
}

resource "aws_lambda_function" "delivery_dispatcher" {
  function_name    = "DeliveryAssistant-DeliveryDispatcher"
  filename         = data.archive_file.delivery_dispatcher_zip.output_path
  source_code_hash = data.archive_file.delivery_dispatcher_zip.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec_role.arn
}

resource "aws_lambda_function" "notification_sender" {
  function_name    = "DeliveryAssistant-NotificationSender"
  filename         = data.archive_file.notification_sender_zip.output_path
  source_code_hash = data.archive_file.notification_sender_zip.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec_role.arn
}

# ------------------------------------------------------------------
# AWS Step Functions State Machine
# ------------------------------------------------------------------
resource "aws_sfn_state_machine" "delivery_assistant" {
  name     = "DeliveryAssistant-StateMachine"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../statemachine/delivery_assistant.asl.json", {
    ValidateOrderFunctionArn      = aws_lambda_function.validate_order.arn
    BedrockHandlerFunctionArn     = aws_lambda_function.bedrock_handler.arn
    PricingEngineFunctionArn      = aws_lambda_function.pricing_engine.arn
    PaymentProcessorFunctionArn   = aws_lambda_function.payment_processor.arn
    DeliveryDispatcherFunctionArn = aws_lambda_function.delivery_dispatcher.arn
    NotificationSenderFunctionArn = aws_lambda_function.notification_sender.arn
  })
}
