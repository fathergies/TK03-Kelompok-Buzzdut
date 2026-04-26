from django import forms
from .models import Venue

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['nama_venue', 'alamat', 'kota', 'kapasitas']