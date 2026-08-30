import unittest
from lambdas.validate_order.lambda_function import lambda_handler as validate_order
from lambdas.pricing_engine.lambda_function import lambda_handler as pricing_engine
from lambdas.payment_processor.lambda_function import lambda_handler as payment_processor
from lambdas.delivery_dispatcher.lambda_function import lambda_handler as delivery_dispatcher

class TestDeliveryFlow(unittest.TestCase):

    def test_validate_order_success(self):
        payload = {
            "order_id": "ORD-TEST-1",
            "customer": {"name": "Teste", "address": "Rua 1"},
            "items": [{"name": "Pizza", "quantity": 1, "price": 40.0}],
            "payment_method": "CREDIT_CARD"
        }
        result = validate_order({"order": payload}, None)
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["order_id"], "ORD-TEST-1")

    def test_validate_order_failure(self):
        payload = {
            "order_id": "",
            "customer": {"name": ""},
            "items": []
        }
        result = validate_order({"order": payload}, None)
        self.assertFalse(result["is_valid"])
        self.assertTrue(len(result["errors"]) > 0)

    def test_pricing_calculation(self):
        payload = {
            "items": [
                {"name": "Item A", "quantity": 2, "price": 30.0}, # 60
                {"name": "Item B", "quantity": 1, "price": 50.0}  # 50 -> subtotal = 110 (frete grátis)
            ],
            "coupon_code": "BEMVINDO10"
        }
        result = pricing_engine(payload, None)
        self.assertEqual(result["status"], "PRICING_CALCULATED")
        pricing = result["pricing"]
        self.assertEqual(pricing["subtotal"], 110.0)
        self.assertEqual(pricing["delivery_fee"], 0.0)
        self.assertEqual(pricing["discount"], 11.0)
        self.assertEqual(pricing["total"], 99.0)

    def test_payment_success(self):
        payload = {
            "order_id": "ORD-123",
            "pricing": {"total": 50.0, "currency": "BRL"},
            "payment_method": "PIX"
        }
        result = payment_processor(payload, None)
        self.assertTrue(result["is_paid"])
        self.assertIn("TXN-", result["transaction_id"])

    def test_payment_declined(self):
        payload = {
            "order_id": "ORD-123",
            "pricing": {"total": 50.0, "currency": "BRL"},
            "payment_method": "INVALID_CARD"
        }
        result = payment_processor(payload, None)
        self.assertFalse(result["is_paid"])
        self.assertEqual(result["status"], "PAYMENT_FAILED")

    def test_delivery_dispatcher(self):
        payload = {
            "order_id": "ORD-123",
            "delivery_address": "Av. Brasil, 500"
        }
        result = delivery_dispatcher(payload, None)
        self.assertEqual(result["status"], "DISPATCHED")
        self.assertIn("courier", result["dispatch"])
        self.assertIn("tracking_code", result["dispatch"])

if __name__ == "__main__":
    unittest.main()
