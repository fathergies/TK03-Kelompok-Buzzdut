from django import forms
from ticketing.models import Event, Venue, Artist

class EventForm(forms.ModelForm):
    start_datetime = forms.DateTimeField(
        label='TANGGAL & WAKTU (DATE & TIME)',
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
        })
    )
    
    artists = forms.ModelMultipleChoiceField(
        queryset=Artist.objects.all().order_by('name'),
        label='ARTIS (EVENT_ARTIST)',
        help_text='Tahan tombol Ctrl (Windows) atau Command (Mac) untuk memilih lebih dari satu artis.',
        widget=forms.SelectMultiple(attrs={
            'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white h-32'
        })
    )

    class Meta:
        model = Event
        fields = ['title', 'venue', 'description']
        labels = {
            'title': 'JUDUL ACARA (EVENT_TITLE)',
            'venue': 'VENUE (VENUE_ID)',
            'description': 'DESKRIPSI',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white',
                'placeholder': 'cth. Konser Melodi Senja'
            }),
            'venue': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white',
                'placeholder': 'Deskripsi acara...',
                'rows': 4
            })
        }
