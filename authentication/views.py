from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm
from ticketing.models import CustomUser

def register_select(request):
    """Role selection page: Pelanggan or Penyelenggara."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'authentication/register_select.html')


def register_view(request, role):
    """Registration form for a specific role (CUSTOMER or ORGANIZER)."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    role_upper = role.upper()
    if role_upper not in ('CUSTOMER', 'ORGANIZER', 'ADMIN'):
        return redirect('authentication:register_select')

    role_labels = {
        'CUSTOMER': 'Pelanggan',
        'ORGANIZER': 'Penyelenggara',
        'ADMIN': 'Admin',
    }

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['full_name'],
                phone_number=form.cleaned_data['phone_number'],
                role=role_upper,
            )
            messages.success(request, f'Akun berhasil dibuat! Silakan login.')
            return redirect('authentication:login')
    else:
        form = RegisterForm()

    context = {
        'form': form,
        'role': role_upper,
        'role_label': role_labels.get(role_upper, role),
    }
    return render(request, 'authentication/register_form.html', context)


def login_view(request):
    """Login using username and password."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                messages.success(request, f'Selamat datang, {user.first_name or user.username}!')
                return redirect('core:dashboard')
            else:
                messages.error(request, 'Username atau password salah.')
    else:
        form = LoginForm()

    return render(request, 'authentication/login.html', {'form': form})


def logout_view(request):
    """End session and redirect to login."""
    logout(request)
    messages.info(request, 'Anda telah logout.')
    return redirect('authentication:login')
