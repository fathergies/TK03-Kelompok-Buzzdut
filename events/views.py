from django.shortcuts import render, redirect
from basdat_tk03.auth import login_required
from django.contrib import messages
from datetime import datetime
import uuid

from basdat_tk03.db import fetch_all, fetch_one, execute_query

def get_event_list_context(request):
    query = request.GET.get('q', '')
    venue_filter = request.GET.get('venue', '')
    artist_filter = request.GET.get('artist', '')

    # Base query for events
    sql_events = """
        SELECT 
            e.event_id as pk,
            e.event_id,
            e.event_title as title, 
            e.event_datetime as start_date,
            e.image_url,
            e.organizer_id,
            v.venue_name,
            v.city,
            COALESCE(MIN(tc.price), 0) as min_price
        FROM EVENT e
        JOIN VENUE v ON e.venue_id = v.venue_id
        LEFT JOIN TICKET_CATEGORY tc ON e.event_id = tc.tevent_id
    """
    
    where_clauses = ["1=1"]
    params = []

    if query:
        where_clauses.append("(e.event_title ILIKE %s OR e.event_id IN (SELECT event_id FROM EVENT_ARTIST ea JOIN ARTIST a ON ea.artist_id = a.artist_id WHERE a.name ILIKE %s))")
        params.extend([f"%{query}%", f"%{query}%"])
    
    if venue_filter:
        where_clauses.append("e.venue_id = %s")
        params.append(venue_filter)
        
    if artist_filter:
        where_clauses.append("e.event_id IN (SELECT event_id FROM EVENT_ARTIST WHERE artist_id = %s)")
        params.append(artist_filter)
        
    sql_events += " WHERE " + " AND ".join(where_clauses)
    sql_events += " GROUP BY e.event_id, e.event_title, e.event_datetime, e.image_url, e.organizer_id, v.venue_name, v.city ORDER BY e.event_datetime ASC"
    
    events_raw = fetch_all(sql_events, params)
    
    # Manually stitch artist names and ticket categories for each event
    for evt in events_raw:
        artists_data = fetch_all("SELECT a.name FROM EVENT_ARTIST ea JOIN ARTIST a ON ea.artist_id = a.artist_id WHERE ea.event_id = %s", [evt['event_id']])
        evt['artist_names'] = ", ".join([a['name'] for a in artists_data])
        evt['artists'] = artists_data
        
        cats_data = fetch_all("SELECT category_name, price FROM TICKET_CATEGORY WHERE tevent_id = %s", [evt['event_id']])
        evt['ticket_categories'] = cats_data
        
        # Mocking an object-like interface for the template if it expects event.venue.name
        class MockVenue:
            def __init__(self, name, city):
                self.name = name
                self.city = city
        evt['venue'] = MockVenue(evt['venue_name'], evt.get('city', ''))

    venues = fetch_all("SELECT venue_id as pk, venue_name as name FROM VENUE ORDER BY venue_name ASC")
    artists = fetch_all("SELECT artist_id as pk, name FROM ARTIST ORDER BY name ASC")

    return {
        'events': events_raw,
        'venues': venues,
        'artists': artists,
        'query': query,
        'venue_filter': venue_filter,
        'artist_filter': artist_filter,
    }

def event_list(request):
    context = get_event_list_context(request)
    # We pass empty form data since we don't use Django Forms anymore
    context['show_modal'] = False
    return render(request, 'events/event_list.html', context)

