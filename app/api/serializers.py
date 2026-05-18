from rest_framework import serializers
from decimal import Decimal


class SplitItemSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=100)
    role = serializers.CharField(max_length=50)
    percent = serializers.DecimalField(max_digits=5, decimal_places=2)


class PaymentRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=19, decimal_places=2)
    currency = serializers.CharField(default="BRL", max_length=3)
    payment_method = serializers.ChoiceField(choices=["pix", "card"])
    installments = serializers.IntegerField(default=1)
    splits = SplitItemSerializer(many=True)
    
    def validate(self, data):
        """Validação de negócio após formato validado"""
        from app.services.split_calculator import SplitCalculator
        
        is_valid, error = SplitCalculator.validate_input(
            amount=Decimal(str(data["amount"])),
            payment_method=data["payment_method"],
            installments=data["installments"],
            splits=data["splits"]
        )

        if not is_valid:
            raise serializers.ValidationError(error)

        return data
