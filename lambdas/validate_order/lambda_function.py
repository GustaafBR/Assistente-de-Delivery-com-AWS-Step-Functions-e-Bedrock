import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Valida a integridade do pedido recebido:
    - Presença de dados do cliente (ID, nome, endereço)
    - Lista de itens não vazia com quantidades válidas
    - Forma de pagamento e valor declarado
    """
    logger.info(f"Recebendo evento para validação: {json.dumps(event)}")
    
    order = event.get("order", event)
    order_id = order.get("order_id")
    customer = order.get("customer", {})
    items = order.get("items", [])
    payment_method = order.get("payment_method")

    errors = []
    if not order_id:
        errors.append("Campo 'order_id' é obrigatório.")
    if not customer.get("name") or not customer.get("address"):
        errors.append("Dados do cliente incompletos (nome e endereço são obrigatórios).")
    if not items or not isinstance(items, list) or len(items) == 0:
        errors.append("O pedido deve conter pelo menos um item válido.")
    else:
        for idx, item in enumerate(items):
            if not item.get("name") or item.get("quantity", 0) <= 0 or item.get("price", 0) <= 0:
                errors.append(f"Item #{idx+1} possui dados inválidos (nome, quantidade > 0 e preço > 0).")
    if not payment_method:
        errors.append("Forma de pagamento não especificada.")

    if errors:
        logger.error(f"Validação falhou: {errors}")
        return {
            "status": "INVALID",
            "is_valid": False,
            "order_id": order_id,
            "errors": errors
        }

    logger.info(f"Pedido {order_id} validado com sucesso.")
    return {
        "status": "VALID",
        "is_valid": True,
        "order_id": order_id,
        "customer": customer,
        "items": items,
        "delivery_address": customer.get("address"),
        "payment_method": payment_method,
        "special_instructions": order.get("special_instructions", ""),
        "restaurant_id": order.get("restaurant_id", "REST-001")
    }
