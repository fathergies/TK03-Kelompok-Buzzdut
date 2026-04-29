from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Count, Sum
from django.shortcuts import render

from ticketing.models import CustomUser, Event, Ticket_Category, Venue

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
    return render(request, 'core/admin.html', context)


def organizer_dashboard(request):
    """Organizer dashboard with their event info."""
    my_events = Event.objects.filter(organizer=request.user).count()
    context = {
        'my_events': my_events,
    }
    return render(request, 'core/organizer.html', context)


def customer_dashboard(request):
    """Customer dashboard with quick access menus."""
    return render(request, 'core/customer.html')
