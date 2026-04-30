from django import forms
from .models import Order

class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_status']
        widgets = {
            'payment_status': forms.Select(attrs={
                'class': 'border rounded-lg px-4 py-2.5 text-sm w-full outline-none focus:ring-2 focus:ring-blue-500 font-medium text-gray-700'
            })
        }