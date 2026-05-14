<<<<<<< HEAD
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect, render
from basdat_tk03.auth import login_required
from basdat_tk03.db import fetch_all, fetch_one, execute_query
from django.utils import timezone
import uuid
=======
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Order
from .forms import OrderUpdateForm
from django.db.models import Sum, Q, CharField
from django.db.models.functions import Cast
from django.utils import timezone
from ticketing.models.event import Event
from ticketing.models.ticket_category import Ticket_Category
from promotions.models import Promotion, OrderPromotion
from decimal import Decimal
from django.contrib import messages
>>>>>>> 61b17254380ad6fb00b6f142da9d26deb3967168

@login_required
def order_list(request):
    user = request.user
<<<<<<< HEAD
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
        # Organizer only sees orders for their events
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

    # Stats
    total_order = len(orders)
    lunas = sum(1 for o in orders if o['payment_status'] == 'Paid')
    pending = sum(1 for o in orders if o['payment_status'] == 'Pending')
    total_revenue = sum(o['total_amount'] for o in orders if o['payment_status'] == 'Paid')

    stats = {
        'total_order': total_order,
        'lunas': lunas,
        'pending': pending,
        'total_revenue': total_revenue
    }

    # Format objects for template
    for o in orders:
        o['pk'] = o['order_id']
        class MockCustomer:
            pass
        c = MockCustomer()
        c.username = o['customer_username']
        # The template might use first_name / last_name, we just have full_name
        name_parts = o['customer_name'].split(' ', 1)
        c.first_name = name_parts[0]
        c.last_name = name_parts[1] if len(name_parts) > 1 else ''
        o['customer'] = c

    status_choices = [('Pending', 'Pending'), ('Paid', 'Lunas'), ('Cancelled', 'Dibatalkan')]

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'stats': stats,
        'status_choices': status_choices,
    })

