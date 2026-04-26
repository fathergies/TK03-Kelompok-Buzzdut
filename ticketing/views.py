from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ArtistForm, TicketCategoryForm
from .models import Artist, Event, Ticket_Category, Venue

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
