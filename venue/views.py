from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ticketing.models import Venue
from .forms import VenueForm


def get_user_role(request):
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role:
        return str(request.user.role)

    return request.session.get('role', 'CUSTOMER')


def is_admin_or_organizer(request):
    role = get_user_role(request).upper()
    return role in ['ADMIN', 'ORGANIZER']


@login_required
def venue_list(request):
    all_venues = Venue.objects.all().order_by('name')
    venues = all_venues

    query = request.GET.get('q', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_seating = request.GET.get('seating', '').strip()

    if query:
        venues = venues.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query)
        )

    if selected_city:
        venues = venues.filter(city__iexact=selected_city)

    if selected_seating == 'reserved':
        venues = venues.filter(has_reserved_seating=True)
    elif selected_seating == 'free':
        venues = venues.filter(has_reserved_seating=False)

    cities = Venue.objects.values_list('city', flat=True).distinct().order_by('city')

    total_venues = all_venues.count()
    reserved_count = all_venues.filter(has_reserved_seating=True).count()
    total_capacity = all_venues.aggregate(total=Sum('capacity'))['total'] or 0

    role = get_user_role(request)
    can_manage = is_admin_or_organizer(request)

    context = {
        'venues': venues,
        'cities': cities,
        'query': query,
        'selected_city': selected_city,
        'selected_seating': selected_seating,
        'total_venues': total_venues,
        'reserved_count': reserved_count,
        'total_capacity': total_capacity,
        'role': role,
        'is_admin_or_organizer': can_manage,
        'can_manage': can_manage,
    }

    return render(request, 'venue/venue_list.html', context)


@login_required
def venue_create(request):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Anda tidak memiliki akses untuk menambah venue.')
        return redirect('venue_list')

    if request.method == 'POST':
        form = VenueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Venue berhasil ditambahkan.')
        else:
            messages.error(request, 'Venue gagal ditambahkan. Pastikan semua data sudah benar.')

    return redirect('venue_list')


@login_required
def venue_update(request, venue_id):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Anda tidak memiliki akses untuk mengubah venue.')
        return redirect('venue_list')

    venue = get_object_or_404(Venue, id=venue_id)

    if request.method == 'POST':
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            messages.success(request, 'Venue berhasil diperbarui.')
        else:
            messages.error(request, 'Venue gagal diperbarui. Pastikan semua data sudah benar.')

    return redirect('venue_list')


@login_required
def venue_delete(request, venue_id):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus venue.')
        return redirect('venue_list')

    venue = get_object_or_404(Venue, id=venue_id)

    if request.method == 'POST':
        venue.delete()
        messages.success(request, 'Venue berhasil dihapus.')

    return redirect('venue_list')