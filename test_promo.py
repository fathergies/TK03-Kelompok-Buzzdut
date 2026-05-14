import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'basdat_tk03.settings')
django.setup()

from django.utils import timezone
from basdat_tk03.db import fetch_one

today = timezone.localdate()
t_day = str(today)[:10]

promo_code = 'LOKETHEMAT15'
promotion = fetch_one("SELECT * FROM PROMOTION WHERE promo_code ILIKE %s", [promo_code])

p_start = str(promotion['start_date'])[:10]
p_end = str(promotion['end_date'])[:10]

print(f"t_day: {t_day}")
print(f"p_start: {p_start}")
print(f"p_end: {p_end}")
print(f"p_start > t_day: {p_start > t_day}")
print(f"p_end < t_day: {p_end < t_day}")

