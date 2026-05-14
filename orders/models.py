import uuid
from django.db import models
from django.conf import settings 

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Lunas'),
        ('CANCELLED', 'Dibatalkan'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.id)