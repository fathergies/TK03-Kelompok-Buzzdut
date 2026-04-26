import uuid

from django.db import models

from .event import Event


class Artist(models.Model):
    """Represents an artist or performer."""

    artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=False, null=False)
    genre = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        db_table = 'artist'


class Event_Artist(models.Model):
    """Many-to-many junction table connecting Event and Artist, with role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='event_artists',
        db_column='event_id',
    )
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name='event_artists',
        db_column='artist_id',
    )
    role = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return f"{self.artist.name} @ {self.event.title} ({self.role})"

    class Meta:
        verbose_name = 'Event Artist'
        verbose_name_plural = 'Event Artists'
        unique_together = ('event', 'artist')
        db_table = 'event_artist'
