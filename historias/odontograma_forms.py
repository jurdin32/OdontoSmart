from django import forms
from .models import Odontograma

INPUT_CLASSES = ('mt-1 block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100')

CHECKBOX_CLASSES = 'h-4 w-4 cursor-pointer rounded border-slate-300 accent-sky-600 focus:ring-2 focus:ring-sky-100'


class OdontogramaForm(forms.ModelForm):
    class Meta:
        model = Odontograma
        fields = [
            'protesis_fija', 'protesis_removible', 'coronas',
            'cantidad_dientes_existentes', 'presencia_sarro',
            'enfermedad_periodontal',
        ]
        widgets = {
            'protesis_fija': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'protesis_removible': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'coronas': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'cantidad_dientes_existentes': forms.NumberInput(attrs={
                'class': INPUT_CLASSES, 'style': 'width: 96px; text-align: center;', 'readonly': 'readonly'
            }),
            'presencia_sarro': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'enfermedad_periodontal': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
        }
