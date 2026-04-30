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

@login_required
def order_list(request):
    user = request.user
    
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
