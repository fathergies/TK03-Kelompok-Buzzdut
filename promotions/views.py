from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PromotionForm
from .models import Promotion


def _is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


def promotion_list(request):
    """List all promotions. Accessible by everyone (including guests)."""
    promotions = Promotion.objects.annotate(current_usage=Count('order_promotions'))

    search = request.GET.get('search', '')
    if search:
        promotions = promotions.filter(promo_code__icontains=search)

    promo_type = request.GET.get('type', '')
    if promo_type == 'PERCENTAGE':
        promotions = promotions.filter(discount_type=Promotion.DISCOUNT_PERCENTAGE)
    elif promo_type == 'NOMINAL':
        promotions = promotions.filter(discount_type=Promotion.DISCOUNT_NOMINAL)

    promotions = promotions.order_by("-start_date")

    # Stats computed from the full queryset (before search/filter for accuracy? Per spec: total of all)
    all_promos = Promotion.objects.annotate(current_usage=Count('order_promotions'))
    total_promo = all_promos.count()
    total_usage = sum(p.current_usage for p in all_promos)
    total_persentase = all_promos.filter(discount_type=Promotion.DISCOUNT_PERCENTAGE).count()

    context = {
        "promos": promotions,
        "search": search,
        "promo_type": promo_type,
        "stats": {
            "total_promo": total_promo,
            "total_usage": total_usage,
            "total_persentase": total_persentase,
        },
        "can_manage": _is_admin(request.user),
    }
    return render(request, "promotions/promotion_list.html", context)


@login_required
def promotion_create(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Hanya Admin yang dapat membuat promosi.")

    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promosi berhasil dibuat!')
            return redirect('promotions:list')
        else:
            messages.error(request, 'Mohon perbaiki kesalahan pada form.')
    else:
        form = PromotionForm()

    return render(request, 'promotions/promotion_form.html', {
        'form': form,
        'title': 'Buat Promo Baru',
        'button_text': 'Buat',
    })


@login_required
def promotion_update(request, promotion_id):
    promotion = get_object_or_404(Promotion, promotion_id=promotion_id)

    if not _is_admin(request.user):
        return HttpResponseForbidden("Hanya Admin yang dapat mengubah promosi.")

    if request.method == 'POST':
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            form.save()
            messages.success(request, f'Promosi "{promotion.promo_code}" berhasil diperbarui!')
            return redirect('promotions:list')
        else:
            messages.error(request, 'Mohon perbaiki kesalahan pada form.')
    else:
        form = PromotionForm(instance=promotion)

    return render(request, 'promotions/promotion_form.html', {
        'form': form,
        'title': 'Edit Promo',
        'button_text': 'Simpan',
    })


@login_required
def promotion_delete(request, promotion_id):
    promotion = get_object_or_404(Promotion, promotion_id=promotion_id)

    if not _is_admin(request.user):
        return HttpResponseForbidden("Hanya Admin yang dapat menghapus promosi.")

    if request.method == 'POST':
        code = promotion.promo_code
        promotion.delete()
        messages.success(request, f'Promosi "{code}" berhasil dihapus.')
        return redirect('promotions:list')

    return render(request, 'promotions/promotion_delete.html', {'promotion': promotion})