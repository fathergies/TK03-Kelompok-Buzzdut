import uuid

from django.db import models

from .event import Event


class Artist(models.Model):
    """Represents an artist or performer."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    genre = models.CharField(max_length=100, blank=True, default='')
    phonenumber = models.CharField(max_length=30, blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Event_Artist(models.Model):
    """Many-to-many junction table connecting Event and Artist."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='event_artists',
    )
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name='event_artists',
    )

    def __str__(self):
        return f"{self.artist.name} @ {self.event.title}"

    class Meta:
        verbose_name = 'Event Artist'
        verbose_name_plural = 'Event Artists'
        unique_together = ('event', 'artist')
