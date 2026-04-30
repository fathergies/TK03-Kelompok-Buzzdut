from django.shortcuts import render
from .models import Order
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

@login_required
def order_list(request):
    user = request.user
    orders = Order.objects.all().order_by('-order_date')

    # R-Order: Filter berdasarkan Role
    if user.role == 'CUSTOMER':
        orders = orders.filter(customer=user)
    elif user.role == 'ORGANIZER':
        # Asumsi relasi melalui tiket/event. Untuk simpelnya kita filter berdasarkan logic sistemmu.
        pass 

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
        orders = orders.filter(id__icontains=search)
    if status:
        orders = orders.filter(payment_status=status)

    return render(request, 'orders/order_list.html', {'orders': orders, 'stats': stats})