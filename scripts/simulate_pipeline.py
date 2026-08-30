"""
Script de Simulação Local para o Assistente de Delivery com AWS Step Functions e Amazon Bedrock.
Permite testar o fluxo completo localmente passo a passo, simulando as transições de estado da State Machine.
"""

import json
import os
import sys
import time

# Adiciona o diretório raiz ao path para importar as lambdas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lambdas.validate_order.lambda_function import lambda_handler as validate_order_handler
from lambdas.pricing_engine.lambda_function import lambda_handler as pricing_handler
from lambdas.payment_processor.lambda_function import lambda_handler as payment_handler
from lambdas.delivery_dispatcher.lambda_function import lambda_handler as dispatch_handler
from lambdas.bedrock_handler.lambda_function import lambda_handler as bedrock_handler
from lambdas.notification_sender.lambda_function import lambda_handler as notification_handler

def print_separator(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f"  📌 {title.upper()}")
        print("=" * 70)

def simulate_step_functions_execution(event_file_path: str):
    print_separator(f"Iniciando Execução da State Machine: {os.path.basename(event_file_path)}")
    
    with open(event_file_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)
        
    print("📥 Payload de Entrada:")
    print(json.dumps(input_data, indent=2, ensure_ascii=False))
    
    # 1. State: ValidateOrder
    print_separator("1. Estado: ValidateOrder")
    validation_res = validate_order_handler({"order": input_data}, None)
    print("Output de Validação:")
    print(json.dumps(validation_res, indent=2, ensure_ascii=False))
    
    if not validation_res.get("is_valid"):
        print("\n❌ [ESTADO FAIL]: OrderValidationFailed -> Fluxo interrompido.")
        return
    
    print("\n✅ Pedido Válido! Prosseguindo para processamento paralelo...")

    # 2. State: ParallelProcessingAIAndPricing
    print_separator("2. Estado Paralelo: Bedrock AI + Pricing Engine")
    
    # Branch A: Bedrock
    print("  🧠 Invocando Amazon Bedrock (Análise Nutricional & Cross-Selling)...")
    bedrock_ai_res = bedrock_handler({
        "action": "analyze_preferences",
        "customer": validation_res.get("customer"),
        "items": validation_res.get("items"),
        "special_instructions": validation_res.get("special_instructions")
    }, None)
    print("  Resultado Bedrock:")
    print(" ", json.dumps(bedrock_ai_res, indent=2, ensure_ascii=False))
    
    # Branch B: Pricing
    print("\n  💰 Invocando Pricing Engine...")
    pricing_res = pricing_handler({
        "items": validation_res.get("items"),
        "coupon_code": input_data.get("coupon_code", "")
    }, None)
    print("  Resultado Pricing:")
    print(" ", json.dumps(pricing_res, indent=2, ensure_ascii=False))
    
    # 3. State: ProcessPayment
    print_separator("3. Estado: ProcessPayment")
    payment_res = payment_handler({
        "order_id": validation_res.get("order_id"),
        "pricing": pricing_res.get("pricing"),
        "payment_method": validation_res.get("payment_method")
    }, None)
    print("Resultado do Pagamento:")
    print(json.dumps(payment_res, indent=2, ensure_ascii=False))
    
    if not payment_res.get("is_paid"):
        print("\n❌ [ESTADO FAIL]: PaymentDeclined -> Pagamento recusado.")
        return

    print("\n✅ Pagamento Aprovado com Sucesso!")

    # 4. State: DispatchDelivery
    print_separator("4. Estado: DispatchDelivery")
    dispatch_res = dispatch_handler({
        "order_id": validation_res.get("order_id"),
        "delivery_address": validation_res.get("delivery_address")
    }, None)
    print("Resultado do Despacho:")
    print(json.dumps(dispatch_res, indent=2, ensure_ascii=False))

    # 5. State: GenerateBedrockNotification
    print_separator("5. Estado: GenerateBedrockNotification (Amazon Bedrock)")
    print("  🤖 Gerando mensagem humanizada com Claude 3 / Titan via Bedrock...")
    eta_min = dispatch_res.get("dispatch", {}).get("eta_minutes", 30)
    ai_notif_res = bedrock_handler({
        "action": "generate_notification",
        "customer": validation_res.get("customer"),
        "order_id": validation_res.get("order_id"),
        "items": validation_res.get("items"),
        "eta_minutes": eta_min,
        "delivery_address": validation_res.get("delivery_address")
    }, None)
    print("Mensagem Gerada pela IA:")
    print(ai_notif_res.get("notification_message"))

    # 6. State: SendCustomerNotification
    print_separator("6. Estado: SendCustomerNotification")
    notif_res = notification_handler({
        "order_id": validation_res.get("order_id"),
        "customer": validation_res.get("customer"),
        "notification_message": ai_notif_res.get("notification_message"),
        "dispatch": dispatch_res.get("dispatch")
    }, None)
    print("Relatório de Envio:")
    print(json.dumps(notif_res, indent=2, ensure_ascii=False))

    # 7. State: OrderSuccessSummary
    print_separator("🎉 Estado Final: OrderSuccessSummary (SUCCEED)")
    final_output = {
        "status": "COMPLETED",
        "order_id": validation_res.get("order_id"),
        "customer": validation_res.get("customer"),
        "pricing": pricing_res.get("pricing"),
        "payment": payment_res,
        "ai_insights": bedrock_ai_res.get("ai_insights"),
        "dispatch": dispatch_res.get("dispatch"),
        "notification": notif_res.get("delivery_report")
    }
    print(json.dumps(final_output, indent=2, ensure_ascii=False))
    print("\n✅ Fluxo do Step Functions finalizado com êxito!")

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    events_dir = os.path.abspath(os.path.join(base_dir, "..", "events"))
    
    test_files = [
        "order_valid.json",
        "order_vegan_custom.json",
        "order_payment_declined.json",
        "order_missing_fields.json"
    ]
    
    print("Escolha o cenário de teste para simular:")
    for idx, f in enumerate(test_files):
        print(f"[{idx + 1}] {f}")
    
    choice = input("\nDigite o número (1 a 4) ou Enter para executar o padrão (1): ").strip()
    selected_file = test_files[0]
    if choice in ["1", "2", "3", "4"]:
        selected_file = test_files[int(choice) - 1]
        
    full_event_path = os.path.join(events_dir, selected_file)
    simulate_step_functions_execution(full_event_path)
