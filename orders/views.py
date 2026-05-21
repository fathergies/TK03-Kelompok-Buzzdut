from decimal import Decimal
import uuid

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render

from basdat_tk03.auth import login_required
from basdat_tk03.db import execute_query, fetch_all, fetch_one


def _generate_ticket_code(order_id, index):
    prefix = str(order_id).split('-')[0].upper()
    return f"TTK-{prefix}-{index + 1:03d}"


def _database_error_message(error):
    diag = getattr(error, "diag", None)
    message = getattr(diag, "message_primary", None) or str(error)
    message = message.strip().splitlines()[0]
    return message


def _is_order_promotion_trigger_error(error):
    text = str(error)
    message = _database_error_message(error)
    return (
        "validate_order_promotion" in text
        or "trg_validate_order_promotion" in text
        or message.startswith("ERROR: Promotion")
    )


def _date_string(value):
    if hasattr(value, 'date'):
        value = value.date()
    return str(value)[:10]


def _validate_promotion_for_event(promo_code, event):
    promo_code = (promo_code or '').strip()
    if not promo_code:
        return None, 'Kode promo wajib diisi.'

    promotion = fetch_one("SELECT * FROM PROMOTION WHERE promo_code ILIKE %s", [promo_code])
    if not promotion:
        return None, f'ERROR: Promotion dengan ID {promo_code.upper()} tidak ditemukan.'

    usage = fetch_one(
        "SELECT COUNT(*) as count FROM ORDER_PROMOTION WHERE promotion_id = %s",
        [promotion['promotion_id']],
    )['count']
    if usage >= promotion['usage_limit']:
        return None, f'ERROR: Promotion {promo_code.upper()} telah mencapai batas maksimum penggunaan.'

    event_day = _date_string(event['event_datetime'])
    promo_start = _date_string(promotion['start_date'])
    promo_end = _date_string(promotion['end_date'])
    if promo_start > event_day or promo_end < event_day:
        return None, f'ERROR: Promotion {promo_code.upper()} tidak berlaku untuk tanggal event ini.'

    return promotion, None


def _calculate_discount(subtotal, promotion):
    if not promotion:
        return Decimal('0')
    if promotion['discount_type'] == 'PERCENTAGE':
        discount = subtotal * (promotion['discount_value'] / Decimal('100'))
    else:
        discount = promotion['discount_value']
    return min(discount, subtotal)


@login_required
def order_list(request):
    user = request.user
    role = user.role.upper()

    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    base_query = """
        SELECT o.order_id as id, o.order_id, o.order_date, o.payment_status, o.total_amount,
               c.full_name as customer_name, ua.username as customer_username
        FROM "ORDER" o
        JOIN CUSTOMER c ON o.customer_id = c.customer_id
        JOIN USER_ACCOUNT ua ON c.user_id = ua.user_id
        WHERE 1=1
    """
    params = []

    if role == 'CUSTOMER':
        base_query += " AND c.user_id = %s"
        params.append(user.pk)
    elif role == 'ORGANIZER':
        base_query += """
            AND o.order_id IN (
                SELECT t.torder_id
                FROM TICKET t
                JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
                JOIN EVENT e ON tc.tevent_id = e.event_id
                JOIN ORGANIZER org ON e.organizer_id = org.organizer_id
                WHERE org.user_id = %s
            )
        """
        params.append(user.pk)

    if search:
        base_query += " AND (o.order_id::text ILIKE %s OR ua.username ILIKE %s OR c.full_name ILIKE %s)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if status:
        base_query += " AND o.payment_status = %s"
        params.append(status)

    base_query += " ORDER BY o.order_date DESC"
    orders = fetch_all(base_query, params)

    stats = {
        'total_order': len(orders),
        'lunas': sum(1 for order in orders if order['payment_status'] == 'Paid'),
        'pending': sum(1 for order in orders if order['payment_status'] == 'Pending'),
        'total_revenue': sum(order['total_amount'] for order in orders if order['payment_status'] == 'Paid'),
    }

    for order in orders:
        order['pk'] = order['order_id']

        class MockCustomer:
            pass

        customer = MockCustomer()
        customer.username = order['customer_username']
        name_parts = order['customer_name'].split(' ', 1)
        customer.first_name = name_parts[0]
        customer.last_name = name_parts[1] if len(name_parts) > 1 else ''
        order['customer'] = customer

    status_choices = [('Pending', 'Pending'), ('Paid', 'Lunas'), ('Cancelled', 'Dibatalkan')]

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'stats': stats,
        'status_choices': status_choices,
    })


