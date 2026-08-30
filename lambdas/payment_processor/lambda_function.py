import json
import logging
import uuid
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Processa o pagamento do pedido.
    Simula autorização e captura de transação bancária / cartão / PIX.
    """
    logger.info(f"Processando pagamento: {json.dumps(event)}")
    
    order_id = event.get("order_id")
    pricing = event.get("pricing", {})
    total_amount = pricing.get("total", 0.0)
    payment_method = event.get("payment_method", "CREDIT_CARD")
    
    # Simulação de regra de negócio: Se o método for 'INVALID_CARD' ou valor <= 0, rejeita
    if payment_method == "INVALID_CARD" or total_amount <= 0:
        logger.error(f"Pagamento recusado para o pedido {order_id}.")
        return {
            "status": "PAYMENT_FAILED",
            "is_paid": False,
            "order_id": order_id,
            "error_code": "DECLINED_BY_ISSUER",
            "message": "Transação não autorizada pela operadora do cartão."
        }
        
    transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    timestamp = int(time.time())
    
    logger.info(f"Pagamento aprovado. ID da Transação: {transaction_id}")
    return {
        "status": "PAYMENT_CONFIRMED",
        "is_paid": True,
        "order_id": order_id,
        "transaction_id": transaction_id,
        "amount_paid": total_amount,
        "currency": pricing.get("currency", "BRL"),
        "payment_method": payment_method,
        "processed_at": timestamp
    }
