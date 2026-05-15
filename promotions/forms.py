from django import forms
from .models import Promotion


class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = [
            "promo_code",
            "discount_type",
            "discount_value",
            "start_date",
            "end_date",
            "usage_limit",
        ]

        widgets = {
            "promo_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Contoh: HEMAT50"
            }),
            "discount_type": forms.Select(attrs={
                "class": "form-control"
            }),
            "discount_value": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1
            }),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "usage_limit": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                "Tanggal berakhir harus sama dengan atau setelah tanggal mulai."
            )

        return cleaned_data