@login_required
def apply_promo(request, event_id):
    if request.user.role != 'CUSTOMER':
        return JsonResponse({'ok': False, 'message': 'Promo hanya dapat digunakan oleh pelanggan.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'message': 'Method tidak valid.'}, status=405)

    event = fetch_one("SELECT event_id, event_datetime FROM EVENT WHERE event_id = %s", [str(event_id)])
    if not event:
        return JsonResponse({'ok': False, 'message': 'Event tidak ditemukan.'}, status=404)

    category = fetch_one(
        "SELECT price FROM TICKET_CATEGORY WHERE category_id = %s AND tevent_id = %s",
        [request.POST.get('category_id'), str(event_id)],
    )
    if not category:
        return JsonResponse({'ok': False, 'message': 'Kategori tidak valid.'}, status=400)

    try:
        quantity = int(request.POST.get('quantity', '1'))
    except ValueError:
        quantity = 1
    quantity = max(1, min(quantity, 10))

    promotion, error_message = _validate_promotion_for_event(request.POST.get('promo_code'), event)
    if error_message:
        return JsonResponse({'ok': False, 'message': error_message}, status=400)

    subtotal = category['price'] * quantity
    discount = _calculate_discount(subtotal, promotion)
    total = subtotal - discount

    return JsonResponse({
        'ok': True,
        'message': f'Promo {promotion["promo_code"]} berhasil diterapkan.',
        'promo_code': promotion['promo_code'],
        'discount': float(discount),
        'total': float(total),
    })


@login_required
def checkout(request, event_id):
    event_id = str(event_id)
    if request.user.role != 'CUSTOMER':
        messages.error(request, 'Checkout hanya tersedia untuk pelanggan.')
        return redirect('ticketing:show_ticket_categories')

    event = fetch_one("""
        SELECT e.*, v.venue_name, v.seating_type
        FROM EVENT e
        JOIN VENUE v ON e.venue_id = v.venue_id
        WHERE e.event_id = %s
    """, [event_id])

    if not event:
        messages.error(request, 'Event tidak ditemukan.')
        return redirect('events:event_list')

    class MockVenue:
        def __init__(self, name, seating_type):
            self.name = name
            self.has_reserved_seating = seating_type == 'reserved'

    event['venue'] = MockVenue(event['venue_name'], event['seating_type'])
    event['pk'] = event['event_id']

    categories_raw = fetch_all(
        "SELECT * FROM TICKET_CATEGORY WHERE tevent_id = %s ORDER BY price DESC, category_name",
        [event_id],
    )
    categories = []
    for category in categories_raw:
        sold = fetch_one(
            "SELECT COUNT(*) as count FROM TICKET WHERE tcategory_id = %s",
            [category['category_id']],
        )['count']
        category['pk'] = category['category_id']
        categories.append({
            'category': category,
            'remaining': max(category['quota'] - sold, 0),
        })

    default_category = categories[0]['category'] if categories else None

    seats_raw = fetch_all("""
        SELECT s.*
        FROM SEAT s
        LEFT JOIN HAS_RELATIONSHIP hr ON s.seat_id = hr.seat_id
        WHERE s.venue_id = %s AND hr.seat_id IS NULL
        ORDER BY s.section, s.row_number, s.seat_number
    """, [event['venue_id']])

    for seat in seats_raw:
        seat['pk'] = seat['seat_id']

    promos_raw = fetch_all("""
        SELECT *
        FROM PROMOTION
        WHERE start_date <= %s AND end_date >= %s
        ORDER BY promo_code
    """, [_date_string(event['event_datetime']), _date_string(event['event_datetime'])])
    active_promos = []
    for promo in promos_raw:
        usage = fetch_one(
            "SELECT COUNT(*) as count FROM ORDER_PROMOTION WHERE promotion_id = %s",
            [promo['promotion_id']],
        )['count']
        if usage < promo['usage_limit']:
            active_promos.append(promo)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', '1'))
        except ValueError:
            quantity = 1

        promo_code = request.POST.get('applied_promo_code', '').strip()
        category_id = request.POST.get('category_id')

        category = fetch_one(
            "SELECT * FROM TICKET_CATEGORY WHERE category_id = %s AND tevent_id = %s",
            [category_id, event_id],
        )
        if not category:
            messages.error(request, 'Kategori tidak valid.')
            return redirect('orders:checkout', event_id=event_id)

        sold = fetch_one(
            "SELECT COUNT(*) as count FROM TICKET WHERE tcategory_id = %s",
            [category_id],
        )['count']
        available_quota = max(category['quota'] - sold, 0)

        selected_seat_ids = request.POST.getlist('seat_ids')
        promotion = None

        if quantity < 1 or quantity > 10:
            messages.error(request, 'Jumlah tiket harus 1-10.')
            return redirect('orders:checkout', event_id=event_id)

        if quantity > available_quota:
            messages.error(request, 'Jumlah tiket melebihi kuota tersedia.')
            return redirect('orders:checkout', event_id=event_id)

        selected_seats = []
        if event['seating_type'] == 'reserved':
            if len(selected_seat_ids) > quantity:
                messages.error(request, 'Jumlah kursi tidak boleh melebihi jumlah tiket.')
                return redirect('orders:checkout', event_id=event_id)

            for seat_id in selected_seat_ids:
                seat = fetch_one(
                    "SELECT * FROM SEAT WHERE seat_id = %s AND venue_id = %s",
                    [seat_id, event['venue_id']],
                )
                if not seat:
                    messages.error(request, 'Kursi tidak valid.')
                    return redirect('orders:checkout', event_id=event_id)
                selected_seats.append(seat)

            placeholders = ', '.join(['%s'] * len(selected_seat_ids))
            if placeholders:
                occupied = fetch_one(
                    f"SELECT COUNT(*) as count FROM HAS_RELATIONSHIP WHERE seat_id IN ({placeholders})",
                    selected_seat_ids,
                )['count']
                if occupied > 0:
                    messages.error(request, 'Sebagian kursi sudah dipesan.')
                    return redirect('orders:checkout', event_id=event_id)

        if promo_code:
            promotion, error_message = _validate_promotion_for_event(promo_code, event)
            if error_message:
                messages.error(request, error_message)
                return redirect('orders:checkout', event_id=event_id)

        subtotal = category['price'] * quantity
        discount = _calculate_discount(subtotal, promotion)
        total_amount = subtotal - discount
        customer = fetch_one("SELECT customer_id FROM CUSTOMER WHERE user_id = %s", [request.user.pk])
        order_id = str(uuid.uuid4())

        try:
            execute_query(
                'INSERT INTO "ORDER" (order_id, payment_status, total_amount, customer_id) VALUES (%s, %s, %s, %s)',
                [order_id, 'Pending', total_amount, customer['customer_id']],
            )

            for index in range(quantity):
                ticket_id = str(uuid.uuid4())
                execute_query(
                    'INSERT INTO TICKET (ticket_id, ticket_code, tcategory_id, torder_id, status) VALUES (%s, %s, %s, %s, %s)',
                    [ticket_id, _generate_ticket_code(order_id, index), category['category_id'], order_id, 'Valid'],
                )
                if event['seating_type'] == 'reserved' and index < len(selected_seats):
                    execute_query(
                        'INSERT INTO HAS_RELATIONSHIP (seat_id, ticket_id) VALUES (%s, %s)',
                        [selected_seats[index]['seat_id'], ticket_id],
                    )

            if promotion:
                execute_query(
                    'INSERT INTO ORDER_PROMOTION (order_promotion_id, promotion_id, order_id) VALUES (%s, %s, %s)',
                    [str(uuid.uuid4()), promotion['promotion_id'], order_id],
                )

            messages.success(request, 'Checkout berhasil. Order dibuat dengan status Pending.')
            return redirect('orders:order_list')
        except Exception as error:
            try:
                execute_query('DELETE FROM "ORDER" WHERE order_id = %s', [order_id])
            except Exception:
                pass

            message = _database_error_message(error)
            if _is_order_promotion_trigger_error(error):
                messages.error(request, message, extra_tags='trigger_error')
            else:
                messages.error(request, f'Terjadi kesalahan: {message}')
            return redirect('orders:checkout', event_id=event_id)

    return render(request, 'orders/checkout.html', {
        'event': event,
        'categories': categories,
        'default_category': default_category,
        'available_seats': seats_raw,
        'active_promos': active_promos,
    })


@login_required
def order_detail(request, pk):
    pk = str(pk)
    role = request.user.role.upper()

    query = """
        SELECT o.order_id, o.order_date, o.payment_status, o.total_amount,
               c.full_name as customer_name, ua.username as customer_username
        FROM "ORDER" o
        JOIN CUSTOMER c ON o.customer_id = c.customer_id
        JOIN USER_ACCOUNT ua ON c.user_id = ua.user_id
        WHERE o.order_id = %s
    """
    params = [pk]

    if role == 'CUSTOMER':
        query += " AND c.user_id = %s"
        params.append(request.user.pk)
    elif role == 'ORGANIZER':
        query += """
            AND o.order_id IN (
                SELECT t.torder_id
                FROM TICKET t
                JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
                JOIN EVENT e ON tc.tevent_id = e.event_id
                JOIN ORGANIZER org ON e.organizer_id = org.organizer_id
                WHERE org.user_id = %s
            )
        """
        params.append(request.user.pk)

    order = fetch_one(query, params)
    if not order:
        messages.error(request, 'Order tidak ditemukan.')
        return redirect('orders:order_list')

    class MockCustomer:
        pass

    customer = MockCustomer()
    customer.full_name = order['customer_name']
    customer.username = order['customer_username']
    order['customer'] = customer

    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def update_order(request, pk):
    pk = str(pk)
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat mengubah order.')
        return redirect('orders:order_list')

    if request.method == 'POST':
        payment_status = request.POST.get('payment_status')
        if payment_status in ['Pending', 'Paid', 'Cancelled']:
            execute_query('UPDATE "ORDER" SET payment_status = %s WHERE order_id = %s', [payment_status, pk])
            messages.success(request, 'Status order berhasil diperbarui.')
        else:
            messages.error(request, 'Status order tidak valid.')
    return redirect('orders:order_list')


@login_required
def delete_order(request, pk):
    pk = str(pk)
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat menghapus order.')
        return redirect('orders:order_list')

    if request.method == 'POST':
        execute_query('DELETE FROM "ORDER" WHERE order_id = %s', [pk])
        messages.success(request, 'Order berhasil dihapus.')
    return redirect('orders:order_list')
