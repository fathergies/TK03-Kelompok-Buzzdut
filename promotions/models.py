import uuid
from django.db import models

from orders.models import Order


class Promotion(models.Model):
    DISCOUNT_NOMINAL = "NOMINAL"
    DISCOUNT_PERCENTAGE = "PERCENTAGE"

    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_NOMINAL, "Nominal"),
        (DISCOUNT_PERCENTAGE, "Percentage"),
    ]

    promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    promo_code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.IntegerField(default=0)

    class Meta:
        db_table = "PROMOTION"
        ordering = ["-start_date"]

    def __str__(self):
        return self.promo_code

    @property
    def is_active(self):
        from django.utils import timezone

        today = timezone.localdate()
        return self.start_date <= today <= self.end_date


class OrderPromotion(models.Model):
    order_promotion_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        db_column="promotion_id",
        related_name="order_promotions",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_column="order_id",
        related_name="order_promotions",
    )

    class Meta:
        db_table = "ORDER_PROMOTION"
        unique_together = ("promotion", "order")

    def __str__(self):
        return f"{self.order_id} - {self.promotion_id}"