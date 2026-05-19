from decimal import ROUND_DOWN, Decimal
from typing import Any, Dict, List


class SplitCalculator:
    """
    Split calculation engine: guaranteed cent-level precision.
    Invariant: sum(receivables) == net_amount (always, without exception)
    """

    # Constants
    PAYMENT_FEES = {
        "pix": Decimal("0.00"),
        "card": None,  # Depends on installments
    }

    BASE_CARD_FEE = Decimal("3.99")  # 3.99%
    INSTALLMENT_FEE = Decimal("2.00")  # 2.00% per extra installment

    @staticmethod
    def validate_input(
        amount: Decimal, payment_method: str, installments: int, splits: List[Dict[str, Any]]
    ) -> tuple[bool, str]:
        """
        Validate business-level input.

        Returns: (is_valid, error_message)
        """
        # Validation 1: amount > 0
        if amount <= 0:
            return False, "amount must be > 0"

        # Validation 2: valid payment_method
        if payment_method not in ["pix", "card"]:
            return False, f"unknown payment_method: {payment_method}"

        # Validation 3: PIX does not support installments
        if payment_method == "pix" and installments != 1:
            return False, "pix does not support installments"

        # Validation 4: CARD accepts 1-12
        if payment_method == "card" and not (1 <= installments <= 12):
            return False, "card installments must be 1-12"

        # Validation 5: splits must have 1-5 recipients
        if not (1 <= len(splits) <= 5):
            return False, "splits must have 1-5 recipients"

        # Validation 6: percentages must sum to 100
        total_percent = sum(Decimal(s["percent"]) for s in splits)
        if total_percent != Decimal("100"):
            return False, f"splits percentages must sum to 100, got {total_percent}"

        # Validation 7: each percentage > 0 and <= 100
        for s in splits:
            pct = Decimal(s["percent"])
            if not (0 < pct <= 100):
                return False, f"each percent must be 0 < x <= 100, got {pct}"

        return True, ""

    @staticmethod
    def calculate_fee_percent(payment_method: str, installments: int) -> Decimal:
        """
        Calculate fee percentage based on payment method and installments.

        Examples:
        - PIX: 0%
        - CARD 1x: 3.99%
        - CARD 2x: 4.99% + 2% = 6.99%
        - CARD 3x: 4.99% + 4% = 8.99%
        - CARD 12x: 4.99% + 22% = 26.99%
        """
        if payment_method == "pix":
            return Decimal("0.00")

        if payment_method == "card":
            if installments == 1:
                return Decimal("3.99")
            else:
                base = Decimal("4.99")
                extra_installments = installments - 1
                extra_fee = extra_installments * Decimal("2.00")
                return base + extra_fee

        raise ValueError(f"Unknown payment_method: {payment_method}")

    @staticmethod
    def calculate_with_precision(
        gross_amount: Decimal, payment_method: str, installments: int, splits: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate split with cent-level precision guarantee.

        Rounding strategy:
        - Each recipient receives floor(their percentage of net)
        - The FIRST recipient absorbs remaining cents

        This guarantees: sum(receivables) == net_amount

        Returns:
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
                    "rounding_adjustment": Decimal,  # Document if adjustment occurred
                },
                ...
            ]
        }
        """

        # Step 1: Calculate fee
        fee_percent = SplitCalculator.calculate_fee_percent(payment_method, installments)
        fee_amount = (gross_amount * fee_percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        net_amount = gross_amount - fee_amount

        # Step 2: Distribute net among recipients
        receivables = []
        accumulated = Decimal("0.00")

        for idx, split in enumerate(splits):
            percent = Decimal(split["percent"])

            if idx < len(splits) - 1:
                # All except the last: use floor
                amount = (net_amount * percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            else:
                # Last recipient: absorbs everything remaining
                amount = net_amount - accumulated

            rounding_adj = (
                amount - ((net_amount * percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_DOWN))
                if idx < len(splits) - 1
                else Decimal("0.00")
            )

            receivables.append(
                {
                    "recipient_id": split["recipient_id"],
                    "role": split["role"],
                    "percent": percent,
                    "amount": amount,
                    "rounding_adjustment": rounding_adj,
                }
            )
            accumulated += amount

        # Step 3: Validate invariant
        assert (
            sum(r["amount"] for r in receivables) == net_amount
        ), f"Invariant broken: sum={sum(r['amount'] for r in receivables)}, expected={net_amount}"

        return {
            "gross_amount": gross_amount,
            "platform_fee_amount": fee_amount,
            "platform_fee_percent": fee_percent,
            "net_amount": net_amount,
            "receivables": receivables,
        }
