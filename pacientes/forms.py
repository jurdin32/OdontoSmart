from django import forms
from .models import Paciente
from datetime import date


class PacienteForm(forms.ModelForm):
    """Formulario de registro de paciente"""

    class Meta:
        model = Paciente
        fields = [
            'nombres', 'apellidos', 'cedula', 'fecha_nacimiento',
            'lugar', 'nacionalidad', 'genero',
            'telefono', 'celular', 'email', 'direccion',
            'ocupacion', 'foto',
            'acompanante_nombre', 'acompanante_telefono',
            'acompanante_parentesco',
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Nombres del paciente'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Apellidos del paciente'
            }),
            'cedula': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Ej: 1234567890'
            }),
            'fecha_nacimiento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'genero': forms.Select(attrs={'class': 'form-input'}),
            'lugar': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Ciudad / Lugar de origen'
            }),
            'nacionalidad': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Ej: Ecuatoriana, Colombiana...'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '+57 300 123 4567'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '+57 300 123 4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input', 'placeholder': 'paciente@correo.com'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-input', 'placeholder': 'Dirección de residencia',
                'rows': 3
            }),
            'ocupacion': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Ej: Ingeniero, Estudiante...'
            }),
            'foto': forms.FileInput(attrs={
                'class': 'form-input', 'accept': 'image/*'
            }),
            'acompanante_nombre': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Nombre del acompañante'
            }),
            'acompanante_telefono': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '+57 300 123 4567'
            }),
            'acompanante_parentesco': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Ej: Madre, Padre, Cónyuge...'
            }),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data['cedula'].strip()
        if not cedula.isdigit():
            raise forms.ValidationError('La cédula debe contener solo números.')
        return cedula

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data['fecha_nacimiento']
        if fecha > date.today():
            raise forms.ValidationError(
                'La fecha de nacimiento no puede ser futura.'
            )
        return fecha
