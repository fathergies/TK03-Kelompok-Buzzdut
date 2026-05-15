from django.contrib import messages
<<<<<<< HEAD
from django.shortcuts import redirect, render
from basdat_tk03.auth import login_required
from basdat_tk03.db import fetch_all, fetch_one, execute_query
from django.utils import timezone
import uuid

def promotion_list(request):
    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')

    base_query = """
        SELECT p.*, COUNT(op.order_promotion_id) as used_count
        FROM PROMOTION p
        LEFT JOIN ORDER_PROMOTION op ON p.promotion_id = op.promotion_id
        WHERE 1=1
    """
    params = []

    if search_query:
        base_query += " AND p.promo_code ILIKE %s"
        params.append(f"%{search_query}%")
    if type_filter:
        base_query += " AND p.discount_type = %s"
        params.append(type_filter)

    base_query += " GROUP BY p.promotion_id ORDER BY p.start_date DESC, p.promo_code ASC"

    promos_raw = fetch_all(base_query, params)

    today = timezone.localdate()
    total_usage = 0
    total_persentase = 0

    for p in promos_raw:
        p['is_active_for_list'] = str(p['start_date']) <= str(today) <= str(p['end_date']) and p['used_count'] < p['usage_limit']
        # Django template compatibility
        p['code'] = p['promo_code']
        p['pk'] = p['promotion_id']
        
        total_usage += p['used_count']
        if p['discount_type'] == 'PERCENTAGE':
            total_persentase += 1

    stats = {
        'total_promo': len(promos_raw),
        'total_usage': total_usage,
        'total_persentase': total_persentase
    }

    # Dummy form object to trick the template into working without forms.py
    class DummyForm:
        pass

    user_role = getattr(request.user, 'role', 'GUEST') if hasattr(request, 'user') and request.user else 'GUEST'

    return render(request, 'promotions/promotion_list.html', {
        'promos': promos_raw, 
        'stats': stats,
        'form': DummyForm(),
        'user_role': user_role
=======
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count
from django.shortcuts import render, redirect, get_object_or_404

from .models import Promotion
from .forms import PromotionForm


def is_admin(user):
    return user.is_authenticated and user.is_staff


def promotion_list(request):
    promotions = Promotion.objects.all()

    search_query = request.GET.get("q", "")
    discount_type = request.GET.get("discount_type", "")

    if search_query:
        promotions = promotions.filter(promo_code__icontains=search_query)

    if discount_type in ["percentage", "nominal"]:
        promotions = promotions.filter(discount_type=discount_type)

    all_promotions = Promotion.objects.all()

    total_promo = all_promotions.count()
    total_usage = all_promotions.aggregate(total=Sum("used_count"))["total"] or 0
    total_percentage = all_promotions.filter(discount_type="percentage").count()

    context = {
        "promotions": promotions,
        "search_query": search_query,
        "discount_type": discount_type,
        "total_promo": total_promo,
        "total_usage": total_usage,
        "total_percentage": total_percentage,
    }

    return render(request, "promotions/promotion_list.html", context)


@login_required
@user_passes_test(is_admin)
def promotion_create(request):
    if request.method == "POST":
        form = PromotionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Promo berhasil dibuat.")
            return redirect("promotions:promotion_list")
    else:
        form = PromotionForm()

    return render(request, "promotions/promotion_form.html", {
        "form": form,
        "title": "Buat Promo",
        "button_text": "Simpan",
>>>>>>> 61b17254380ad6fb00b6f142da9d26deb3967168
    })


@login_required
<<<<<<< HEAD
def create_promotion(request):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat membuat promosi.')
        return redirect('promotions:promotion_list')
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_type = request.POST.get('discount_type')
        discount_value = request.POST.get('discount_value')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        usage_limit = request.POST.get('usage_limit')

        try:
            execute_query(
                "INSERT INTO PROMOTION (promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [str(uuid.uuid4()), code, discount_type, discount_value, start_date, end_date, usage_limit]
            )
            messages.success(request, 'Promosi berhasil dibuat.')
        except Exception as e:
            messages.error(request, f'Promosi gagal dibuat: {e}')
            
    return redirect('promotions:promotion_list')


@login_required
def update_promotion(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat mengubah promosi.')
        return redirect('promotions:promotion_list')
        
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_type = request.POST.get('discount_type')
        discount_value = request.POST.get('discount_value')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        usage_limit = request.POST.get('usage_limit')

        try:
            execute_query(
                "UPDATE PROMOTION SET promo_code=%s, discount_type=%s, discount_value=%s, start_date=%s, end_date=%s, usage_limit=%s WHERE promotion_id=%s",
                [code, discount_type, discount_value, start_date, end_date, usage_limit, pk]
            )
            messages.success(request, 'Promosi berhasil diperbarui.')
        except Exception as e:
            messages.error(request, f'Promosi gagal diperbarui: {e}')

    return redirect('promotions:promotion_list')


@login_required
def delete_promotion(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat menghapus promosi.')
        return redirect('promotions:promotion_list')
        
    if request.method == 'POST':
        try:
            execute_query("DELETE FROM PROMOTION WHERE promotion_id=%s", [pk])
            messages.success(request, 'Promosi berhasil dihapus.')
        except Exception as e:
            messages.error(request, f'Promosi gagal dihapus: {e}')
            
    return redirect('promotions:promotion_list')
=======
@user_passes_test(is_admin)
def promotion_update(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)

    if request.method == "POST":
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            form.save()
            messages.success(request, "Promo berhasil diperbarui.")
            return redirect("promotions:promotion_list")
    else:
        form = PromotionForm(instance=promotion)

    return render(request, "promotions/promotion_form.html", {
        "form": form,
        "title": "Update Promo",
        "button_text": "Update",
    })


@login_required
@user_passes_test(is_admin)
def promotion_delete(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)

    if request.method == "POST":
        promotion.delete()
        messages.success(request, "Promo berhasil dihapus.")
        return redirect("promotions:promotion_list")

    return render(request, "promotions/promotion_confirm_delete.html", {
        "promotion": promotion
    })
>>>>>>> 61b17254380ad6fb00b6f142da9d26deb3967168
