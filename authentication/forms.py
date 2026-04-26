from django import forms
from ticketing.models import CustomUser

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
