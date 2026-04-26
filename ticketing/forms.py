from django import forms
from django.contrib.auth import authenticate
from django.db import models

from .models import Artist, CustomUser, Ticket_Category


# =============================================================================
# Auth Forms
# =============================================================================

class RegisterForm(forms.Form):
    """Registration form for Customer and Organizer."""

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Masukkan nama lengkap'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Masukkan email'}),
    )
    phone_number = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'placeholder': 'Masukkan nomor telepon'}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Pilih username'}),
    )
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimal 6 karakter'}),
    )
    confirm_password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Konfirmasi password'}),
    )
    agree_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'Anda harus menyetujui Syarat & Ketentuan.'},
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('Username sudah digunakan.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email sudah terdaftar.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Password dan konfirmasi password tidak cocok.')
        return cleaned_data


class LoginForm(forms.Form):
    """Login form using username and password."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Masukkan username'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Masukkan password'}),
    )


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
