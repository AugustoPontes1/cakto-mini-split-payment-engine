import json
from uuid import uuid4

from django.db import transaction

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.api.models import LedgerEntry, OutboxEvent, Payment
from app.api.serializers import PaymentRequestSerializer
from app.services.split_calculator import SplitCalculator


class PaymentCreateView(APIView):
    """
    POST /api/v1/payments

    Flow:
    1. Validate input (serializer)
    2. Check idempotency (return 409 if conflict)
    3. Calculate split (via SplitCalculator)
    4. Persist Payment
    5. Persist LedgerEntries
    6. Register OutboxEvent
    7. Return response
    """

    def post(self, request):
        # Step 1: Validate input
        serializer = PaymentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Idempotency check
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response({"error": "Idempotency-Key header is required"}, status=status.HTTP_400_BAD_REQUEST)

        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()

        if existing:
            # Same key + same payload = return previous result
            if self._payloads_match(request.data, existing.payload):
                return Response(existing.to_dict(), status=status.HTTP_200_OK)
            else:
                # Same key + different payload = CONFLICT
                return Response(
                    {"error": "Idempotency conflict: same key, different payload"}, status=status.HTTP_409_CONFLICT
                )

        # Step 3: Calculate split
        calc_result = SplitCalculator.calculate_with_precision(
            gross_amount=serializer.validated_data["amount"],
            payment_method=serializer.validated_data["payment_method"],
            installments=serializer.validated_data["installments"],
            splits=serializer.validated_data["splits"],
        )

        # Step 4-6: Persist in transaction
        with transaction.atomic():
            payment = Payment.objects.create(
                payment_id=f"pmt_{uuid4()}",
                status="captured",
                gross_amount=calc_result["gross_amount"],
                platform_fee_amount=calc_result["platform_fee_amount"],
                net_amount=calc_result["net_amount"],
                payment_method=serializer.validated_data["payment_method"],
                installments=serializer.validated_data["installments"],
                idempotency_key=idempotency_key,
                payload=request.data,  # Store original payload
            )

            # Register ledger entries
            for receivable in calc_result["receivables"]:
                LedgerEntry.objects.create(
                    payment=payment,
                    recipient_id=receivable["recipient_id"],
                    role=receivable["role"],
                    amount=receivable["amount"],
                )

            # Register audit event
            payload = {
                "gross_amount": str(calc_result["gross_amount"]),
                "platform_fee_amount": str(calc_result["platform_fee_amount"]),
                "platform_fee_percent": str(calc_result["platform_fee_percent"]),
                "net_amount": str(calc_result["net_amount"]),
                "receivables": [
                    {
                        **r,
                        "percent": str(r["percent"]),
                        "amount": str(r["amount"]),
                        "rounding_adjustment": str(r["rounding_adjustment"]),
                    }
                    for r in calc_result["receivables"]
                ],
            }
            OutboxEvent.objects.create(
                payment=payment,
                type="payment_captured",
                payload=payload,
                status="pending",
            )

        # Step 7: Return response
        return Response(payment.to_dict(), status=status.HTTP_201_CREATED)

    def _payloads_match(self, payload1, payload2):
        # Semantic comparison (not exact due to Decimal types)
        return json.dumps(payload1, sort_keys=True) == json.dumps(payload2, sort_keys=True)
