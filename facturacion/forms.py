from django import forms
from .models import Proforma, Factura
from pacientes.models import Paciente
from medicos.models import Medico
from datetime import date, timedelta


class ProformaForm(forms.ModelForm):
    """Formulario para crear/editar proformas."""

    class Meta:
        model = Proforma
        fields = [
            'paciente', 'medico', 'fecha_validez',
            'descuento_porcentaje', 'impuesto_porcentaje',
            'estado', 'notas',
        ]
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-input'}),
            'medico': forms.Select(attrs={'class': 'form-input'}),
            'fecha_validez': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'descuento_porcentaje': forms.NumberInput(
                attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'impuesto_porcentaje': forms.NumberInput(
                attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'estado': forms.Select(attrs={'class': 'form-input'}),
            'notas': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Condiciones, observaciones...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paciente'].queryset = Paciente.objects.filter(activo=True)
        self.fields['medico'].queryset = Medico.objects.filter(activo=True)
        self.fields['paciente'].empty_label = 'Seleccione un paciente'
        self.fields['medico'].empty_label = 'Seleccione un médico'
        self.fields['fecha_validez'].initial = date.today() + timedelta(days=15)
        self.fields['impuesto_porcentaje'].initial = 0
        self.fields['descuento_porcentaje'].initial = 0
        self.fields['paciente'].widget.attrs.pop('required', None)
        self.fields['medico'].widget.attrs.pop('required', None)
        self.fields['estado'].required = False
        self.fields['estado'].required = False


class FacturaForm(forms.ModelForm):
    """Formulario para crear/editar facturas."""

    class Meta:
        model = Factura
        fields = [
            'proforma', 'paciente', 'medico',
            'descuento_porcentaje', 'impuesto_porcentaje',
            'forma_pago', 'estado', 'fecha_pago', 'notas',
        ]
        widgets = {
            'proforma': forms.Select(attrs={'class': 'form-input'}),
            'paciente': forms.Select(attrs={'class': 'form-input'}),
            'medico': forms.Select(attrs={'class': 'form-input'}),
            'descuento_porcentaje': forms.NumberInput(
                attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'impuesto_porcentaje': forms.NumberInput(
                attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'forma_pago': forms.Select(attrs={'class': 'form-input'}),
            'estado': forms.Select(attrs={'class': 'form-input'}),
            'fecha_pago': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'notas': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paciente'].queryset = Paciente.objects.filter(activo=True)
        self.fields['medico'].queryset = Medico.objects.filter(activo=True)
        self.fields['proforma'].queryset = Proforma.objects.filter(estado='APROBADA')
        self.fields['paciente'].empty_label = 'Seleccione un paciente'
        self.fields['medico'].empty_label = 'Seleccione un médico'
        self.fields['proforma'].empty_label = '--- Sin proforma ---'
        self.fields['impuesto_porcentaje'].initial = 0
        self.fields['descuento_porcentaje'].initial = 0
        self.fields['fecha_pago'].initial = date.today()
