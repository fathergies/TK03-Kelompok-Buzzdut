import uuid
from django.db import models
from .ticket_category import Ticket_Category

class Ticket(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Aktif'
        USED = 'USED', 'Terpakai'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_code = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )

    tcategory = models.ForeignKey(
        Ticket_Category,
        on_delete=models.CASCADE,
        related_name='tickets'
    )

    torder_id = models.UUIDField()

    def __str__(self):
        return self.ticket_code

    class Meta:
        db_table = 'ticket'
