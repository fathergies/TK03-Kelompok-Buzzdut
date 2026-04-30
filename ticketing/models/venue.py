import uuid

from django.core.validators import MinValueValidator
from django.db import models


class Venue(models.Model):
    """Represents a physical venue where events take place."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    capacity = models.IntegerField(
        validators=[MinValueValidator(1, message="Capacity must be greater than 0.")]
    )
    address = models.TextField()
    city = models.CharField(max_length=255)
    has_reserved_seating = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def seating_label(self):
        return "Reserved Seating" if self.has_reserved_seating else "Free Seating"

    class Meta:
        ordering = ['name']
        db_table = 'venue'