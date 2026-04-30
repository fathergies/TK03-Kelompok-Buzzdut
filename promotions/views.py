from django.shortcuts import render
from .models import Promotion
from django.db.models import Count, Q

def promotion_list(request):
    promos = Promotion.objects.all()
    
    # Statistik Ringkasan
    stats = {
        'total_promo': promos.count(),
        'total_usage': sum(p.current_usage for p in promos),
        'total_persentase': promos.filter(discount_type='Persentase').count()
    }
    
    # Logic Filter & Search
    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    
    if search_query:
        promos = promos.filter(code__icontains=search_query)
    if type_filter:
        promos = promos.filter(discount_type=type_filter)

    return render(request, 'promotions/promotion_list.html', {
        'promos': promos, 
        'stats': stats,
        'user_role': getattr(request.user, 'role', 'GUEST')
    })