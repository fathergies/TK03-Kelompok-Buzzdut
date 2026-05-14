from basdat_tk03.auth import login_required
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
    """Customer dashboard with real statistics."""
    user_id = request.user.pk
    
    # Find customer id
    customer = fetch_one("SELECT customer_id FROM CUSTOMER WHERE user_id = %s", [str(user_id)])
    
    active_tickets = 0
    total_orders = 0
    upcoming_events = 0

    if customer:
        cust_id = customer['customer_id']
        
        # Active tickets
        t_stat = fetch_one("""
            SELECT COUNT(t.ticket_id) as total 
            FROM TICKET t
            JOIN "ORDER" o ON t.torder_id = o.order_id
            WHERE o.customer_id = %s AND t.status = 'Valid'
        """, [cust_id])
        if t_stat: active_tickets = t_stat['total']

        # Total orders
        o_stat = fetch_one("""
            SELECT COUNT(*) as total 
            FROM "ORDER" 
            WHERE customer_id = %s
        """, [cust_id])
        if o_stat: total_orders = o_stat['total']

        # Upcoming events
        e_stat = fetch_one("""
            SELECT COUNT(DISTINCT e.event_id) as total 
            FROM TICKET t
            JOIN "ORDER" o ON t.torder_id = o.order_id
            JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
            JOIN EVENT e ON tc.tevent_id = e.event_id
            WHERE o.customer_id = %s AND t.status = 'Valid' AND e.event_datetime > CURRENT_TIMESTAMP
        """, [cust_id])
        if e_stat: upcoming_events = e_stat['total']

    context = {
        'active_tickets': active_tickets,
        'total_orders': total_orders,
        'upcoming_events': upcoming_events,
    }
    return render(request, 'core/customer.html', context)
