from django import forms
from .models import Odontograma


class OdontogramaForm(forms.ModelForm):
    class Meta:
        model = Odontograma
        fields = [
            'protesis_fija', 'protesis_removible', 'coronas',
            'cantidad_dientes_existentes', 'presencia_sarro',
            'enfermedad_periodontal',
        ]
        widgets = {
            'protesis_fija': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'protesis_removible': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'coronas': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'cantidad_dientes_existentes': forms.NumberInput(attrs={
                'class': 'form-input', 'style': 'width: 80px;', 'readonly': 'readonly'
            }),
            'presencia_sarro': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'enfermedad_periodontal': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
        }
