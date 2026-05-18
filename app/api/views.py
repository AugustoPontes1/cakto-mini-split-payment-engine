from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.db import transaction

from uuid import uuid4
import json

from app.api.serializers import PaymentRequestSerializer
from app.services.split_calculator import SplitCalculator
from app.api.models import Payment, LedgerEntry, OutboxEvent


class PaymentCreateView(APIView):
    """
    POST /api/v1/payments
    
    Fluxo:
    1. Validar entrada (serializer)
    2. Verificar idempotency (retorna 409 se conflito)
    3. Calcular split (via SplitCalculator)
    4. Persistir Payment
    5. Persistir LedgerEntries
    6. Registrar OutboxEvent
    7. Retornar response
    """
    
    def post(self, request):
        # Step 1: Validar
        serializer = PaymentRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Step 2: Idempotência
        idempotency_key = request.headers.get("Idempotency-Key")
        
        existing = Payment.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        
        if existing:
            # Mesma key + mesmo payload = retornar result anterior
            if self._payloads_match(request.data, existing.payload):
                return Response(existing.to_dict(), status=status.HTTP_200_OK)
            else:
                # Mesma key + payload diferente = CONFLITO
                return Response(
                    {"error": "Idempotency conflict: same key, different payload"},
                    status=status.HTTP_409_CONFLICT
                )

        # Step 3: Calcular
        calc_result = SplitCalculator.calculate_with_precision(
            gross_amount=serializer.validated_data["amount"],
            payment_method=serializer.validated_data["payment_method"],
            installments=serializer.validated_data["installments"],
            splits=serializer.validated_data["splits"]
        )

        # Step 4-6: Persistir em transação
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
                payload=request.data,  # Guardar payload original
            )

            # Registrar ledger
            for receivable in calc_result["receivables"]:
                LedgerEntry.objects.create(
                    payment=payment,
                    recipient_id=receivable["recipient_id"],
                    role=receivable["role"],
                    amount=receivable["amount"],
                )

            # Registrar evento de auditoria
            OutboxEvent.objects.create(
                payment=payment,
                type="payment_captured",
                payload=calc_result,  # JSON com cálculo completo
                status="pending",
            )

        # Step 7: Retornar
        return Response(payment.to_dict(), status=status.HTTP_201_CREATED)

    def _payloads_match(self, payload1, payload2):
        # Comparar semanticamente (não exato, pois Decimal etc)
        return json.dumps(payload1, sort_keys=True) == \
               json.dumps(payload2, sort_keys=True)
