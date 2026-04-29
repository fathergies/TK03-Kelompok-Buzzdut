import uuid
from django.db import models
from .venue import Venue

class Seat(models.Model):
    seat_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.CharField(max_length=50)
    row_number = models.CharField(max_length=10)
    seat_number = models.CharField(max_length=10)

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name='seats'
    )

    def __str__(self):
        return f"{self.section} - Row {self.row_number} Seat {self.seat_number}"

    class Meta:
        db_table = 'seat'