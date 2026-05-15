from django.shortcuts import render, redirect
from django.contrib import messages
from basdat_tk03.auth import login_required
from basdat_tk03.db import fetch_all, fetch_one, execute_query, get_database_error_message
import uuid
import psycopg2
def get_user_role(request):
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role:
        return str(request.user.role)
    return request.session.get('role', 'CUSTOMER')


def is_admin_or_organizer(request):
    role = get_user_role(request).upper()
    return role in ['ADMIN', 'ORGANIZER']


@login_required
def venue_list(request):
    query = request.GET.get('q', '').strip()
    selected_city = request.GET.get('city', '').strip()
    selected_seating = request.GET.get('seating', '').strip()

    sql_query = "SELECT * FROM VENUE WHERE 1=1"
    params = []

    if query:
        sql_query += " AND (venue_name ILIKE %s OR address ILIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])
    
    if selected_city:
        sql_query += " AND city ILIKE %s"
        params.append(selected_city)
        
    if selected_seating == 'reserved':
        sql_query += " AND seating_type = 'reserved'"
    elif selected_seating == 'free':
        sql_query += " AND seating_type = 'free'"
        
    sql_query += " ORDER BY venue_name ASC;"
    
    venues = fetch_all(sql_query, params)
    for v in venues:
        v['id'] = v['venue_id']
        v['name'] = v['venue_name']
        v['has_reserved_seating'] = (v['seating_type'] == 'reserved')

    cities_result = fetch_all("SELECT DISTINCT city FROM VENUE ORDER BY city ASC;")
    cities = [row['city'] for row in cities_result]

    total_venues_res = fetch_one("SELECT COUNT(*) as count FROM VENUE;")
    total_venues = total_venues_res['count'] if total_venues_res else 0

    reserved_count_res = fetch_one("SELECT COUNT(*) as count FROM VENUE WHERE seating_type = 'reserved';")
    reserved_count = reserved_count_res['count'] if reserved_count_res else 0

    total_capacity_res = fetch_one("SELECT SUM(capacity) as total FROM VENUE;")
    total_capacity = total_capacity_res['total'] if total_capacity_res and total_capacity_res['total'] else 0

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
        venue_name = request.POST.get('name')
        capacity = request.POST.get('capacity')
        address = request.POST.get('address')
        city = request.POST.get('city')
        has_reserved = request.POST.get('has_reserved_seating') == 'on'
        seating_type = 'reserved' if has_reserved else 'free'
        
        if venue_name and capacity and address and city:
            try:
                execute_query(
                    "INSERT INTO VENUE (venue_id, venue_name, capacity, address, city, seating_type) VALUES (%s, %s, %s, %s, %s, %s);",
                    [str(uuid.uuid4()), venue_name, int(capacity), address, city, seating_type]
                )
                messages.success(request, 'Venue berhasil ditambahkan.')
            except psycopg2.DatabaseError as e:
                messages.error(request, get_database_error_message(e), extra_tags='trigger_error')
            except Exception as e:
                messages.error(request, f'Venue gagal ditambahkan: {e}')
        else:
            messages.error(request, 'Venue gagal ditambahkan. Pastikan semua data sudah benar.')
    return redirect('venue_list')


@login_required
def venue_update(request, venue_id):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Anda tidak memiliki akses untuk mengubah venue.')
        return redirect('venue_list')

    if request.method == 'POST':
        venue_name = request.POST.get('name')
        capacity = request.POST.get('capacity')
        address = request.POST.get('address')
        city = request.POST.get('city')
        has_reserved = request.POST.get('has_reserved_seating') == 'on'
        seating_type = 'reserved' if has_reserved else 'free'
        
        if venue_name and capacity and address and city:
            try:
                execute_query(
                    "UPDATE VENUE SET venue_name=%s, capacity=%s, address=%s, city=%s, seating_type=%s WHERE venue_id=%s;",
                    [venue_name, int(capacity), address, city, seating_type, venue_id]
                )
                messages.success(request, 'Venue berhasil diperbarui.')
            except psycopg2.DatabaseError as e:
                messages.error(request, get_database_error_message(e), extra_tags='trigger_error')
            except Exception as e:
                messages.error(request, f'Venue gagal diperbarui: {e}')
        else:
            messages.error(request, 'Venue gagal diperbarui. Pastikan semua data sudah benar.')
    return redirect('venue_list')


@login_required
def venue_delete(request, venue_id):
    if not is_admin_or_organizer(request):
        messages.error(request, 'Anda tidak memiliki akses untuk menghapus venue.')
        return redirect('venue_list')

    if request.method == 'POST':
        try:
            execute_query("DELETE FROM VENUE WHERE venue_id=%s;", [venue_id])
            messages.success(request, 'Venue berhasil dihapus.')
        except psycopg2.DatabaseError as e:
            messages.error(request, get_database_error_message(e), extra_tags='trigger_error')
        except Exception as e:
            messages.error(request, f'Venue gagal dihapus: {e}')
    return redirect('venue_list')
