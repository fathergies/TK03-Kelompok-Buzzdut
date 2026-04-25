import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


# =============================================================================
# Core Models
# =============================================================================

class Venue(models.Model):
    """Represents a physical venue where events take place."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    capacity = models.IntegerField(
        validators=[MinValueValidator(1, message="Capacity must be greater than 0.")]
    )
    address = models.TextField()
    city = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.city})"

    class Meta:
        ordering = ['name']


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


# =============================================================================
# Green Module Models
# =============================================================================

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


class Ticket_Category(models.Model):
    """
    Represents a ticket category for an event.

    Business Rule: The sum of quota across all Ticket_Category entries for the
    same Event must not exceed the capacity of the Event's Venue.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='ticket_categories',
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0, message="Price must be >= 0.")],
    )
    quota = models.IntegerField(
        validators=[MinValueValidator(1, message="Quota must be greater than 0.")]
    )

    def clean(self):
        """
        Validate that the total quota of all ticket categories for this event
        does not exceed the venue capacity.

        On UPDATE: excludes the current instance from the aggregate to avoid
        double-counting its own quota.
        On CREATE (no pk saved yet): sums all existing categories for the event.
        """
        super().clean()

        if not self.event_id:
            return  # Cannot validate without an associated event

        venue_capacity = self.event.venue.capacity

        # Sum existing quotas for the same event, excluding this instance
        # (important when updating an existing Ticket_Category)
        existing_quota = (
            Ticket_Category.objects
            .filter(event=self.event)
            .exclude(pk=self.pk)
            .aggregate(total=models.Sum('quota'))['total']
            or 0
        )

        total_quota = existing_quota + (self.quota or 0)

        if total_quota > venue_capacity:
            raise ValidationError({
                'quota': (
                    f"Total quota ({total_quota}) exceeds the venue capacity "
                    f"({venue_capacity}). Available remaining quota: "
                    f"{venue_capacity - existing_quota}."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event.title} - {self.name} (${self.price})"

    class Meta:
        verbose_name = 'Ticket Category'
        verbose_name_plural = 'Ticket Categories'
        ordering = ['event__title', 'name']
