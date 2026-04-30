from django import forms
from .models import Promotion


class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['promo_code', 'discount_type', 'discount_value', 'start_date', 'end_date', 'usage_limit']

    def clean_promo_code(self):
        code = self.cleaned_data.get('promo_code', '').strip().upper()
        qs = Promotion.objects.filter(promo_code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Kode promo ini sudah digunakan. Gunakan kode yang berbeda.")
        return code

    def clean_discount_value(self):
        value = self.cleaned_data.get('discount_value')
        if value is not None and value <= 0:
            raise forms.ValidationError("Nilai diskon harus berupa bilangan positif > 0.")
        return value

    def clean_usage_limit(self):
        limit = self.cleaned_data.get('usage_limit')
        if limit is not None and limit <= 0:
            raise forms.ValidationError("Batas penggunaan harus berupa bilangan bulat positif > 0.")
        return limit

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', "Tanggal berakhir harus sama dengan atau setelah tanggal mulai.")
        return cleaned_data
