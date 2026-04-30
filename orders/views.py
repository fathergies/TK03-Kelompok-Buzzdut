from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Order
from promotions.models import Promotion
from ticketing.models import Event, HasRelationship, Seat, Ticket, Ticket_Category

@login_required
def order_list(request):
    user = request.user
    orders = Order.objects.all().order_by('-order_date')

    # R-Order: Filter berdasarkan Role
    if user.role == 'CUSTOMER':
        orders = orders.filter(customer=user)
    elif user.role == 'ORGANIZER':
        organizer_order_ids = (
            Ticket.objects
            .filter(tcategory__tevent__organizer=user)
            .values_list('torder_id', flat=True)
            .distinct()
        )
        orders = orders.filter(id__in=organizer_order_ids)

    # Statistik Ringkasan
    stats = {
        'total_order': orders.count(),
        'lunas': orders.filter(payment_status='Lunas').count(),
        'pending': orders.filter(payment_status='Pending').count(),
        'total_revenue': orders.filter(payment_status='Lunas').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    }

    # Search & Filter
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(customer__username__icontains=search) |
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search)
        )
    if status:
        orders = orders.filter(payment_status=status)

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'stats': stats,
        'status_choices': Order.STATUS_CHOICES,
    })


def _generate_ticket_code(order_id, index):
    prefix = str(order_id).split('-')[0].upper()
    return f"TTK-{prefix}-{index + 1:03d}"


def _calculate_discount(promotion, subtotal):
    if not promotion:
        return Decimal('0')
    if promotion.discount_type == 'Persentase':
        discount = subtotal * (promotion.discount_value / Decimal('100'))
    else:
        discount = promotion.discount_value
    return min(discount, subtotal)


def _promotion_usage(promotion):
    return Order.objects.filter(promotion=promotion).count()


def _category_rows(event):
    rows = []
    for category in event.ticket_categories.all().order_by('-price', 'category_name'):
        sold_count = Ticket.objects.filter(tcategory=category).count()
        remaining = max(category.quota - sold_count, 0)
        rows.append({
            'category': category,
            'remaining': remaining,
        })
    return rows


@login_required
def checkout(request, event_id):
    if request.user.role != 'CUSTOMER':
        messages.error(request, 'Checkout hanya tersedia untuk pelanggan.')
        return redirect('ticketing:show_ticket_categories')

    event = get_object_or_404(
        Event.objects.select_related('venue').prefetch_related('ticket_categories'),
        pk=event_id,
    )
    categories = _category_rows(event)
    default_category = categories[0]['category'] if categories else None
    available_seats = Seat.objects.filter(venue=event.venue).exclude(
        seat_id__in=HasRelationship.objects.values_list('seat_id', flat=True)
    ).order_by('section', 'row_number', 'seat_number')
    active_promos = [
        promo for promo in Promotion.objects.order_by('code')
        if promo.start_date <= timezone.localdate() <= promo.end_date
        and _promotion_usage(promo) < promo.usage_limit
    ]

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', '1'))
        except ValueError:
            quantity = 1

        promo_code = request.POST.get('promo_code', '').strip()
        category = get_object_or_404(Ticket_Category, pk=request.POST.get('category_id'), tevent=event)
        sold_count = Ticket.objects.filter(tcategory=category).count()
        available_quota = max(category.quota - sold_count, 0)
        selected_seat_ids = request.POST.getlist('seat_ids')
        promotion = None
        if quantity < 1:
            messages.error(request, 'Jumlah tiket minimal 1.')
            return redirect('orders:checkout', event_id=event.pk)
        if quantity > 10:
            messages.error(request, 'Maksimal 10 tiket per transaksi.')
            return redirect('orders:checkout', event_id=event.pk)
        if quantity > available_quota:
            messages.error(request, 'Jumlah tiket melebihi kuota tersedia.')
            return redirect('orders:checkout', event_id=event.pk)

        selected_seats = Seat.objects.none()
        if event.venue.has_reserved_seating:
            if len(selected_seat_ids) > quantity:
                messages.error(request, 'Jumlah kursi tidak boleh melebihi jumlah tiket.')
                return redirect('orders:checkout', event_id=event.pk)
            selected_seats = Seat.objects.filter(seat_id__in=selected_seat_ids, venue=event.venue)
            if selected_seats.count() != len(selected_seat_ids):
                messages.error(request, 'Kursi yang dipilih tidak valid.')
                return redirect('orders:checkout', event_id=event.pk)
            occupied_count = HasRelationship.objects.filter(seat_id__in=selected_seat_ids).count()
            if occupied_count:
                messages.error(request, 'Sebagian kursi yang dipilih sudah dipesan.')
                return redirect('orders:checkout', event_id=event.pk)

        if promo_code:
            today = timezone.localdate()
            promotion = Promotion.objects.filter(code__iexact=promo_code).first()
            if not promotion:
                messages.error(request, 'Kode promo tidak ditemukan.')
                return redirect('orders:checkout', event_id=event.pk)
            if not (promotion.start_date <= today <= promotion.end_date):
                messages.error(request, 'Kode promo belum aktif atau sudah berakhir.')
                return redirect('orders:checkout', event_id=event.pk)
            if _promotion_usage(promotion) >= promotion.usage_limit:
                messages.error(request, 'Kuota penggunaan promo sudah habis.')
                return redirect('orders:checkout', event_id=event.pk)

        subtotal = category.price * quantity
        discount = _calculate_discount(promotion, subtotal)
        total_amount = subtotal - discount

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                payment_status='Pending',
                total_amount=total_amount,
                promotion=promotion,
            )
            seats = list(selected_seats)
            for index in range(quantity):
                ticket = Ticket.objects.create(
                    ticket_code=_generate_ticket_code(order.id, index),
                    tcategory=category,
                    torder_id=order.id,
                    status=Ticket.StatusChoices.ACTIVE,
                )
                if event.venue.has_reserved_seating and index < len(seats):
                    HasRelationship.objects.create(ticket=ticket, seat=seats[index])

        messages.success(request, 'Checkout berhasil. Order dibuat dengan status Pending.')
        return redirect('orders:order_list')

    return render(request, 'orders/checkout.html', {
        'event': event,
        'categories': categories,
        'default_category': default_category,
        'available_seats': available_seats,
        'active_promos': active_promos,
    })


@login_required
def update_order(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat mengubah order.')
        return redirect('orders:order_list')
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        payment_status = request.POST.get('payment_status')
        if payment_status in dict(Order.STATUS_CHOICES):
            order.payment_status = payment_status
            order.save(update_fields=['payment_status'])
            messages.success(request, 'Status order berhasil diperbarui.')
        else:
            messages.error(request, 'Status order tidak valid.')
    return redirect('orders:order_list')


@login_required
def delete_order(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat menghapus order.')
        return redirect('orders:order_list')
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        Ticket.objects.filter(torder_id=order.id).delete()
        order.delete()
        messages.success(request, 'Order berhasil dihapus.')
    return redirect('orders:order_list')
