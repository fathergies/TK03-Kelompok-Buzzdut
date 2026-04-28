import uuid
from django.db import models
from .seat import Seat
from .ticket import Ticket

class HasRelationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name='seat_ticket'
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='seat_ticket'
    )

    def __str__(self):
        return f"{self.seat} -> {self.ticket}"

    class Meta:
        db_table = 'has_relationship'
        unique_together = ('seat', 'ticket')