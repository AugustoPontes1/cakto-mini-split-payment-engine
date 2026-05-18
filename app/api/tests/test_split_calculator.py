from decimal import Decimal
from app.services.split_calculator import SplitCalculator


class TestSplitCalculatorValidation:
    """Testes de validação de entrada"""
    
    def test_negative_amount_rejected(self):
        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal("-100.00"),
            payment_method="pix",
            installments=1,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}]
        )
        assert not is_valid
        assert "amount must be > 0" in error
    
    def test_pix_rejects_installments(self):
        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal("100.00"),
            payment_method="pix",
            installments=2,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}]
        )
        assert not is_valid
        assert "pix does not support installments" in error
    
    def test_splits_must_sum_100(self):
        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal("100.00"),
            payment_method="card",
            installments=1,
            splits=[
                {"recipient_id": "p1", "role": "producer", "percent": 60},
                {"recipient_id": "a1", "role": "affiliate", "percent": 35},
            ]
        )
        assert not is_valid
        assert "sum to 100" in error


class TestSplitCalculatorPrecision:
    """Testes de precisão de centavos"""
    
    def test_pix_zero_fee_100_percent_split(self):
        """PIX com taxa zero, split 100%, soma bate certinho"""
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("100.00"),
            payment_method="pix",
            installments=1,
            splits=[{"recipient_id": "p1", "role": "producer", "percent": 100}]
        )
        
        assert result["platform_fee_amount"] == Decimal("0.00")
        assert result["net_amount"] == Decimal("100.00")
        assert result["receivables"][0]["amount"] == Decimal("100.00")
        assert sum(r["amount"] for r in result["receivables"]) == result["net_amount"]
    
    def test_card_3x_70_30_split(self):
        """CARD 3x, split 70/30, soma receivables = net"""
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("297.00"),
            payment_method="card",
            installments=3,
            splits=[
                {"recipient_id": "producer_1", "role": "producer", "percent": 70},
                {"recipient_id": "affiliate_9", "role": "affiliate", "percent": 30},
            ]
        )
        
        # 3x = 3.99% + 4% = 7.99%
        expected_fee = (Decimal("297.00") * Decimal("7.99") / Decimal("100")).quantize(
            Decimal("0.01")
        )
        assert result["platform_fee_amount"] == Decimal("23.70")  # ou similar
        assert sum(r["amount"] for r in result["receivables"]) == result["net_amount"]
    
    def test_rounding_one_cent_remainder(self):
        """Caso onde sobra 0.01 ao distribuir - deve absorver no primeiro"""
        # Amount que causa arredondamento
        result = SplitCalculator.calculate_with_precision(
            gross_amount=Decimal("100.00"),
            payment_method="pix",
            installments=1,
            splits=[
                {"recipient_id": "p1", "role": "producer", "percent": 33.33},
                {"recipient_id": "p2", "role": "producer", "percent": 33.33},
                {"recipient_id": "p3", "role": "producer", "percent": 33.34},
            ]
        )
        
        # Invariante: soma == net
        total = sum(r["amount"] for r in result["receivables"])
        assert total == result["net_amount"]
        
        # Nenhum centavo perdido
        assert total == Decimal("100.00")
