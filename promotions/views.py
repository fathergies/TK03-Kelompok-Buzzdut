from django.contrib import messages
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
    })


@login_required
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