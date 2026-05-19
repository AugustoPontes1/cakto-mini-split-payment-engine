import json

from django.test import TestCase

from app.api.models import Payment


class TestPaymentCreateView(TestCase):
    def test_successful_payment_creation(self):
        """POST /api/v1/payments com dados válidos retorna 201"""
        response = self.client.post(
            "/api/v1/payments",
            data=json.dumps({
                "amount": "297.00",
                "currency": "BRL",
                "payment_method": "card",
                "installments": 3,
                "splits": [
                    {"recipient_id": "p1", "role": "producer", "percent": 70},
                    {"recipient_id": "a1", "role": "affiliate", "percent": 30},
                ],
            }),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="key123",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "captured")
        self.assertIn("receivables", data)
        self.assertEqual(len(data["receivables"]), 2)

    def test_idempotency_same_key_same_payload(self):
        """Mesma key + mesmo payload = retorna 200 com resultado anterior"""
        payload = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "pix",
            "installments": 1,
            "splits": [{"recipient_id": "p1", "role": "producer", "percent": 100}],
        }

        response1 = self.client.post(
            "/api/v1/payments",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="key_abc",
        )
        payment_id_1 = response1.json()["payment_id"]

        response2 = self.client.post(
            "/api/v1/payments",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="key_abc",
        )
        payment_id_2 = response2.json()["payment_id"]

        self.assertEqual(response2.status_code, 200)
        self.assertEqual(payment_id_2, payment_id_1)
        self.assertEqual(Payment.objects.count(), 1)

    def test_idempotency_same_key_different_payload_returns_409(self):
        """Mesma key + payload diferente = retorna 409"""
        self.client.post(
            "/api/v1/payments",
            data=json.dumps({
                "amount": "100.00",
                "currency": "BRL",
                "payment_method": "pix",
                "installments": 1,
                "splits": [{"recipient_id": "p1", "role": "producer", "percent": 100}],
            }),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="key_xyz",
        )

        response = self.client.post(
            "/api/v1/payments",
            data=json.dumps({
                "amount": "200.00",
                "currency": "BRL",
                "payment_method": "pix",
                "installments": 1,
                "splits": [{"recipient_id": "p1", "role": "producer", "percent": 100}],
            }),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="key_xyz",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("conflict", response.json()["error"].lower())
