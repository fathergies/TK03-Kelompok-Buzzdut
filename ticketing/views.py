import uuid
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from basdat_tk03.auth import login_required
from basdat_tk03.db import fetch_all, fetch_one, execute_query

# =============================================================================
# Helper: Role Checks
# =============================================================================

def _is_admin(user):
    return hasattr(user, 'role') and user.role == 'ADMIN'

def _is_admin_or_organizer(user):
    return hasattr(user, 'role') and user.role in ('ADMIN', 'ORGANIZER')

def _get_artist_from_post_value(artist_value):
    artist_value = str(artist_value).strip()
    if not artist_value:
        raise ValidationError('Artist wajib dipilih.')
    
    try:
        uuid.UUID(artist_value)
        artist = fetch_one("SELECT * FROM ARTIST WHERE artist_id = %s", [artist_value])
        if artist: return artist
    except ValueError:
        pass
        
    artist = fetch_one("SELECT * FROM ARTIST WHERE name ILIKE %s", [artist_value])
    if artist: return artist
    raise ValidationError(f'Artist tidak ditemukan: {artist_value}')

# =============================================================================
# Artist Views
# =============================================================================

def show_artists(request):
    artists = fetch_all("SELECT * FROM ARTIST ORDER BY name")
    total_artists = len(artists)
    
    unique_genres_raw = fetch_all("SELECT DISTINCT genre FROM ARTIST WHERE genre != '' AND genre IS NOT NULL")
    unique_genres = len(unique_genres_raw)
    
    artists_in_events_raw = fetch_one("SELECT COUNT(DISTINCT artist_id) as count FROM EVENT_ARTIST")
    artists_in_events = artists_in_events_raw['count'] if artists_in_events_raw else 0

    context = {
        'artists': artists,
        'total_artists': total_artists,
        'unique_genres': unique_genres,
        'artists_in_events': artists_in_events,
        'user_role': getattr(request.user, 'role', None),
        'can_manage': _is_admin(request.user) if getattr(request.user, 'is_authenticated', False) else False,
    }
    return render(request, 'ticketing/show_artists.html', context)


