from django.db import models


class Payment(models.Model):
    STATUS_CHOICES = [("captured", "Captured")]

    payment_id = models.CharField(max_length=50, unique=True)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    gross_amount = models.DecimalField(max_digits=19, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=19, decimal_places=2)
    net_amount = models.DecimalField(max_digits=19, decimal_places=2)

    payment_method = models.CharField(max_length=20)  # pix, card
    installments = models.IntegerField(default=1)

    payload = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["idempotency_key", "created_at"])]

    def to_dict(self):
        return {
            "payment_id": self.payment_id,
            "status": self.status,
            "gross_amount": str(self.gross_amount),
            "platform_fee_amount": str(self.platform_fee_amount),
            "net_amount": str(self.net_amount),
            "receivables": list(self.ledgerentries.values("recipient_id", "role", "amount")),
            "outbox_event": {
                "type": self.outboxevents.first().type,
                "status": self.outboxevents.first().status,
            },
            "created_at": self.created_at.isoformat(),
        }


class LedgerEntry(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="ledgerentries")
    recipient_id = models.CharField(max_length=100)
    role = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class OutboxEvent(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("published", "Published"),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="outboxevents")
    type = models.CharField(max_length=50)  # payment_captured
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
