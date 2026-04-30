from django import forms
from ticketing.models import Venue


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'address', 'city', 'capacity', 'has_reserved_seating']