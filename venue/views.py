from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum
from .models import Venue
from .forms import VenueForm


def get_user_role(request):
    """
    Sementara default ke Admin biar aman untuk screenshot.
    Nanti kalau sistem login kelompokmu sudah stabil, ganti sesuai role asli.
    """
    role = None

    if hasattr(request.user, 'role'):
        role = getattr(request.user, 'role', None)

    if not role:
        role = request.session.get('role')

    if not role:
        role = 'Admin'  # fallback sementara

    return str(role)


def venue_list(request):
    all_venues = Venue.objects.all().order_by('nama_venue')
    venues = all_venues

    query = request.GET.get('q', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_seating = request.GET.get('seating', '').strip()

    if query:
        venues = venues.filter(
            Q(nama_venue__icontains=query) |
            Q(alamat__icontains=query)
        )

    if selected_city:
        venues = venues.filter(kota__iexact=selected_city)

    if selected_seating == 'reserved':
        venues = venues.filter(has_reserved_seating=True)
    elif selected_seating == 'free':
        venues = venues.filter(has_reserved_seating=False)

    cities = Venue.objects.values_list('kota', flat=True).distinct().order_by('kota')

    total_venues = all_venues.count()
    reserved_count = all_venues.filter(has_reserved_seating=True).count()
    total_capacity = all_venues.aggregate(total=Sum('kapasitas'))['total'] or 0

    role = get_user_role(request)
    is_admin_or_organizer = role.lower() in ['admin', 'organizer']

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
        'is_admin_or_organizer': is_admin_or_organizer,
    }
    return render(request, 'venue/venue_list.html', context)


def venue_create(request):
    if request.method == 'POST':
        form = VenueForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect('venue_list')


def venue_update(request, venue_id):
    venue = get_object_or_404(Venue, venue_id=venue_id)
    if request.method == 'POST':
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
    return redirect('venue_list')


def venue_delete(request, venue_id):
    venue = get_object_or_404(Venue, venue_id=venue_id)
    if request.method == 'POST':
        venue.delete()
    return redirect('venue_list')