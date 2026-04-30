from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Promotion
from .forms import PromotionForm

def promotion_list(request):
    promos = Promotion.objects.annotate(used_count=Count('order')).order_by('-start_date', 'code')
    
    # Statistik Ringkasan
    stats = {
        'total_promo': promos.count(),
        'total_usage': sum(p.used_count for p in promos),
        'total_persentase': promos.filter(discount_type='Persentase').count()
    }
    
    # Logic Filter & Search
    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    
    if search_query:
        promos = promos.filter(code__icontains=search_query)
    if type_filter:
        promos = promos.filter(discount_type=type_filter)
    today = timezone.localdate()
    promos = list(promos)
    for promo in promos:
        promo.is_active_for_list = promo.start_date <= today <= promo.end_date and promo.used_count < promo.usage_limit

    return render(request, 'promotions/promotion_list.html', {
        'promos': promos, 
        'stats': stats,
        'form': PromotionForm(),
        'user_role': getattr(request.user, 'role', 'GUEST')
    })


@login_required
def create_promotion(request):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat membuat promosi.')
        return redirect('promotions:promotion_list')
    if request.method != 'POST':
        return redirect('promotions:promotion_list')

    form = PromotionForm(request.POST)
    if form.is_valid():
        promo = form.save(commit=False)
        promo.current_usage = 0
        promo.save()
        messages.success(request, 'Promosi berhasil dibuat.')
    else:
        messages.error(request, 'Promosi gagal dibuat. Periksa kembali data yang diisi.')
    return redirect('promotions:promotion_list')


@login_required
def update_promotion(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat mengubah promosi.')
        return redirect('promotions:promotion_list')
    promo = get_object_or_404(Promotion, pk=pk)
    if request.method != 'POST':
        return redirect('promotions:promotion_list')

    form = PromotionForm(request.POST, instance=promo)
    if form.is_valid():
        updated = form.save(commit=False)
        updated.current_usage = promo.current_usage
        updated.save()
        messages.success(request, 'Promosi berhasil diperbarui.')
    else:
        messages.error(request, 'Promosi gagal diperbarui. Periksa kembali data yang diisi.')
    return redirect('promotions:promotion_list')


@login_required
def delete_promotion(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat menghapus promosi.')
        return redirect('promotions:promotion_list')
    promo = get_object_or_404(Promotion, pk=pk)
    if request.method == 'POST':
        promo.delete()
        messages.success(request, 'Promosi berhasil dihapus.')
    return redirect('promotions:promotion_list')