def _generate_ticket_code(order_id, index):
    prefix = str(order_id).split('-')[0].upper()
    return f"TTK-{prefix}-{index + 1:03d}"

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

    # Mock venue
    class MockVenue:
        def __init__(self, name, seating_type):
            self.name = name
            self.has_reserved_seating = seating_type == 'reserved'
    event['venue'] = MockVenue(event['venue_name'], event['seating_type'])
    event['pk'] = event['event_id']

    # Categories
    categories_raw = fetch_all("SELECT * FROM TICKET_CATEGORY WHERE tevent_id = %s ORDER BY price DESC, category_name", [event_id])
    categories = []
    for cat in categories_raw:
        sold = fetch_one("SELECT COUNT(*) as count FROM TICKET WHERE tcategory_id = %s", [cat['category_id']])['count']
        remaining = max(cat['quota'] - sold, 0)
        
        # Template compatibility
        cat['pk'] = cat['category_id']
        categories.append({
            'category': cat,
            'remaining': remaining
        })
        
    default_category = categories[0]['category'] if categories else None

    # Available seats
    seats_raw = fetch_all("""
        SELECT s.* 
        FROM SEAT s
        LEFT JOIN HAS_RELATIONSHIP hr ON s.seat_id = hr.seat_id
        WHERE s.venue_id = %s AND hr.seat_id IS NULL
        ORDER BY s.section, s.row_number, s.seat_number
    """, [event['venue_id']])
    
    for s in seats_raw:
        s['pk'] = s['seat_id']

    available_seats = seats_raw

    # Active promos
    today = timezone.localdate()
    promos_raw = fetch_all("""
        SELECT * FROM PROMOTION 
        WHERE start_date <= CURRENT_DATE AND end_date >= CURRENT_DATE
        ORDER BY promo_code
    """)
    active_promos = []
    for promo in promos_raw:
        usage = fetch_one("SELECT COUNT(*) as count FROM ORDER_PROMOTION WHERE promotion_id = %s", [promo['promotion_id']])['count']
        if usage < promo['usage_limit']:
            active_promos.append(promo)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', '1'))
        except ValueError:
            quantity = 1

        promo_code = request.POST.get('promo_code', '').strip()
        category_id = request.POST.get('category_id')
        
        category = fetch_one("SELECT * FROM TICKET_CATEGORY WHERE category_id = %s AND tevent_id = %s", [category_id, event_id])
        if not category:
            messages.error(request, 'Kategori tidak valid.')
            return redirect('orders:checkout', event_id=event_id)
            
        sold = fetch_one("SELECT COUNT(*) as count FROM TICKET WHERE tcategory_id = %s", [category_id])['count']
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
                
            for sid in selected_seat_ids:
                seat = fetch_one("SELECT * FROM SEAT WHERE seat_id = %s AND venue_id = %s", [sid, event['venue_id']])
                if not seat:
                    messages.error(request, 'Kursi tidak valid.')
                    return redirect('orders:checkout', event_id=event_id)
                selected_seats.append(seat)
                
            if len(selected_seats) != len(selected_seat_ids):
                messages.error(request, 'Kursi yang dipilih tidak valid.')
                return redirect('orders:checkout', event_id=event_id)
                
            # Check occupied
            placeholders = ', '.join(['%s'] * len(selected_seat_ids))
            if placeholders:
                occupied = fetch_one(f"SELECT COUNT(*) as count FROM HAS_RELATIONSHIP WHERE seat_id IN ({placeholders})", selected_seat_ids)['count']
                if occupied > 0:
                    messages.error(request, 'Sebagian kursi sudah dipesan.')
                    return redirect('orders:checkout', event_id=event_id)

        if promo_code:
            promotion = fetch_one("SELECT * FROM PROMOTION WHERE promo_code ILIKE %s", [promo_code])
            if not promotion:
                messages.error(request, 'Kode promo tidak ditemukan.')
                return redirect('orders:checkout', event_id=event_id)
                
            p_start = str(promotion['start_date'])[:10]
            p_end = str(promotion['end_date'])[:10]
            t_day = str(today)[:10]

            if p_start > t_day or p_end < t_day:
                messages.error(request, 'Kode promo belum aktif atau sudah berakhir.')
                return redirect('orders:checkout', event_id=event_id)
                
            usage = fetch_one("SELECT COUNT(*) as count FROM ORDER_PROMOTION WHERE promotion_id = %s", [promotion['promotion_id']])['count']
            if usage >= promotion['usage_limit']:
                messages.error(request, 'Kuota promo habis.')
                return redirect('orders:checkout', event_id=event_id)

        subtotal = category['price'] * quantity
        discount = Decimal('0')
        if promotion:
            if promotion['discount_type'] == 'PERCENTAGE':
                discount = subtotal * (promotion['discount_value'] / Decimal('100'))
            else:
                discount = promotion['discount_value']
            discount = min(discount, subtotal)
            
        total_amount = subtotal - discount
        
        customer = fetch_one("SELECT customer_id FROM CUSTOMER WHERE user_id = %s", [request.user.pk])

        # Transaction simulation manually
        order_id = str(uuid.uuid4())
        try:
            execute_query(
                'INSERT INTO "ORDER" (order_id, payment_status, total_amount, customer_id) VALUES (%s, %s, %s, %s)',
                [order_id, 'Pending', total_amount, customer['customer_id']]
            )
            
            if promotion:
                execute_query(
                    'INSERT INTO ORDER_PROMOTION (order_promotion_id, promotion_id, order_id) VALUES (%s, %s, %s)',
                    [str(uuid.uuid4()), promotion['promotion_id'], order_id]
                )
                
            for index in range(quantity):
                ticket_id = str(uuid.uuid4())
                ticket_code = _generate_ticket_code(order_id, index)
                execute_query(
                    'INSERT INTO TICKET (ticket_id, ticket_code, tcategory_id, torder_id, status) VALUES (%s, %s, %s, %s, %s)',
                    [ticket_id, ticket_code, category['category_id'], order_id, 'Valid']
                )
                if event['seating_type'] == 'reserved' and index < len(selected_seats):
                    execute_query(
                        'INSERT INTO HAS_RELATIONSHIP (seat_id, ticket_id) VALUES (%s, %s)',
                        [selected_seats[index]['seat_id'], ticket_id]
                    )
            
            messages.success(request, 'Checkout berhasil. Order dibuat dengan status Pending.')
            return redirect('orders:order_list')
        except Exception as e:
            execute_query('DELETE FROM "ORDER" WHERE order_id = %s', [order_id]) # Rollback
            messages.error(request, f'Terjadi kesalahan: {e}')
            return redirect('orders:checkout', event_id=event_id)

    return render(request, 'orders/checkout.html', {
        'event': event,
        'categories': categories,
        'default_category': default_category,
        'available_seats': available_seats,
        'active_promos': active_promos,
    })

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
        # Rely on CASCADE or delete manually
        execute_query('DELETE FROM "ORDER" WHERE order_id = %s', [pk])
        messages.success(request, 'Order berhasil dihapus.')
    return redirect('orders:order_list')
