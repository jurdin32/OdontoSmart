from django import forms
from .models import Paciente
from datetime import date

# Clases compartidas para los campos (Tailwind CSS)
INPUT_CLASSES = (
    'mt-1 block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 '
    'text-sm text-slate-800 shadow-sm outline-none transition '
    'placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100'
)


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
                'class': INPUT_CLASSES, 'placeholder': 'Nombres del paciente'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Apellidos del paciente'
            }),
            'cedula': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Ej: 1234567890'
            }),
            'fecha_nacimiento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'genero': forms.Select(attrs={'class': INPUT_CLASSES}),
            'lugar': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Ciudad / Lugar de origen'
            }),
            'nacionalidad': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Ej: Ecuatoriana, Colombiana...'
            }),
            'telefono': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': '+57 300 123 4567'
            }),
            'celular': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': '+57 300 123 4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'paciente@correo.com'
            }),
            'direccion': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Dirección de residencia',
                'rows': 3
            }),
            'ocupacion': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Ej: Ingeniero, Estudiante...'
            }),
            'foto': forms.FileInput(attrs={
                'class': INPUT_CLASSES + ' file:mr-3 file:rounded-lg file:border-0 file:bg-sky-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-sky-700 hover:file:bg-sky-100', 'accept': 'image/*'
            }),
            'acompanante_nombre': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Nombre del acompañante'
            }),
            'acompanante_telefono': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': '+57 300 123 4567'
            }),
            'acompanante_parentesco': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Ej: Madre, Padre, Cónyuge...'
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
