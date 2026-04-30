from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "order_date", "payment_status", "total_amount")
    list_filter = ("payment_status", "order_date")
    search_fields = ("id", "customer__username", "customer__email")