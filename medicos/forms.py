from django import forms
from .models import Medico


class MedicoForm(forms.ModelForm):
    """Formulario de registro de médicos"""

    class Meta:
        model = Medico
        fields = [
            'nombres', 'apellidos', 'cedula', 'especialidad',
            'registro_profesional', 'telefono', 'email'
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Nombres del médico'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Apellidos del médico'
            }),
            'cedula': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Ej: 1234567890'
            }),
            'especialidad': forms.Select(attrs={'class': 'form-input'}),
            'registro_profesional': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: RP-12345'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '+57 300 123 4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input', 'placeholder': 'medico@consultorio.com'
            }),
        }
