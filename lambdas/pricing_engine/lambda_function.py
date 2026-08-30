import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_DELIVERY_FEE = 7.50

def lambda_handler(event, context):
    """
    Calcula subtotal, frete dinâmico, descontos e total do pedido.
    """
    logger.info(f"Calculando preços para evento: {json.dumps(event)}")
    
    items = event.get("items", [])
    coupon = event.get("coupon_code", "").strip().upper()
    
    subtotal = 0.0
    for item in items:
        price = float(item.get("price", 0.0))
        qty = int(item.get("quantity", 1))
        subtotal += price * qty
        
    delivery_fee = BASE_DELIVERY_FEE
    
    # Frete grátis para pedidos acima de R$ 100,00
    if subtotal >= 100.0:
        delivery_fee = 0.0
        
    discount = 0.0
    if coupon == "BEMVINDO10":
        discount = subtotal * 0.10
    elif coupon == "BEDROCK15":
        discount = subtotal * 0.15
    elif coupon == "FRETEGRATIS":
        delivery_fee = 0.0

    total = max(0.0, subtotal + delivery_fee - discount)
    
    pricing_result = {
        "subtotal": round(subtotal, 2),
        "delivery_fee": round(delivery_fee, 2),
        "discount": round(discount, 2),
        "total": round(total, 2),
        "currency": "BRL"
    }
    
    logger.info(f"Cálculo final: {pricing_result}")
    return {
        "status": "PRICING_CALCULATED",
        "pricing": pricing_result
    }
