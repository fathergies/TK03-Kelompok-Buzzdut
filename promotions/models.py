from django.utils import timezone 

from django.db import models
from django.core.validators import MinValueValidator


class Promotion(models.Model):
    DISCOUNT_PERCENTAGE = "percentage"
    DISCOUNT_NOMINAL = "nominal"

    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_PERCENTAGE, "Persentase"),
        (DISCOUNT_NOMINAL, "Nominal"),
    ]

    promo_code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES
    )
    discount_value = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    used_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.promo_code
    

class OrderPromotion(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="order_promotions"
    )
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="order_promotions"
    )
    used_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("order", "promotion")

    def __str__(self):
        return f"{self.order} - {self.promotion.promo_code}"