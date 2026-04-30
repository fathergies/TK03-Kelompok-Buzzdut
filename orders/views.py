from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Order
from .forms import OrderUpdateForm
from django.db.models import Sum

@login_required
def order_list(request):
    user = request.user

    if user.is_staff:  # ADMIN
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(customer=user)

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
    }

    return render(request, 'orders/list.html', context)


@login_required
def update_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if not request.user.is_staff:
        return redirect('orders:list')

    if request.method == 'POST':
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect('orders:list')
    else:
        form = OrderUpdateForm(instance=order)

    return render(request, 'orders/update_modal.html', {'form': form, 'order': order})


@login_required
def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if not request.user.is_staff:
        return redirect('orders:list')

    if request.method == 'POST':
        order.delete()
        return redirect('orders:list')

    return render(request, 'orders/delete_confirm.html', {'order': order})
