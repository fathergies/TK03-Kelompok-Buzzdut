from django import forms
from django.db import models

from .models import Artist, Ticket_Category


# =============================================================================
# CRUD Forms
# =============================================================================

class ArtistForm(forms.ModelForm):
    """Form for creating and editing Artists."""

    class Meta:
        model = Artist
        fields = ['name', 'genre']
        labels = {
            'name': 'Artist Name',
            'genre': 'Genre',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter artist name',
            }),
            'genre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Pop, Rock, Jazz',
            }),
        }


class TicketCategoryForm(forms.ModelForm):
    """
    Form for creating and editing Ticket Categories.
    Includes quota vs venue capacity validation.
    """

    class Meta:
        model = Ticket_Category
        fields = ['tevent', 'category_name', 'price', 'quota']
        labels = {
            'tevent': 'Event',
            'category_name': 'Category Name',
            'price': 'Price (IDR)',
            'quota': 'Quota',
        }
        widgets = {
            'tevent': forms.Select(attrs={'class': 'form-control'}),
            'category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. VIP, Regular, Student',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'min': '0',
                'step': '0.01',
            }),
            'quota': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Number of tickets',
                'min': '1',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        event = cleaned_data.get('tevent')
        quota = cleaned_data.get('quota')

        if not event or not quota:
            return cleaned_data

        venue_capacity = event.venue.capacity
        existing_quota = (
            Ticket_Category.objects
            .filter(tevent=event)
            .exclude(pk=self.instance.pk)
            .aggregate(total=models.Sum('quota'))['total']
            or 0
        )
        total_quota = existing_quota + quota

        if total_quota > venue_capacity:
            remaining = venue_capacity - existing_quota
            raise forms.ValidationError(
                f"Total quota ({total_quota}) exceeds venue capacity "
                f"({venue_capacity}). Remaining available: {remaining}."
            )

        return cleaned_data
