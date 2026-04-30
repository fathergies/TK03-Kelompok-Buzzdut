from django import forms

from .models import Promotion


class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = [
            'code',
            'discount_type',
            'discount_value',
            'start_date',
            'end_date',
            'usage_limit',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'discount_type': forms.Select(attrs={'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'discount_value': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500', 'min': '0', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500', 'min': '1'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'Tanggal berakhir tidak boleh lebih awal dari tanggal mulai.')
        return cleaned_data
