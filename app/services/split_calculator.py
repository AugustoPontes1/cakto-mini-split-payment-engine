from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Any


class SplitCalculator:
    """
    Motor de cálculo de split: precisão de centavos garantida.
    Invariante: sum(receivables) == net_amount (sempre, sem exceção)
    """
    
    # Constantes
    PAYMENT_FEES = {
        "pix": Decimal("0.00"),
        "card": None,  # Depende de installments
    }
    
    BASE_CARD_FEE = Decimal("3.99")      # 3.99%
    INSTALLMENT_FEE = Decimal("2.00")    # 2.00% por parcela extra
    
    @staticmethod
    def validate_input(
        amount: Decimal,
        payment_method: str,
        installments: int,
        splits: List[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """
        Valida entrada em nível de negócio.
        
        Retorna: (is_valid, error_message)
        """
        # Validação 1: amount > 0
        if amount <= 0:
            return False, "amount must be > 0"
        
        # Validação 2: payment_method válido
        if payment_method not in ["pix", "card"]:
            return False, f"unknown payment_method: {payment_method}"
        
        # Validação 3: PIX não aceita installments
        if payment_method == "pix" and installments != 1:
            return False, "pix does not support installments"
        
        # Validação 4: CARD aceita 1-12
        if payment_method == "card" and not (1 <= installments <= 12):
            return False, "card installments must be 1-12"
        
        # Validação 5: splits deve ter 1-5 recebedores
        if not (1 <= len(splits) <= 5):
            return False, "splits must have 1-5 recipients"
        
        # Validação 6: percentuais devem somar 100
        total_percent = sum(Decimal(s["percent"]) for s in splits)
        if total_percent != Decimal("100"):
            return False, f"splits percentages must sum to 100, got {total_percent}"
        
        # Validação 7: cada percentual > 0 e <= 100
        for s in splits:
            pct = Decimal(s["percent"])
            if not (0 < pct <= 100):
                return False, f"each percent must be 0 < x <= 100, got {pct}"
        
        return True, ""
    
    @staticmethod
    def calculate_fee_percent(payment_method: str, installments: int) -> Decimal:
        """
        Calcula percentual de taxa baseado no método e parcelamento.
        
        Exemplos:
        - PIX: 0%
        - CARD 1x: 3.99%
        - CARD 2x: 3.99% + 2% = 5.99%
        - CARD 3x: 3.99% + 4% = 7.99%
        - CARD 12x: 3.99% + 22% = 26.99%
        """
        if payment_method == "pix":
            return Decimal("0.00")
        
        if payment_method == "card":
            base = Decimal("3.99")
            extra_installments = installments - 1
            extra_fee = extra_installments * Decimal("2.00")
            return base + extra_fee
        
        raise ValueError(f"Unknown payment_method: {payment_method}")
    
    @staticmethod
    def calculate_with_precision(
        gross_amount: Decimal,
        payment_method: str,
        installments: int,
        splits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calcula split com garantia de precisão de centavos.
        
        Estratégia de arredondamento:
        - Cada recebedor recebe floor(seu percentual do net)
        - O PRIMEIRO recebedor absorve centavos restantes
        
        Isso garante: sum(receivables) == net_amount
        
        Retorna:
        {
            "gross_amount": Decimal,
            "platform_fee_amount": Decimal,
            "platform_fee_percent": Decimal,
            "net_amount": Decimal,
            "receivables": [
                {
                    "recipient_id": str,
                    "role": str,
                    "percent": Decimal,
                    "amount": Decimal,
                    "rounding_adjustment": Decimal,  # Documentar se houve ajuste
                },
                ...
            ]
        }
        """

        # Step 1: Calcular taxa
        fee_percent = SplitCalculator.calculate_fee_percent(
            payment_method, installments
        )
        fee_amount = (gross_amount * fee_percent / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        net_amount = gross_amount - fee_amount

        # Step 2: Distribuir net entre recebedores
        receivables = []
        accumulated = Decimal("0.00")
        
        for idx, split in enumerate(splits):
            percent = Decimal(split["percent"])
            
            if idx < len(splits) - 1:
                # Para todos EXCETO o último: usar floor
                amount = (net_amount * percent / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_DOWN
                )
            else:
                # Último recebedor: absorve tudo que sobrou
                amount = net_amount - accumulated
            
            rounding_adj = amount - (
                (net_amount * percent / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_DOWN
                )
            ) if idx < len(splits) - 1 else Decimal("0.00")
            
            receivables.append({
                "recipient_id": split["recipient_id"],
                "role": split["role"],
                "percent": percent,
                "amount": amount,
                "rounding_adjustment": rounding_adj,
            })
            accumulated += amount
        
        # Step 3: Validar invariante
        assert sum(r["amount"] for r in receivables) == net_amount, \
            f"Invariant broken: sum={sum(r['amount'] for r in receivables)}, expected={net_amount}"
        
        return {
            "gross_amount": gross_amount,
            "platform_fee_amount": fee_amount,
            "platform_fee_percent": fee_percent,
            "net_amount": net_amount,
            "receivables": receivables,
        }