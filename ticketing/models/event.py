import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .venue import Venue


class Event(models.Model):
    """Represents an event organized at a venue."""

    class CategoryChoices(models.TextChoices):
        MUSIC = 'Music', 'Music'
        SPORTS = 'Sports', 'Sports'
        THEATER = 'Theater', 'Theater'
        CONFERENCE = 'Conference', 'Conference'
        FESTIVAL = 'Festival', 'Festival'
        OTHER = 'Other', 'Other'

    class StatusChoices(models.TextChoices):
        SCHEDULED = 'Scheduled', 'Scheduled'
        ONGOING = 'Ongoing', 'Ongoing'
        FINISHED = 'Finished', 'Finished'
        CANCELED = 'Canceled', 'Canceled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name='events',
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category = models.CharField(
        max_length=50,
        choices=CategoryChoices.choices,
        default=CategoryChoices.OTHER,
    )
    status = models.CharField(
        max_length=50,
        choices=StatusChoices.choices,
        default=StatusChoices.SCHEDULED,
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def clean(self):
        """Validate that end_date is after start_date."""
        super().clean()
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError({
                'end_date': "End date must be after start date."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.status})"

    class Meta:
        ordering = ['start_date']
