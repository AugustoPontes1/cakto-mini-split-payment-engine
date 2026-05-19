from decimal import Decimal

from django.test import TestCase

from app.services.split_calculator import SplitCalculator


class TestSplitCalculatorValidation(TestCase):
    """Testes de validação de entrada"""

    def test_negative_amount_rejected(self):
        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal("-100.00"),
            payment_method="pix",
            installments=1,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}],
        )
        self.assertFalse(is_valid)
        self.assertIn("amount must be > 0", error)

    def test_pix_rejects_installments(self):
        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal("100.00"),
            payment_method="pix",
            installments=2,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}],
        )
        self.assertFalse(is_valid)
        self.assertIn("pix does not support installments", error)

    def test_splits_must_sum_100(self):
        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal("100.00"),
            payment_method="card",
            installments=1,
            splits=[
                {"recipient_id": "p1", "role": "producer", "percent": 60},
                {"recipient_id": "a1", "role": "affiliate", "percent": 35},
            ],
        )
        self.assertFalse(is_valid)
        self.assertIn("sum to 100", error)


class TestSplitCalculatorPrecision(TestCase):
    """Testes de precisão de centavos"""

    def test_pix_zero_fee_100_percent_split(self):
        """PIX com taxa zero, split 100%, soma bate certinho"""
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("100.00"),
            payment_method="pix",
            installments=1,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}],
        )

        self.assertEqual(result["platform_fee_amount"], Decimal("0.00"))
        self.assertEqual(result["net_amount"], Decimal("100.00"))
        self.assertEqual(result["receivables"][0]["amount"], Decimal("100.00"))
        self.assertEqual(sum(r["amount"] for r in result["receivables"]), result["net_amount"])

    def test_card_3x_70_30_split(self):
        """CARD 3x, split 70/30, soma receivables = net"""
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("297.00"),
            payment_method="card",
            installments=3,
            splits=[
                {"recipient_id": "producer_1", "role": "producer", "percent": 70},
                {"recipient_id": "affiliate_9", "role": "affiliate", "percent": 30},
            ],
        )

        self.assertEqual(result["platform_fee_amount"], Decimal("26.70"))
        self.assertEqual(sum(r["amount"] for r in result["receivables"]), result["net_amount"])

    def test_rounding_one_cent_remainder(self):
        """Caso onde sobra 0.01 ao distribuir - deve absorver no primeiro"""
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("100.00"),
            payment_method="pix",
            installments=1,
            splits=[
                {"recipient_id": "p1", "role": "producer", "percent": 33.33},
                {"recipient_id": "p2", "role": "producer", "percent": 33.33},
                {"recipient_id": "p3", "role": "producer", "percent": 33.34},
            ],
        )

        total = sum(r["amount"] for r in result["receivables"])
        self.assertEqual(total, result["net_amount"])
        self.assertEqual(total, Decimal("100.00"))
