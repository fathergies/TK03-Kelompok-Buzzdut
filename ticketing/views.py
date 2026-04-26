from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Count, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ArtistForm, LoginForm, RegisterForm, TicketCategoryForm
from .models import Artist, CustomUser, Event, Ticket_Category, Venue


# =============================================================================
# Auth Views
# =============================================================================

def register_select(request):
    """Role selection page: Pelanggan or Penyelenggara."""
    if request.user.is_authenticated:
        return redirect('ticketing:dashboard')
    return render(request, 'ticketing/auth/register_select.html')


def register_view(request, role):
    """Registration form for a specific role (CUSTOMER or ORGANIZER)."""
    if request.user.is_authenticated:
        return redirect('ticketing:dashboard')

    role_upper = role.upper()
    if role_upper not in ('CUSTOMER', 'ORGANIZER'):
        return redirect('ticketing:register_select')

    role_labels = {
        'CUSTOMER': 'Pelanggan',
        'ORGANIZER': 'Penyelenggara',
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
            return redirect('ticketing:login')
    else:
        form = RegisterForm()

    context = {
        'form': form,
        'role': role_upper,
        'role_label': role_labels.get(role_upper, role),
    }
    return render(request, 'ticketing/auth/register_form.html', context)


def login_view(request):
    """Login using username and password."""
    if request.user.is_authenticated:
        return redirect('ticketing:dashboard')

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
                return redirect('ticketing:dashboard')
            else:
                messages.error(request, 'Username atau password salah.')
    else:
        form = LoginForm()

    return render(request, 'ticketing/auth/login.html', {'form': form})


def logout_view(request):
    """End session and redirect to login."""
    logout(request)
    messages.info(request, 'Anda telah logout.')
    return redirect('ticketing:login')


# =============================================================================
# Dashboard Views
# =============================================================================

@login_required
def dashboard(request):
    """Route to the correct dashboard based on user role."""
    role = request.user.role
    if role == 'ADMIN':
        return admin_dashboard(request)
    elif role == 'ORGANIZER':
        return organizer_dashboard(request)
    else:
        return customer_dashboard(request)


def admin_dashboard(request):
    """Admin dashboard with platform statistics."""
    total_users = CustomUser.objects.count()
    total_events = Event.objects.count()
    total_venues = Venue.objects.count()

    # Gross volume from ticket prices * quotas
    gross_volume = (
        Ticket_Category.objects.aggregate(
            total=Sum('price')
        )['total'] or 0
    )

    # Venue stats
    venue_stats = Venue.objects.aggregate(
        total=Count('id'),
        max_capacity=models.Max('capacity'),
    )

    context = {
        'total_users': total_users,
        'total_events': total_events,
        'total_venues': total_venues,
        'gross_volume': gross_volume,
        'venue_max_capacity': venue_stats.get('max_capacity') or 0,
    }
    return render(request, 'ticketing/dashboard/admin.html', context)


def organizer_dashboard(request):
    """Organizer dashboard with their event info."""
    my_events = Event.objects.filter(organizer=request.user).count()
    context = {
        'my_events': my_events,
    }
    return render(request, 'ticketing/dashboard/organizer.html', context)


def customer_dashboard(request):
    """Customer dashboard with quick access menus."""
    return render(request, 'ticketing/dashboard/customer.html')


# =============================================================================
# Helper: Role Checks
# =============================================================================

def _is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


def _is_admin_or_organizer(user):
    return user.is_authenticated and user.role in ('ADMIN', 'ORGANIZER')


# =============================================================================
# Artist Views
# =============================================================================

def show_artists(request):
    """List all artists. Accessible by logged-in users."""
    artists = Artist.objects.all()
    total_artists = artists.count()
    unique_genres = artists.exclude(genre='').values('genre').distinct().count()
    # Count how many artists appear in at least one event
    from .models import Event_Artist
    artists_in_events = Event_Artist.objects.values('artist').distinct().count()

    context = {
        'artists': artists,
        'total_artists': total_artists,
        'unique_genres': unique_genres,
        'artists_in_events': artists_in_events,
        'user_role': getattr(request.user, 'role', None),
        'can_manage': _is_admin(request.user) if request.user.is_authenticated else False,
    }
    return render(request, 'ticketing/show_artists.html', context)


@login_required
def create_artist(request):
    """Create a new artist. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        form = ArtistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Artist created successfully!')
            return redirect('ticketing:show_artists')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ArtistForm()

    context = {
        'form': form,
        'form_title': 'Add New Artist',
        'submit_label': 'Create Artist',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/artist_form.html', context)


@login_required
def edit_artist(request, pk):
    """Edit an existing artist. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    artist = get_object_or_404(Artist, pk=pk)

    if request.method == 'POST':
        form = ArtistForm(request.POST, instance=artist)
        if form.is_valid():
            form.save()
            messages.success(request, f'Artist "{artist.name}" updated successfully!')
            return redirect('ticketing:show_artists')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ArtistForm(instance=artist)

    context = {
        'form': form,
        'form_title': f'Edit Artist: {artist.name}',
        'submit_label': 'Save Changes',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/artist_form.html', context)


@login_required
def delete_artist(request, pk):
    """Delete an artist. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    artist = get_object_or_404(Artist, pk=pk)

    if request.method == 'POST':
        name = artist.name
        artist.delete()
        messages.success(request, f'Artist "{name}" deleted successfully!')
        return redirect('ticketing:show_artists')

    context = {
        'object': artist,
        'object_type': 'Artist',
        'cancel_url': 'ticketing:show_artists',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/delete_confirm.html', context)


# =============================================================================
# Ticket Category Views
# =============================================================================

def show_ticket_categories(request):
    """List all ticket categories. Accessible by everyone."""
    categories = Ticket_Category.objects.select_related('tevent', 'tevent__venue').all()
    context = {
        'categories': categories,
        'user_role': getattr(request.user, 'role', None),
        'can_manage': _is_admin_or_organizer(request.user) if request.user.is_authenticated else False,
    }
    return render(request, 'ticketing/show_ticket_categories.html', context)


@login_required
def create_ticket_category(request):
    """Create a new ticket category. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        form = TicketCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ticket category created successfully!')
            return redirect('ticketing:show_ticket_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TicketCategoryForm()

    context = {
        'form': form,
        'form_title': 'Add New Ticket Category',
        'submit_label': 'Create Category',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/ticket_category_form.html', context)


@login_required
def edit_ticket_category(request, pk):
    """Edit an existing ticket category. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    category = get_object_or_404(Ticket_Category, pk=pk)

    if request.method == 'POST':
        form = TicketCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ticket category "{category.category_name}" updated successfully!')
            return redirect('ticketing:show_ticket_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TicketCategoryForm(instance=category)

    context = {
        'form': form,
        'form_title': f'Edit Category: {category.category_name}',
        'submit_label': 'Save Changes',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/ticket_category_form.html', context)


@login_required
def delete_ticket_category(request, pk):
    """Delete a ticket category. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    category = get_object_or_404(Ticket_Category, pk=pk)

    if request.method == 'POST':
        name = category.category_name
        category.delete()
        messages.success(request, f'Ticket category "{name}" deleted successfully!')
        return redirect('ticketing:show_ticket_categories')

    context = {
        'object': category,
        'object_type': 'Ticket Category',
        'cancel_url': 'ticketing:show_ticket_categories',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/delete_confirm.html', context)
