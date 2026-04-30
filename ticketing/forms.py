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


from ticketing.models.event import Event

class TicketCategoryForm(forms.ModelForm):
    tevent = forms.ModelChoiceField(
        queryset=Event.objects.filter(status='Scheduled'),
        required=True,
        empty_label='Pilih Event',
        label='Acara',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white',
        })
    )
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
            'category_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white',
                'placeholder': 'cth. WVIP',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white',
                'placeholder': '0',
                'min': '0',
                'step': '1',
            }),
            'quota': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white',
                'placeholder': '100',
                'min': '1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure queryset is up-to-date
        self.fields['tevent'].queryset = Event.objects.filter(status='Scheduled')
        self.fields['tevent'].empty_label = 'Pilih Event'

    def clean(self):
        cleaned_data = super().clean()
        event = cleaned_data.get('tevent')
        quota = cleaned_data.get('quota')
        price = cleaned_data.get('price')
        if price is not None and price < 0:
            self.add_error('price', "Price cannot be negative.")
        if quota is not None and quota <= 0:
            self.add_error('quota', "Quota must be a positive integer.")
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
                f"Total quota ({total_quota}) exceeds venue capacity ({venue_capacity}). Remaining available: {remaining}."
            )
        return cleaned_data
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
            'category_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white',
                'placeholder': 'cth. WVIP',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white',
                'placeholder': '0',
                'min': '0',
                'step': '1',
            }),
            'quota': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white',
                'placeholder': '100',
                'min': '1',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate event dropdown with all available events
        from ticketing.models.event import Event
        self.fields['tevent'].queryset = Event.objects.all()
        self.fields['tevent'].empty_label = 'Pilih Event'

    def clean(self):
        cleaned_data = super().clean()
        event = cleaned_data.get('tevent')
        quota = cleaned_data.get('quota')
        price = cleaned_data.get('price')

        if price is not None and price < 0:
            self.add_error('price', "Price cannot be negative.")

        if quota is not None and quota <= 0:
            self.add_error('quota', "Quota must be a positive integer.")

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
