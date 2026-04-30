from django.contrib import admin
from .models import Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        "promo_code",
        "discount_type",
        "discount_value",
        "start_date",
        "end_date",
        "used_count",
        "usage_limit",
    ]
    search_fields = ["promo_code"]
    list_filter = ["discount_type", "start_date", "end_date"]