@login_required
def event_create(request):
    if request.user.role not in ['ADMIN', 'ORGANIZER']:
        messages.error(request, 'Hanya Admin dan Organizer yang dapat membuat acara.')
        return redirect('events:event_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        venue_id = request.POST.get('venue')
        description = request.POST.get('description')
        start_datetime = request.POST.get('start_datetime')
        artists_ids = request.POST.getlist('artists')
        
        category_names = request.POST.getlist('category_name[]')
        prices = request.POST.getlist('price[]')
        quotas = request.POST.getlist('quota[]')
        
        if not title or not venue_id or not start_datetime:
            messages.error(request, 'Data tidak lengkap.')
            return redirect('events:event_list')
            
        # Get organizer ID
        org = fetch_one("SELECT organizer_id FROM ORGANIZER WHERE user_id = %s", [request.user.pk])
        if not org and request.user.role == 'ORGANIZER':
            messages.error(request, 'Data organizer tidak ditemukan.')
            return redirect('events:event_list')
            
        organizer_id = org['organizer_id'] if org else '40000000-0000-4000-8000-000000000001' # Fallback for admin
            
        event_id = str(uuid.uuid4())
        
        try:
            # Create Event
            execute_query(
                "INSERT INTO EVENT (event_id, event_datetime, event_title, description, venue_id, organizer_id) VALUES (%s, %s, %s, %s, %s, %s)",
                [event_id, start_datetime, title, description, venue_id, organizer_id]
            )
            
            # Create Event Artists
            for artist_id in artists_ids:
                execute_query("INSERT INTO EVENT_ARTIST (event_id, artist_id) VALUES (%s, %s)", [event_id, artist_id])
                
            # Create Ticket Categories
            for i in range(len(category_names)):
                name = category_names[i].strip()
                price = prices[i]
                quota = quotas[i]
                if name and price and quota:
                    execute_query(
                        "INSERT INTO TICKET_CATEGORY (category_id, category_name, quota, price, tevent_id) VALUES (%s, %s, %s, %s, %s)",
                        [str(uuid.uuid4()), name, int(quota), float(price), event_id]
                    )
                    
            messages.success(request, 'Acara berhasil dibuat!')
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan saat menyimpan data: {str(e)}')
            
        return redirect('events:event_list')
            
    return redirect('events:event_list')

@login_required
def event_update(request, pk):
    event_raw = fetch_one("SELECT * FROM EVENT WHERE event_id = %s", [pk])
    if not event_raw:
        messages.error(request, 'Acara tidak ditemukan.')
        return redirect('events:event_list')
        
    org = fetch_one("SELECT organizer_id FROM ORGANIZER WHERE user_id = %s", [request.user.pk])
    organizer_id = org['organizer_id'] if org else None

    if event_raw['organizer_id'] != organizer_id and request.user.role != 'ADMIN':
        messages.error(request, 'Anda tidak memiliki akses untuk mengubah acara ini.')
        return redirect('events:event_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        venue_id = request.POST.get('venue')
        description = request.POST.get('description')
        start_datetime = request.POST.get('start_datetime')
        artists_ids = request.POST.getlist('artists')
        
        try:
            # Update Event
            execute_query(
                "UPDATE EVENT SET event_title=%s, event_datetime=%s, description=%s, venue_id=%s WHERE event_id=%s",
                [title, start_datetime, description, venue_id, pk]
            )
            
            # Update Artists
            execute_query("DELETE FROM EVENT_ARTIST WHERE event_id=%s", [pk])
            for artist_id in artists_ids:
                execute_query("INSERT INTO EVENT_ARTIST (event_id, artist_id) VALUES (%s, %s)", [pk, artist_id])
                
            # Update Categories (Delete all and re-insert for simplicity)
            execute_query("DELETE FROM TICKET_CATEGORY WHERE tevent_id=%s", [pk])
            category_names = request.POST.getlist('category_name[]')
            prices = request.POST.getlist('price[]')
            quotas = request.POST.getlist('quota[]')
            
            for i in range(len(category_names)):
                name = category_names[i].strip()
                price = prices[i]
                quota = quotas[i]
                if name and price and quota:
                    execute_query(
                        "INSERT INTO TICKET_CATEGORY (category_id, category_name, quota, price, tevent_id) VALUES (%s, %s, %s, %s, %s)",
                        [str(uuid.uuid4()), name, int(quota), float(price), pk]
                    )
            
            messages.success(request, 'Acara berhasil diperbarui!')
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan saat mengupdate data: {str(e)}')
            
        return redirect('events:event_list')

    # Prepare data for template
    event_raw['pk'] = event_raw['event_id']
    event_raw['title'] = event_raw['event_title']
    event_raw['start_date'] = event_raw['event_datetime']
    
    categories = fetch_all("SELECT * FROM TICKET_CATEGORY WHERE tevent_id = %s", [pk])
    venues = fetch_all("SELECT venue_id as pk, venue_name as name FROM VENUE ORDER BY venue_name ASC")
    artists = fetch_all("SELECT artist_id as pk, name FROM ARTIST ORDER BY name ASC")
    
    current_artists = fetch_all("SELECT artist_id FROM EVENT_ARTIST WHERE event_id = %s", [pk])
    current_artist_ids = [str(a['artist_id']) for a in current_artists]
    
    return render(request, 'events/event_form.html', {
        'title': 'Edit Acara', 
        'event': event_raw,
        'categories': categories,
        'venues': venues,
        'artists': artists,
        'current_artist_ids': current_artist_ids,
        'is_raw_sql': True
    })
