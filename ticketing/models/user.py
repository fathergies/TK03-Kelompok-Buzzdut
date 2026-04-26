import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Custom User model with a role field for access control."""

    class RoleChoices(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        ORGANIZER = 'ORGANIZER', 'Organizer'
        CUSTOMER = 'CUSTOMER', 'Customer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.CUSTOMER,
    )
    phone_number = models.CharField(max_length=30, blank=True, default='')

    class Meta:
        db_table = 'custom_user'

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_admin(self):
        return self.role == self.RoleChoices.ADMIN

    @property
    def is_organizer(self):
        return self.role == self.RoleChoices.ORGANIZER

    @property
    def is_customer(self):
        return self.role == self.RoleChoices.CUSTOMER
