from django import forms
from .models import Medico


INPUT_CLASSES = ('mt-1 block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100')


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
                'class': INPUT_CLASSES, 'placeholder': 'Nombres del médico'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Apellidos del médico'
            }),
            'cedula': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Ej: 1234567890'
            }),
            'especialidad': forms.Select(attrs={'class': INPUT_CLASSES}),
            'registro_profesional': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ej: RP-12345'
            }),
            'telefono': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': '+57 300 123 4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'medico@consultorio.com'
            }),
        }
