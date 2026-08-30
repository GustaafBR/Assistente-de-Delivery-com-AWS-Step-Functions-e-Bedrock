import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuração do cliente Bedrock Runtime
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# Modelo padrão (Claude 3 Haiku ou Titan Express)
DEFAULT_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

def invoke_claude_3(prompt: str, max_tokens: int = 500) -> str:
    """Invoca o modelo Anthropic Claude 3 via Bedrock."""
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    response = bedrock_client.invoke_model(
        modelId=DEFAULT_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )
    
    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"].strip()

def invoke_titan(prompt: str, max_tokens: int = 500) -> str:
    """Fallback para Amazon Titan caso esteja configurado."""
    payload = {
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": max_tokens,
            "stopSequences": [],
            "temperature": 0.5,
            "topP": 0.9
        }
    }
    
    response = bedrock_client.invoke_model(
        modelId=DEFAULT_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )
    
    response_body = json.loads(response["body"].read())
    return response_body["results"][0]["outputText"].strip()

def analyze_order_preferences(customer_name: str, items: list, special_instructions: str) -> dict:
    """
    Usa o Bedrock para analisar restrições alimentares, perfil de consumo e gerar sugestões de upsell/cross-sell.
    """
    items_str = ", ".join([f"{it.get('quantity', 1)}x {it.get('name')}" for it in items])
    
    prompt = f"""Você é o sommelier e assistente virtual inteligente de uma plataforma premium de delivery.
Analise os itens do pedido do cliente e forneça uma resposta EXCLUSIVAMENTE em formato JSON válido (sem tags markdown de código nem texto fora do JSON).

Dados do Pedido:
- Cliente: {customer_name}
- Itens: {items_str}
- Instruções Especiais: {special_instructions if special_instructions else "Nenhuma"}

Campos obrigatórios no JSON:
1. "dietary_profile": (ex: "Sem Glúten", "Vegano", "Vegetariano", "Lacto-vegetariano", "Padrão / Carnívoro", "Fitness")
2. "allergen_alert": (Texto breve de aviso se detectar potenciais alérgenos como amendoim, frutos do mar, lactose, glúten, ou null se seguro)
3. "personalized_recommendations": (Array com até 2 sugestões de acompanhamentos, bebidas ou sobremesas que harmonizam perfeitamente com o pedido)
4. "order_summary_ai": (Resumo atrativo e amigável em 1 frase sobre a experiência culinária escolhida)

Exemplo de formato esperado:
{{
  "dietary_profile": "Padrão",
  "allergen_alert": null,
  "personalized_recommendations": ["Refrigerante Artesanal de Limão", "Sobremesa Petit Gâteau"],
  "order_summary_ai": "Uma excelente combinação para um jantar saboroso e reconfortante!"
}}"""

    try:
        if "anthropic" in DEFAULT_MODEL_ID:
            raw_text = invoke_claude_3(prompt)
        else:
            raw_text = invoke_titan(prompt)
        
        # Limpeza para garantir JSON parse
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(cleaned_text)
        return parsed_json
    except Exception as e:
        logger.warning(f"Erro ao processar resposta do Bedrock ou invocar modelo: {e}. Usando fallback heurístico.")
        return {
            "dietary_profile": "Personalizado",
            "allergen_alert": None,
            "personalized_recommendations": ["Bebida refrescante da casa", "Sobremesa especial"],
            "order_summary_ai": f"Pedido especial preparado com carinho para {customer_name}!"
        }

def generate_notification_message(customer_name: str, order_id: str, items: list, eta_minutes: int, address: str) -> str:
    """
    Gera uma mensagem calorosa e personalizada para envio via WhatsApp/SMS após a confirmação.
    """
    items_str = ", ".join([f"{it.get('quantity', 1)}x {it.get('name')}" for it in items])
    
    prompt = f"""Você é o assistente virtual de delivery 'ChefBot'.
Crie uma mensagem amigável, entusiasmada e elegante para ser enviada pelo WhatsApp para o cliente informando que seu pedido foi confirmado e está em preparação.

Informações:
- Nome do Cliente: {customer_name}
- Número do Pedido: #{order_id}
- Itens do Pedido: {items_str}
- Tempo Estimado de Entrega: {eta_minutes} minutos
- Endereço de Entrega: {address}

Regras:
- Use emojis apropriados de gastronomia e entrega (ex: 🍕, 🛵, ✨).
- Mantenha o tom profissional, caloroso e conciso (máximo 4 a 5 linhas).
- Retorne APENAS o texto da mensagem pronta para envio."""

    try:
        if "anthropic" in DEFAULT_MODEL_ID:
            message = invoke_claude_3(prompt, max_tokens=250)
        else:
            message = invoke_titan(prompt, max_tokens=250)
        return message
    except Exception as e:
        logger.warning(f"Erro ao gerar mensagem com Bedrock: {e}. Usando template padrão.")
        return (f"Olá {customer_name}! 🚀 Seu pedido #{order_id} foi confirmado com sucesso. "
                f"Nossa cozinha já está preparando seus itens com todo capricho! "
                f"Tempo estimado de entrega: {eta_minutes} min no endereço {address}. Bom apetite! 🍽️")

def lambda_handler(event, context):
    """
    Roteador da Lambda para ações do Bedrock:
    - 'analyze_preferences': Análise de itens, restrições e cross-selling
    - 'generate_notification': Geração de texto humanizado de status
    """
    logger.info(f"Bedrock Handler recebeu evento: {json.dumps(event)}")
    
    action = event.get("action", "analyze_preferences")
    
    if action == "analyze_preferences":
        customer = event.get("customer", {})
        customer_name = customer.get("name", "Cliente")
        items = event.get("items", [])
        special_instructions = event.get("special_instructions", "")
        
        analysis = analyze_order_preferences(customer_name, items, special_instructions)
        return {
            "status": "ANALYZED",
            "ai_insights": analysis
        }
        
    elif action == "generate_notification":
        customer = event.get("customer", {})
        customer_name = customer.get("name", "Cliente")
        order_id = event.get("order_id", "000")
        items = event.get("items", [])
        eta_minutes = event.get("eta_minutes", 35)
        address = event.get("delivery_address", "")
        
        message = generate_notification_message(customer_name, order_id, items, eta_minutes, address)
        return {
            "status": "MESSAGE_GENERATED",
            "notification_message": message
        }
        
    else:
        return {
            "status": "UNKNOWN_ACTION",
            "error": f"Ação '{action}' não suportada."
        }
