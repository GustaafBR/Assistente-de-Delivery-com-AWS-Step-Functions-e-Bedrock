import json
import logging
import random
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COURIERS = [
    {"id": "DRV-101", "name": "Carlos Silva", "vehicle": "Moto Honda Fan 160", "rating": 4.9},
    {"id": "DRV-202", "name": "Ana Oliveira", "vehicle": "Moto Yamaha Fazer", "rating": 5.0},
    {"id": "DRV-303", "name": "Marcos Souza", "vehicle": "Bicicleta Elétrica", "rating": 4.8}
]

def lambda_handler(event, context):
    """
    Aloca entregador disponível, calcula tempo estimado de entrega (ETA)
    e gera código de rastreamento.
    """
    logger.info(f"Despachando entrega para evento: {json.dumps(event)}")
    
    order_id = event.get("order_id")
    address = event.get("delivery_address", "Endereço padrão")
    
    courier = random.choice(COURIERS)
    tracking_code = f"TRK-{uuid.uuid4().hex[:8].upper()}"
    eta_minutes = random.randint(25, 45)
    
    dispatch_info = {
        "order_id": order_id,
        "courier": courier,
        "tracking_code": tracking_code,
        "eta_minutes": eta_minutes,
        "delivery_status": "OUT_FOR_DELIVERY",
        "destination": address
    }
    
    logger.info(f"Entrega despachada com sucesso: {dispatch_info}")
    return {
        "status": "DISPATCHED",
        "dispatch": dispatch_info
    }
