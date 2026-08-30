import json
import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
sns_client = boto3.client("sns") if SNS_TOPIC_ARN else None

def lambda_handler(event, context):
    """
    Envia a notificação final ao cliente com os dados da entrega e o texto humanizado gerado pelo Bedrock.
    """
    logger.info(f"Enviando notificação: {json.dumps(event)}")
    
    order_id = event.get("order_id")
    customer = event.get("customer", {})
    message = event.get("notification_message", "Seu pedido foi despachado com sucesso!")
    dispatch = event.get("dispatch", {})
    
    delivery_report = {
        "channel": "WHATSAPP_AND_SMS",
        "recipient": customer.get("phone", customer.get("name")),
        "message": message,
        "tracking_code": dispatch.get("tracking_code"),
        "courier": dispatch.get("courier", {}).get("name"),
        "eta": f"{dispatch.get('eta_minutes', 30)} minutos"
    }
    
    if sns_client and SNS_TOPIC_ARN:
        try:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"Status do Pedido #{order_id}",
                Message=json.dumps(delivery_report, ensure_ascii=False)
            )
            logger.info("Notificação publicada no AWS SNS com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao publicar no SNS: {e}")
            
    return {
        "status": "NOTIFICATION_SENT",
        "delivery_report": delivery_report
    }
