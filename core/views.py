from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from basdat_tk03.db import fetch_one

@login_required
def dashboard(request):
    """Route to the correct dashboard based on user role."""
    role = request.user.role if hasattr(request.user, 'role') else 'CUSTOMER'
    if role == 'ADMIN':
        return admin_dashboard(request)
    elif role == 'ORGANIZER':
        return organizer_dashboard(request)
    else:
        return customer_dashboard(request)


def admin_dashboard(request):
    """Admin dashboard with platform statistics using Raw SQL."""
    users_stat = fetch_one("SELECT COUNT(*) AS total FROM USER_ACCOUNT;")
    events_stat = fetch_one("SELECT COUNT(*) AS total FROM EVENT;")
    venues_stat = fetch_one("SELECT COUNT(*) AS total FROM VENUE;")
    gross_stat = fetch_one("SELECT SUM(price) AS total FROM TICKET_CATEGORY;")
    venue_agg_stat = fetch_one("SELECT COUNT(venue_id) AS total, MAX(capacity) AS max_capacity FROM VENUE;")

    context = {
        'total_users': users_stat['total'] if users_stat else 0,
        'total_events': events_stat['total'] if events_stat else 0,
        'total_venues': venues_stat['total'] if venues_stat else 0,
        'gross_volume': gross_stat['total'] if gross_stat and gross_stat['total'] else 0,
        'venue_max_capacity': venue_agg_stat['max_capacity'] if venue_agg_stat and venue_agg_stat['max_capacity'] else 0,
    }
    return render(request, 'core/admin.html', context)


def organizer_dashboard(request):
    """Organizer dashboard with their event info using Raw SQL."""
    # Assuming organizer events are linked by organizer_id
    # We will fetch the organizer_id based on the logged-in user
    # If the user has a custom attribute or just by username:
    user_id = request.user.pk
    
    # We first find the organizer's UUID based on the user's UUID
    org_stat = fetch_one("SELECT organizer_id FROM ORGANIZER WHERE user_id = %s;", [str(user_id)])
    my_events = 0
    if org_stat:
        event_stat = fetch_one("SELECT COUNT(*) AS total FROM EVENT WHERE organizer_id = %s;", [org_stat['organizer_id']])
        if event_stat:
            my_events = event_stat['total']
            
    context = {
        'my_events': my_events,
    }
    return render(request, 'core/organizer.html', context)


def customer_dashboard(request):
    """Customer dashboard with quick access menus."""
    return render(request, 'core/customer.html')
