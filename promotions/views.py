from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import Promotion


@login_required
def promotion_list(request):
    today = timezone.localdate()

    promotions = (
        Promotion.objects
        .filter(start_date__lte=today, end_date__gte=today)
        .order_by("end_date", "promo_code")
    )

    context = {
        "promotions": promotions,
    }
    return render(request, "promotions/promotion_list.html", context)


@login_required
def promotion_detail(request, promotion_id):
    promotion = get_object_or_404(Promotion, promotion_id=promotion_id)

    context = {
        "promotion": promotion,
    }
    return render(request, "promotions/promotion_detail.html", context)