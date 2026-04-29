from django.db import models
import uuid

class Venue(models.Model):
    venue_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nama_venue = models.CharField(max_length=100)
    alamat = models.TextField()
    kota = models.CharField(max_length=100)
    kapasitas = models.PositiveIntegerField()
    has_reserved_seating = models.BooleanField(default=False)

    def __str__(self):
        return self.nama_venue

    @property
    def seating_label(self):
        return "Reserved Seating" if self.has_reserved_seating else "Free Seating"