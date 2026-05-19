from models import Payment


class TestPaymentCreateView:
    def test_successful_payment_creation(self, client):
        """POST /api/v1/payments com dados válidos retorna 201"""
        response = client.post(
            "/api/v1/payments",
            {
                "amount": "297.00",
                "currency": "BRL",
                "payment_method": "card",
                "installments": 3,
                "splits": [
                    {"recipient_id": "p1", "role": "producer", "percent": 70},
                    {"recipient_id": "a1", "role": "affiliate", "percent": 30},
                ],
            },
            HTTP_IDEMPOTENCY_KEY="key123",
        )

        assert response.status_code == 201
        assert response.data["status"] == "captured"
        assert "receivables" in response.data
        assert len(response.data["receivables"]) == 2

    def test_idempotency_same_key_same_payload(self, client):
        """Mesma key + mesmo payload = retorna 200 com resultado anterior"""
        payload = {
            "amount": "100.00",
            "currency": "BRL",
            "payment_method": "pix",
            "installments": 1,
            "splits": [{"recipient_id": "p1", "role": "producer", "percent": 100}],
        }

        # First call
        response1 = client.post(
            "/api/v1/payments",
            payload,
            HTTP_IDEMPOTENCY_KEY="key_abc",
        )
        payment_id_1 = response1.data["payment_id"]

        # Second call - mesma key, mesmo payload
        response2 = client.post(
            "/api/v1/payments",
            payload,
            HTTP_IDEMPOTENCY_KEY="key_abc",
        )
        payment_id_2 = response2.data["payment_id"]

        # Mesma coisa retornada, nenhum pagamento duplicado
        assert response2.status_code == 200
        assert payment_id_2 == payment_id_1
        assert Payment.objects.count() == 1

    def test_idempotency_same_key_different_payload_returns_409(self, client):
        """Mesma key + payload diferente = retorna 409"""
        # First call
        client.post(
            "/api/v1/payments",
            {
                "amount": "100.00",
                "currency": "BRL",
                "payment_method": "pix",
                "installments": 1,
                "splits": [{"recipient_id": "p1", "role": "producer", "percent": 100}],
            },
            HTTP_IDEMPOTENCY_KEY="key_xyz",
        )

        # Second call - mesma key, OUTRO amount
        response = client.post(
            "/api/v1/payments",
            {
                "amount": "200.00",  # ← diferente
                "currency": "BRL",
                "payment_method": "pix",
                "installments": 1,
                "splits": [{"recipient_id": "p1", "role": "producer", "percent": 100}],
            },
            HTTP_IDEMPOTENCY_KEY="key_xyz",
        )

        assert response.status_code == 409
        assert "conflict" in response.data["error"].lower()
