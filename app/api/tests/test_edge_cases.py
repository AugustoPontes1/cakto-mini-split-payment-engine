from decimal import Decimal

from django.test import TestCase

from app.services.split_calculator import SplitCalculator


class TestEdgeCases(TestCase):

    def test_minimum_amount(self):
        """Amount mínimo: 0.01"""
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("0.01"),
            payment_method="pix",
            installments=1,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}],
        )
        self.assertEqual(result["net_amount"], Decimal("0.01"))

    def test_maximum_installments(self):
        """CARD com 12x parcelas"""
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("1000.00"),
            payment_method="card",
            installments=12,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}],
        )

        expected_fee_percent = Decimal("25.99")
        self.assertEqual(result["platform_fee_percent"], expected_fee_percent)

    def test_five_recipients_max(self):
        """Máximo 5 recebedores"""
        splits = [{"recipient_id": f"r{i}", "role": "producer", "percent": Decimal(str(20.00))} for i in range(5)]

        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("100.00"), payment_method="pix", installments=1, splits=splits
        )

        self.assertEqual(len(result["receivables"]), 5)

    def test_six_recipients_rejected(self):
        """Mais de 5 recebedores é rejeitado"""
        splits = [{"recipient_id": f"r{i}", "role": "producer", "percent": Decimal(str(100 / 6))} for i in range(6)]

        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal("100.00"), payment_method="pix", installments=1, splits=splits
        )

        self.assertFalse(is_valid)
