from django.contrib import admin
from .models import Promotion, OrderPromotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "promotion_id",
        "promo_code",
        "discount_type",
        "discount_value",
        "start_date",
        "end_date",
        "usage_limit",
    )
    list_filter = ("discount_type", "start_date", "end_date")
    search_fields = ("promo_code",)


@admin.register(OrderPromotion)
class OrderPromotionAdmin(admin.ModelAdmin):
    list_display = ("order_promotion_id", "order", "promotion")
    search_fields = ("order__order_id", "promotion__promo_code")