@login_required
def create_artist(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        name = request.POST.get('name')
        genre = request.POST.get('genre')
        if name:
            try:
                execute_query("INSERT INTO ARTIST (artist_id, name, genre) VALUES (%s, %s, %s)",
                              [str(uuid.uuid4()), name, genre])
                messages.success(request, 'Artist created successfully!')
                return redirect('ticketing:show_artists')
            except Exception as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Name is required.')

    class DummyForm: pass
    context = {
        'form': DummyForm(),
        'form_title': 'Add New Artist',
        'submit_label': 'Create Artist',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/artist_form.html', context)


@login_required
def edit_artist(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    artist = fetch_one("SELECT * FROM ARTIST WHERE artist_id = %s", [pk])
    if not artist:
        messages.error(request, 'Artist not found.')
        return redirect('ticketing:show_artists')

    if request.method == 'POST':
        name = request.POST.get('name')
        genre = request.POST.get('genre')
        if name:
            try:
                execute_query("UPDATE ARTIST SET name=%s, genre=%s WHERE artist_id=%s", [name, genre, pk])
                messages.success(request, f'Artist "{name}" updated successfully!')
                return redirect('ticketing:show_artists')
            except Exception as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Name is required.')

    # Mock form fields
    class DummyForm:
        def __init__(self, data):
            self.instance = type('obj', (object,), data)
    
    context = {
        'form': DummyForm(artist),
        'form_title': f'Edit Artist: {artist["name"]}',
        'submit_label': 'Save Changes',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/artist_form.html', context)


@login_required
def delete_artist(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    artist = fetch_one("SELECT * FROM ARTIST WHERE artist_id = %s", [pk])
    if not artist:
        return redirect('ticketing:show_artists')

    if request.method == 'POST':
        try:
            execute_query("DELETE FROM ARTIST WHERE artist_id = %s", [pk])
            messages.success(request, f'Artist "{artist["name"]}" deleted successfully!')
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('ticketing:show_artists')

    # Mock object
    artist['pk'] = artist['artist_id']
    context = {
        'object': artist,
        'object_type': 'Artist',
        'cancel_url': 'ticketing:show_artists',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/delete_confirm.html', context)

@login_required
def assign_artist_to_event(request):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    events = fetch_all("SELECT event_id, event_title FROM EVENT ORDER BY event_title")
    artists = fetch_all("SELECT artist_id, name FROM ARTIST ORDER BY name")

    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        artist_id = request.POST.get('artist_id')
        role = request.POST.get('role') or 'Main Performer'

        try:
            execute_query(
                "INSERT INTO EVENT_ARTIST (event_id, artist_id, role) VALUES (%s, %s, %s)",
                [event_id, artist_id, role]
            )
            messages.success(request, 'Artist berhasil ditambahkan ke event.')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'ticketing/assign_artist_to_event.html', {
        'events': events,
        'artists': artists,
        'user_role': request.user.role,
    })


# =============================================================================
# Ticket Category Views
# =============================================================================

def show_ticket_categories(request):
    base_query = """
        SELECT tc.*, e.event_title as tevent_title, v.venue_name, 
               COALESCE((SELECT SUM(quota) FROM TICKET_CATEGORY WHERE tevent_id = tc.tevent_id), 0) as total_event_quota
        FROM TICKET_CATEGORY tc
        JOIN EVENT e ON tc.tevent_id = e.event_id
        JOIN VENUE v ON e.venue_id = v.venue_id
        WHERE 1=1
    """
    params = []
    
    search_query = request.GET.get('q', '')
    if search_query:
        base_query += " AND tc.category_name ILIKE %s"
        params.append(f"%{search_query}%")

    event_filter = request.GET.get('event', '')
    if event_filter:
        base_query += " AND tc.tevent_id = %s"
        params.append(event_filter)

    base_query += " ORDER BY e.event_title ASC, tc.category_name ASC"
    
    categories = fetch_all(base_query, params)
    
    # Ambil sisa kuota dari stored procedure/function Trigger 3
    for c in categories:
        quota_data = fetch_one(
            """
            SELECT sold_ticket, remaining_quota
            FROM TIKTAKTUK.get_ticket_category_remaining_quota(%s)
            WHERE category_id = %s
            """,
            [c['tevent_id'], c['category_id']]
        )

        if quota_data:
            c['sold_ticket'] = quota_data['sold_ticket']
            c['remaining_quota'] = quota_data['remaining_quota']
        else:
            c['sold_ticket'] = 0
            c['remaining_quota'] = c['quota']
    
    total_categories = len(categories)
    total_quota = sum(c['quota'] for c in categories)
    max_price = max((c['price'] for c in categories), default=0)

    all_events = fetch_all("SELECT event_id as id, event_title as title FROM EVENT ORDER BY event_title")

    # Mock objects for template compatibility
    for c in categories:
        class MockEvent: pass
        class MockVenue: pass
        
        venue = MockVenue()
        venue.name = c['venue_name']
        
        event = MockEvent()
        event.title = c['tevent_title']
        event.venue = venue
        
        c['tevent'] = event
        c['pk'] = c['category_id']

    context = {
        'categories': categories,
        'search_query': search_query,
        'event_filter': event_filter,
        'all_events': all_events,
        'total_categories': total_categories,
        'total_quota': total_quota,
        'max_price': max_price,
        'user_role': getattr(request.user, 'role', None),
        'can_manage': _is_admin_or_organizer(request.user) if getattr(request.user, 'is_authenticated', False) else False,
    }
    return render(request, 'ticketing/show_ticket_categories.html', context)


@login_required
def create_ticket_category(request):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        tevent_id = request.POST.get('tevent')
        category_name = request.POST.get('category_name')
        price = request.POST.get('price')
        quota = request.POST.get('quota')

        try:
            quota = int(quota)
            if quota <= 0: raise ValueError("Quota must be positive")
            
            event = fetch_one("SELECT e.*, v.capacity FROM EVENT e JOIN VENUE v ON e.venue_id = v.venue_id WHERE e.event_id = %s", [tevent_id])
            if not event: raise ValueError("Event not found")
            
            existing_quota = fetch_one("SELECT COALESCE(SUM(quota), 0) as total FROM TICKET_CATEGORY WHERE tevent_id = %s", [tevent_id])['total']
            
            if existing_quota + quota > event['capacity']:
                raise ValueError(f"Total quota exceeds venue capacity ({event['capacity']}). Remaining: {event['capacity'] - existing_quota}")
                
            execute_query(
                "INSERT INTO TICKET_CATEGORY (category_id, category_name, quota, price, tevent_id) VALUES (%s, %s, %s, %s, %s)",
                [str(uuid.uuid4()), category_name, quota, price, tevent_id]
            )
            messages.success(request, 'Ticket category created successfully!')
            return redirect('ticketing:show_ticket_categories')
        except Exception as e:
            messages.error(request, str(e))

    all_events = fetch_all("SELECT event_id, event_title FROM EVENT ORDER BY event_title")
    class DummyForm:
        fields = {'tevent': type('obj', (object,), {'queryset': all_events})}
        
    context = {
        'form': DummyForm(),
        'form_title': 'Add New Ticket Category',
        'submit_label': 'Create Category',
        'user_role': request.user.role,
        'events': all_events
    }
    return render(request, 'ticketing/ticket_category_form.html', context)


@login_required
def edit_ticket_category(request, pk):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    category = fetch_one("SELECT * FROM TICKET_CATEGORY WHERE category_id = %s", [pk])
    if not category:
        return redirect('ticketing:show_ticket_categories')

    if request.method == 'POST':
        tevent_id = request.POST.get('tevent')
        category_name = request.POST.get('category_name')
        price = request.POST.get('price')
        quota = request.POST.get('quota')

        try:
            quota = int(quota)
            if quota <= 0: raise ValueError("Quota must be positive")
            
            event = fetch_one("SELECT e.*, v.capacity FROM EVENT e JOIN VENUE v ON e.venue_id = v.venue_id WHERE e.event_id = %s", [tevent_id])
            if not event: raise ValueError("Event not found")
            
            existing_quota = fetch_one("SELECT COALESCE(SUM(quota), 0) as total FROM TICKET_CATEGORY WHERE tevent_id = %s AND category_id != %s", [tevent_id, pk])['total']
            
            if existing_quota + quota > event['capacity']:
                raise ValueError(f"Total quota exceeds venue capacity ({event['capacity']}). Remaining: {event['capacity'] - existing_quota}")
                
            execute_query(
                "UPDATE TICKET_CATEGORY SET category_name=%s, quota=%s, price=%s, tevent_id=%s WHERE category_id=%s",
                [category_name, quota, price, tevent_id, pk]
            )
            messages.success(request, f'Ticket category "{category_name}" updated successfully!')
            return redirect('ticketing:show_ticket_categories')
        except Exception as e:
            messages.error(request, str(e))

    all_events = fetch_all("SELECT event_id, event_title FROM EVENT ORDER BY event_title")
    class DummyForm:
        def __init__(self, data):
            self.instance = type('obj', (object,), data)
            
    context = {
        'form': DummyForm(category),
        'form_title': f'Edit Category: {category["category_name"]}',
        'submit_label': 'Save Changes',
        'user_role': request.user.role,
        'events': all_events,
        'category': category
    }
    return render(request, 'ticketing/ticket_category_form.html', context)


@login_required
def delete_ticket_category(request, pk):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    category = fetch_one("""
        SELECT tc.*, e.event_title as tevent_title
        FROM TICKET_CATEGORY tc
        JOIN EVENT e ON tc.tevent_id = e.event_id
        WHERE tc.category_id = %s
    """, [pk])
    if not category:
        return redirect('ticketing:show_ticket_categories')

    if request.method == 'POST':
        try:
            execute_query("DELETE FROM TICKET_CATEGORY WHERE category_id = %s", [pk])
            messages.success(request, f'Ticket category "{category["category_name"]}" deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('ticketing:show_ticket_categories')

    class MockEvent: pass
    event = MockEvent()
    event.title = category['tevent_title']
    category['tevent'] = event
    category['id'] = category['category_id']
    category['pk'] = category['category_id']
    category['category_name'] = category['category_name']
    
    context = {
        'object': category,
        'object_type': 'Ticket Category',
        'cancel_url': 'ticketing:show_ticket_categories',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/delete_confirm.html', context)

# =============================================================================
# Seat Views
# =============================================================================

@login_required
def seat_list(request):
    seats = fetch_all("""
        SELECT s.*, v.venue_name, hr.ticket_id
        FROM SEAT s
        JOIN VENUE v ON s.venue_id = v.venue_id
        LEFT JOIN HAS_RELATIONSHIP hr ON s.seat_id = hr.seat_id
        ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
    """)
    
    total_seats = len(seats)
    occupied_count = sum(1 for s in seats if s['ticket_id'])
    
    seat_rows = []
    for s in seats:
        class MockVenue: pass
        venue = MockVenue()
        venue.name = s['venue_name']
        
        s['venue'] = venue
        s['pk'] = s['seat_id']
        
        seat_rows.append({
            'seat': s,
            'is_used': bool(s['ticket_id'])
        })

    venues = fetch_all("SELECT venue_id as id, venue_name as name FROM VENUE ORDER BY venue_name")

    context = {
        'seat_rows': seat_rows,
        'total_seats': total_seats,
        'available_count': total_seats - occupied_count,
        'occupied_count': occupied_count,
        'venues': venues,
        'can_manage': _is_admin_or_organizer(request.user),
        'user_role': request.user.role,
    }
    return render(request, "ticketing/seat_list.html", context)


@login_required
def create_seat(request):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        venue_id = request.POST.get('venue')
        section = request.POST.get('section')
        row_number = request.POST.get('row_number')
        seat_number = request.POST.get('seat_number')

        try:
            duplicate = fetch_one("SELECT seat_id FROM SEAT WHERE venue_id=%s AND section ILIKE %s AND row_number ILIKE %s AND seat_number ILIKE %s", [venue_id, section, row_number, seat_number])
            if duplicate:
                messages.error(request, 'Kursi dengan kombinasi venue, section, baris, dan nomor ini sudah ada.')
            else:
                execute_query("INSERT INTO SEAT (seat_id, venue_id, section, row_number, seat_number) VALUES (%s, %s, %s, %s, %s)", 
                              [str(uuid.uuid4()), venue_id, section, row_number, seat_number])
                messages.success(request, 'Kursi berhasil ditambahkan.')
        except Exception as e:
            messages.error(request, f'Kursi gagal ditambahkan: {e}')
            
    return redirect('ticketing:seat_list')


@login_required
def edit_seat(request, pk):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        venue_id = request.POST.get('venue')
        section = request.POST.get('section')
        row_number = request.POST.get('row_number')
        seat_number = request.POST.get('seat_number')

        try:
            duplicate = fetch_one("SELECT seat_id FROM SEAT WHERE venue_id=%s AND section ILIKE %s AND row_number ILIKE %s AND seat_number ILIKE %s AND seat_id != %s", [venue_id, section, row_number, seat_number, pk])
            if duplicate:
                messages.error(request, 'Kursi dengan kombinasi venue, section, baris, dan nomor ini sudah ada.')
            else:
                execute_query("UPDATE SEAT SET venue_id=%s, section=%s, row_number=%s, seat_number=%s WHERE seat_id=%s", 
                              [venue_id, section, row_number, seat_number, pk])
                messages.success(request, 'Kursi berhasil diperbarui.')
        except Exception as e:
            messages.error(request, f'Kursi gagal diperbarui: {e}')
            
    return redirect('ticketing:seat_list')


@login_required
def delete_seat(request, pk):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        has_rel = fetch_one("SELECT seat_id FROM HAS_RELATIONSHIP WHERE seat_id = %s", [pk])
        if has_rel:
            messages.error(request, 'Kursi ini sudah di-assign ke tiket dan tidak dapat dihapus.')
        else:
            execute_query("DELETE FROM SEAT WHERE seat_id = %s", [pk])
            messages.success(request, 'Kursi berhasil dihapus.')
            
    return redirect('ticketing:seat_list')


# =============================================================================
# Ticket Views
# =============================================================================

def _generate_ticket_code():
    return f"TKT-{uuid.uuid4().hex[:10].upper()}"

def _dummy_customer_name(seed):
    names = ['Budi Santoso', 'Siti Rahayu', 'Dina Pratiwi', 'Raka Wijaya']
    try:
        index = uuid.UUID(str(seed)).int % len(names)
    except ValueError:
        index = sum(ord(char) for char in str(seed)) % len(names)
    return names[index]

def _dummy_order_id_for_event(event_id):
    return uuid.uuid5(uuid.NAMESPACE_URL, f'tiktaktuk-order-{event_id}')

def _build_dummy_orders(events):
    orders = []
    for index, event in enumerate(events, start=1):
        order_id = _dummy_order_id_for_event(event['id'])
        is_reserved = index % 2 == 1
        orders.append({
            'id': order_id,
            'code': f'ord_{index:03d}',
            'customer': _dummy_customer_name(order_id),
            'event': event,
            'is_reserved': is_reserved,
        })
    return orders

@login_required
def ticket_list(request):
    base_query = """
        SELECT t.*, tc.category_name, tc.price, e.event_title, e.event_datetime, v.venue_name, v.venue_id, hr.seat_id, s.section, s.row_number, s.seat_number, o.customer_id, ua.username
        FROM TICKET t
        JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
        JOIN EVENT e ON tc.tevent_id = e.event_id
        JOIN VENUE v ON e.venue_id = v.venue_id
        JOIN "ORDER" o ON t.torder_id = o.order_id
        JOIN CUSTOMER c ON o.customer_id = c.customer_id
        JOIN USER_ACCOUNT ua ON c.user_id = ua.user_id
        LEFT JOIN HAS_RELATIONSHIP hr ON t.ticket_id = hr.ticket_id
        LEFT JOIN SEAT s ON hr.seat_id = s.seat_id
        WHERE 1=1
    """
    params = []

    if request.user.role == 'CUSTOMER':
        base_query += " AND c.user_id = %s"
        params.append(request.user.pk)

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    
    if query:
        base_query += " AND (t.ticket_code ILIKE %s OR e.event_title ILIKE %s OR tc.category_name ILIKE %s)"
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    if status:
        base_query += " AND t.status = %s"
        params.append(status)
        
    base_query += " ORDER BY t.ticket_code"
    
    tickets = fetch_all(base_query, params)
    
    ticket_rows = []
    for t in tickets:
        order_code = f"ord_{str(t['torder_id']).split('-')[0]}"
        
        class MockSeat: pass
        seat = MockSeat()
        seat.section = t['section']
        seat.row_number = t['row_number']
        seat.seat_number = t['seat_number']
        
        class MockVenue: pass
        venue = MockVenue()
        venue.name = t['venue_name']
        
        class MockEvent: pass
        event = MockEvent()
        event.title = t['event_title']
        event.start_date = t['event_datetime']
        event.venue = venue
        
        class MockCategory: pass
        cat = MockCategory()
        cat.category_name = t['category_name']
        cat.price = t['price']
        cat.tevent = event
        
        t['tcategory'] = cat
        t['pk'] = t['ticket_id']
        
        ticket_rows.append({
            'ticket': t,
            'seat': seat if t['seat_id'] else None,
            'customer_name': t['username'],
            'order_code': order_code,
        })

    total_tickets = len(tickets)
    active_count = sum(1 for t in tickets if t['status'] == 'Valid')
    used_count = sum(1 for t in tickets if t['status'] == 'Terpakai')
    cancelled_count = sum(1 for t in tickets if t['status'] == 'Batal')
    
    all_events_raw = fetch_all("SELECT event_id as id, event_title as title FROM EVENT ORDER BY event_title")
    
    categories_raw = fetch_all("""
        SELECT tc.*, e.event_title as tevent_title, v.venue_name, COUNT(t.ticket_id) as used_count
        FROM TICKET_CATEGORY tc
        JOIN EVENT e ON tc.tevent_id = e.event_id
        JOIN VENUE v ON e.venue_id = v.venue_id
        LEFT JOIN TICKET t ON tc.category_id = t.tcategory_id
        GROUP BY tc.category_id, e.event_title, v.venue_name
        ORDER BY e.event_title, tc.category_name
    """)
    
    category_rows = []
    for c in categories_raw:
        class MockEvent: pass
        class MockVenue: pass
        
        venue = MockVenue()
        venue.name = c['venue_name']
        
        event = MockEvent()
        event.title = c['tevent_title']
        event.venue = venue
        
        c['tevent'] = event
        c['pk'] = c['category_id']
        
        category_rows.append({
            'category': c,
            'is_full': c['used_count'] >= c['quota'],
            'remaining': max(c['quota'] - c['used_count'], 0),
        })
        
    available_seats = fetch_all("""
        SELECT s.*, v.venue_name 
        FROM SEAT s
        JOIN VENUE v ON s.venue_id = v.venue_id
        LEFT JOIN HAS_RELATIONSHIP hr ON s.seat_id = hr.seat_id
        WHERE hr.seat_id IS NULL
        ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
    """)
    
    for s in available_seats:
        class MockVenue: pass
        venue = MockVenue()
        venue.name = s['venue_name']
        s['venue'] = venue
        s['pk'] = s['seat_id']

    context = {
        'ticket_rows': ticket_rows,
        'dummy_orders': _build_dummy_orders(all_events_raw),
        'category_rows': category_rows,
        'available_seats': available_seats,
        'status_choices': [('Valid', 'Valid'), ('Terpakai', 'Terpakai'), ('Batal', 'Batal')],
        'selected_status': status,
        'query': query,
        'total_tickets': total_tickets,
        'active_count': active_count,
        'used_count': used_count,
        'cancelled_count': cancelled_count,
        'can_create': _is_admin_or_organizer(request.user),
        'can_manage': _is_admin(request.user),
        'user_role': request.user.role,
    }
    return render(request, "ticketing/ticket_list.html", context)


@login_required
def create_ticket(request):
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        ticket_code = request.POST.get('ticket_code') or _generate_ticket_code()
        torder_id = request.POST.get('torder_id') or str(uuid.uuid4())
        tcategory_id = request.POST.get('tcategory')
        status = request.POST.get('status')
        seat_id = request.POST.get('seat')

        try:
            category = fetch_one("SELECT * FROM TICKET_CATEGORY WHERE category_id = %s", [tcategory_id])
            if not category: raise ValueError("Invalid category")
            
            used_quota = fetch_one("SELECT COUNT(*) as count FROM TICKET WHERE tcategory_id = %s", [tcategory_id])['count']
            if used_quota >= category['quota']: raise ValueError(f"Kuota kategori {category['category_name']} sudah penuh.")
            
            if seat_id:
                occupied = fetch_one("SELECT ticket_id FROM HAS_RELATIONSHIP WHERE seat_id = %s", [seat_id])
                if occupied: raise ValueError("Kursi ini sudah di-assign ke tiket lain.")
                
            ticket_id = str(uuid.uuid4())
            
            # Dummy order if doesn't exist
            order = fetch_one("SELECT order_id FROM \"ORDER\" WHERE order_id = %s", [torder_id])
            if not order:
                customer = fetch_one("SELECT customer_id FROM CUSTOMER LIMIT 1")
                if customer:
                    execute_query('INSERT INTO "ORDER" (order_id, payment_status, total_amount, customer_id) VALUES (%s, %s, %s, %s)',
                                  [torder_id, 'Pending', 0, customer['customer_id']])

            execute_query(
                "INSERT INTO TICKET (ticket_id, ticket_code, tcategory_id, torder_id, status) VALUES (%s, %s, %s, %s, %s)",
                [ticket_id, ticket_code, tcategory_id, torder_id, status]
            )
            
            if seat_id:
                execute_query("INSERT INTO HAS_RELATIONSHIP (seat_id, ticket_id) VALUES (%s, %s)", [seat_id, ticket_id])
                
            messages.success(request, 'Tiket berhasil dibuat.')
        except Exception as e:
            messages.error(request, f'Tiket gagal dibuat: {e}')
            
    return redirect('ticketing:ticket_list')


@login_required
def edit_ticket(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        ticket_code = request.POST.get('ticket_code')
        torder_id = request.POST.get('torder_id')
        tcategory_id = request.POST.get('tcategory')
        status = request.POST.get('status')
        seat_id = request.POST.get('seat')

        try:
            if seat_id:
                occupied = fetch_one("SELECT ticket_id FROM HAS_RELATIONSHIP WHERE seat_id = %s AND ticket_id != %s", [seat_id, pk])
                if occupied: raise ValueError("Kursi ini sudah di-assign ke tiket lain.")
                
            execute_query(
                "UPDATE TICKET SET ticket_code=%s, tcategory_id=%s, torder_id=%s, status=%s WHERE ticket_id=%s",
                [ticket_code, tcategory_id, torder_id, status, pk]
            )
            
            execute_query("DELETE FROM HAS_RELATIONSHIP WHERE ticket_id = %s", [pk])
            if seat_id:
                execute_query("INSERT INTO HAS_RELATIONSHIP (seat_id, ticket_id) VALUES (%s, %s)", [seat_id, pk])
                
            messages.success(request, 'Tiket berhasil diperbarui.')
        except Exception as e:
            messages.error(request, f'Tiket gagal diperbarui: {e}')
            
    return redirect('ticketing:ticket_list')


@login_required
def delete_ticket(request, pk):
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        try:
            execute_query("DELETE FROM TICKET WHERE ticket_id = %s", [pk])
            messages.success(request, 'Tiket berhasil dihapus.')
        except Exception as e:
            messages.error(request, f'Tiket gagal dihapus: {e}')
            
    return redirect('ticketing:ticket_list')

