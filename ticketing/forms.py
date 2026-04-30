from django import forms
from django.db import models

from .models import Artist, Event, Event_Artist, HasRelationship, Seat, Ticket, Ticket_Category, Venue


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
            'tevent': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white'
            }),
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

class EventForm(forms.ModelForm):
    artist = forms.CharField(required=True)

    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'status', 'start_date', 'end_date', 'venue']
        labels = {
            'title': 'Judul Acara',
            'description': 'Deskripsi',
            'category': 'Kategori',
            'status': 'Status',
            'start_date': 'Tanggal & Waktu Mulai',
            'end_date': 'Tanggal & Waktu Selesai',
            'venue': 'Venue',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white',
                'placeholder': 'cth. Konser Melodi Senja',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white',
                'rows': 3,
                'placeholder': 'Deskripsi singkat acara',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white',
            }),
            'end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white',
            }),
            'venue': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.organizer = kwargs.pop('organizer', None)
        super().__init__(*args, **kwargs)

        self.fields['venue'].queryset = Venue.objects.all().order_by('name')

        if self.instance and self.instance.pk:
            event_artist = self.instance.event_artists.select_related('artist').first()
            if event_artist:
                self.fields['artist'].initial = str(event_artist.artist.artist_id)

            if self.instance.start_date:
                self.fields['start_date'].initial = self.instance.start_date.strftime('%Y-%m-%dT%H:%M')
            if self.instance.end_date:
                self.fields['end_date'].initial = self.instance.end_date.strftime('%Y-%m-%dT%H:%M')

    def clean_artist(self):
        artist_id = self.cleaned_data.get('artist')

        try:
            return Artist.objects.get(artist_id=artist_id)
        except Artist.DoesNotExist:
            raise forms.ValidationError('Artist tidak valid atau tidak ditemukan.')

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError('Tanggal selesai harus setelah tanggal mulai.')

        return cleaned_data

    def save(self, commit=True):
        event = super().save(commit=False)

        if not event.pk and self.organizer:
            event.organizer = self.organizer

        if commit:
            event.save()

            artist = self.cleaned_data.get('artist')
            if artist:
                Event_Artist.objects.filter(event=event).delete()
                Event_Artist.objects.create(
                    event=event,
                    artist=artist,
                    role='Main Performer'
                )

        return event
    
class SeatForm(forms.ModelForm):
    """Form for creating and editing venue seats."""

    class Meta:
        model = Seat
        fields = ['venue', 'section', 'row_number', 'seat_number']
        labels = {
            'venue': 'Venue',
            'section': 'Section',
            'row_number': 'Baris',
            'seat_number': 'No. Kursi',
        }
        widgets = {
            'venue': forms.Select(attrs={'class': 'form-control'}),
            'section': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'cth. VIP, Tribune West',
            }),
            'row_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'cth. A',
            }),
            'seat_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'cth. 12',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        venue = cleaned_data.get('venue')
        section = cleaned_data.get('section')
        row_number = cleaned_data.get('row_number')
        seat_number = cleaned_data.get('seat_number')

        if not all([venue, section, row_number, seat_number]):
            return cleaned_data

        duplicate = Seat.objects.filter(
            venue=venue,
            section__iexact=section,
            row_number__iexact=row_number,
            seat_number__iexact=seat_number,
        ).exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise forms.ValidationError(
                'Kursi dengan kombinasi venue, section, baris, dan nomor ini sudah ada.'
            )

        return cleaned_data


class TicketForm(forms.ModelForm):
    """Form for creating tickets and optionally assigning an available seat."""

    seat = forms.ModelChoiceField(
        queryset=Seat.objects.none(),
        required=False,
        label='Kursi',
        empty_label='Tanpa Kursi',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Ticket
        fields = ['torder_id', 'tcategory', 'ticket_code', 'status']
        labels = {
            'torder_id': 'Order ID',
            'tcategory': 'Kategori Tiket',
            'ticket_code': 'Kode Tiket',
            'status': 'Status',
        }
        widgets = {
            'torder_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kosongkan untuk generate otomatis',
            }),
            'tcategory': forms.Select(attrs={'class': 'form-control'}),
            'ticket_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kosongkan untuk generate otomatis',
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.current_seat = kwargs.pop('current_seat', None)
        super().__init__(*args, **kwargs)
        used_seat_ids = HasRelationship.objects.values_list('seat_id', flat=True)
        seat_queryset = Seat.objects.select_related('venue').exclude(seat_id__in=used_seat_ids)
        if self.current_seat:
            seat_queryset = Seat.objects.filter(pk=self.current_seat.pk) | seat_queryset
        self.fields['seat'].queryset = seat_queryset.distinct().order_by(
            'venue__name', 'section', 'row_number', 'seat_number'
        )

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('tcategory')
        seat = cleaned_data.get('seat')

        if not category:
            return cleaned_data

        used_quota = (
            Ticket.objects
            .filter(tcategory=category)
            .exclude(pk=self.instance.pk)
            .count()
        )
        if used_quota >= category.quota:
            raise forms.ValidationError(
                f'Kuota kategori {category.category_name} sudah penuh.'
            )

        if seat:
            occupied = HasRelationship.objects.filter(seat=seat)
            if self.instance.pk:
                occupied = occupied.exclude(ticket=self.instance)
            if occupied.exists():
                raise forms.ValidationError('Kursi ini sudah di-assign ke tiket lain.')

            if seat.venue_id != category.tevent.venue_id:
                raise forms.ValidationError(
                    'Kursi harus berasal dari venue yang sama dengan event kategori tiket.'
                )

        return cleaned_data
