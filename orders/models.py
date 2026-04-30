import uuid
from django.db import models
from django.contrib.auth.models import User
from basdat_tk03 import settings
from promotions.models import Promotion

class Order(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Lunas', 'Lunas'), ('Dibatalkan', 'Dibatalkan')]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Promotion link
    promotion = models.ForeignKey(Promotion, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.id}"
    