=======
    
    is_admin = getattr(user, 'is_admin', user.is_staff)
    is_organizer = getattr(user, 'is_organizer', False)
    is_customer = getattr(user, 'is_customer', not is_admin and not is_organizer)

    if is_admin:
        orders = Order.objects.all()
    elif is_organizer:
        # Relasi Order ke Event belum ada, dikembalikan list kosong sementara
        orders = Order.objects.none()
    else:
        orders = Order.objects.filter(customer=user)

    # Search and Filter
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    
    # Cast id to string for searching UUIDs
    orders = orders.annotate(id_str=Cast('id', output_field=CharField()))

    if search:
        if is_customer:
            orders = orders.filter(id_str__icontains=search)
        else:
            orders = orders.filter(Q(id_str__icontains=search) | Q(customer__username__icontains=search))

    if status:
        orders = orders.filter(payment_status=status)

    total_orders = orders.count()
    paid = orders.filter(payment_status='PAID').count()
    pending = orders.filter(payment_status='PENDING').count()
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    context = {
        'orders': orders.order_by('-order_date'),
        'total_orders': total_orders,
        'paid': paid,
        'pending': pending,
        'total_revenue': total_revenue,
        'is_admin': is_admin,
        'is_organizer': is_organizer,
        'is_customer': is_customer,
    }

    return render(request, 'orders/list.html', context)


@login_required
def checkout(request, event_id):
    # Only customers can create orders based on scenario
    is_admin = getattr(request.user, 'is_admin', request.user.is_staff)
    is_organizer = getattr(request.user, 'is_organizer', False)
    
    if is_admin or is_organizer:
        messages.error(request, "Hanya Customer yang dapat membeli tiket.")
        return redirect('orders:list')

    event = get_object_or_404(Event, pk=event_id)
    categories = event.ticket_categories.all()

    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        quantity = request.POST.get('quantity')
        promo_code = request.POST.get('promo_code', '').strip()

        try:
            quantity = int(quantity)
            if quantity < 1 or quantity > 10:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Jumlah tiket harus berupa bilangan bulat antara 1 hingga 10.")
            return redirect('orders:checkout', event_id=event.id)

        if not category_id:
            messages.error(request, "Silakan pilih kategori tiket.")
            return redirect('orders:checkout', event_id=event.id)

        category = get_object_or_404(Ticket_Category, pk=category_id, tevent=event)
        
        base_price = category.price * quantity
        discount = Decimal('0.00')
        promotion_obj = None

        if promo_code:
            try:
                promotion_obj = Promotion.objects.get(promo_code=promo_code)
                # Check active and usage limit
                if promotion_obj.is_active and promotion_obj.order_promotions.count() < promotion_obj.usage_limit:
                    if promotion_obj.discount_type == 'PERCENTAGE':
                        discount = base_price * (promotion_obj.discount_value / Decimal('100.00'))
                    else:
                        discount = promotion_obj.discount_value
                    
                    if discount > base_price:
                        discount = base_price
                else:
                    messages.warning(request, "Kode promo tidak aktif atau telah mencapai batas penggunaan.")
                    return redirect('orders:checkout', event_id=event.id)
            except Promotion.DoesNotExist:
                messages.warning(request, "Kode promo tidak valid.")
                return redirect('orders:checkout', event_id=event.id)

        total_amount = base_price - discount

        # Create Order
        order = Order.objects.create(
            customer=request.user,
            payment_status='PENDING',
            total_amount=total_amount
        )

        if promotion_obj:
            OrderPromotion.objects.create(order=order, promotion=promotion_obj)

        messages.success(request, "Pesanan berhasil dibuat!")
        return redirect('orders:list')

    context = {
        'event': event,
        'categories': categories,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def update_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    is_admin = getattr(request.user, 'is_admin', request.user.is_staff)
    if not is_admin:
        messages.error(request, "Hanya Admin yang dapat mengubah status pesanan.")
        return redirect('orders:list')

    if request.method == 'POST':
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, "Data order berhasil diperbarui.")
            return redirect('orders:list')
    else:
        form = OrderUpdateForm(instance=order)

    return render(request, 'orders/update_modal.html', {'form': form, 'order': order})


@login_required
def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    is_admin = getattr(request.user, 'is_admin', request.user.is_staff)
    if not is_admin:
        messages.error(request, "Hanya Admin yang dapat menghapus pesanan.")
        return redirect('orders:list')

    if request.method == 'POST':
        order.delete()
        messages.success(request, "Data order berhasil dihapus.")
        return redirect('orders:list')

    return render(request, 'orders/delete_confirm.html', {'order': order})
>>>>>>> 61b17254380ad6fb00b6f142da9d26deb3967168
