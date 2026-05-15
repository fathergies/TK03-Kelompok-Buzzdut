from basdat_tk03.auth import login_required
from django.shortcuts import render, redirect
from basdat_tk03.db import fetch_one, execute_query
from django.contrib import messages
import psycopg2
import uuid
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


def test_trigger(request):
    """View to explicitly test triggers from the web."""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'trigger_username':
                # Force Trigger 1: Invalid username with symbols
                execute_query("INSERT INTO USER_ACCOUNT (user_id, username, email, password) VALUES (%s, %s, %s, %s);",
                              [str(uuid.uuid4()), 'invalid!@#', f'test{uuid.uuid4().hex[:5]}@test.com', 'pwd'])
            elif action == 'trigger_venue_duplicate':
                # Force Trigger 2: Duplicate Venue in the same city
                v_name = f'Venue_{uuid.uuid4().hex[:5]}'
                city = 'Jakarta'
                # Insert first one
                execute_query("INSERT INTO VENUE (venue_id, venue_name, capacity, address, city, seating_type) VALUES (%s, %s, %s, %s, %s, %s);",
                              [str(uuid.uuid4()), v_name, 100, 'Alamat', city, 'free'])
                # Insert duplicate
                execute_query("INSERT INTO VENUE (venue_id, venue_name, capacity, address, city, seating_type) VALUES (%s, %s, %s, %s, %s, %s);",
                              [str(uuid.uuid4()), v_name, 100, 'Alamat', city, 'free'])
            elif action == 'trigger_venue_delete':
                # Force Trigger 3: Delete venue with active events
                v_id = str(uuid.uuid4())
                e_id = str(uuid.uuid4())
                org_id = str(uuid.uuid4())
                
                # 1. Insert Dummy Venue
                execute_query("INSERT INTO VENUE (venue_id, venue_name, capacity, address, city, seating_type) VALUES (%s, %s, %s, %s, %s, %s);",
                              [v_id, 'Venue Test Delete', 100, 'Alamat', 'TestCity', 'free'])
                
                # 2. To insert EVENT, we usually need an Organizer. Let's just try inserting EVENT directly if possible, or we might need to mock organizer/user too. 
                # Actually, wait. Event needs an organizer. Let's find an existing organizer.
                org = fetch_one("SELECT organizer_id FROM ORGANIZER LIMIT 1;")
                if not org:
                    messages.error(request, "Gagal menguji: Tidak ada data Organizer di database untuk membuat Event dummy.")
                    return render(request, 'core/test_trigger.html')
                
                # 3. Insert active Dummy Event (Date in future)
                execute_query("INSERT INTO EVENT (event_id, title, description, event_datetime, venue_id, organizer_id) VALUES (%s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '1 day', %s, %s);",
                              [e_id, 'Event Test Delete', 'Desc', v_id, org['organizer_id']])
                
                # 4. Attempt to Delete Venue (Should Trigger Error)
                execute_query("DELETE FROM VENUE WHERE venue_id = %s;", [v_id])

            messages.success(request, f"Aksi {action} berhasil tanpa memicu Trigger Error (Ini berarti data lolos validasi atau Trigger belum dipasang dengan benar).")

        except psycopg2.DatabaseError as e:
            error_msg = str(e).split('\n')[0]
            messages.add_message(request, messages.ERROR, error_msg, extra_tags='trigger_error')
        except Exception as e:
            messages.error(request, f"Backend Error: {e}")
            
    return render(request, 'core/test_trigger.html')
