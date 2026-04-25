import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from .event import Event


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
