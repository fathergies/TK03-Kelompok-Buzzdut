from django.db import models
from django.utils import timezone

class Promotion(models.Model):
    DISCOUNT_TYPE_CHOICES = [('Persentase', 'Persentase'), ('Nominal', 'Nominal')]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.IntegerField()
    current_usage = models.IntegerField(default=0)

    @property
    def is_active(self):
        today = timezone.localdate()
        return self.start_date <= today <= self.end_date and self.current_usage < self.usage_limit

    def __str__(self):
        return self.code
