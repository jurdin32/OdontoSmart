from django import forms
from .models import Proforma, Factura
from pacientes.models import Paciente
from medicos.models import Medico
from datetime import date, timedelta


INPUT_CLASSES = (
    'mt-1 block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 '
    'text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 '
    'focus:border-sky-500 focus:ring-2 focus:ring-sky-100'
)


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
            'paciente': forms.Select(attrs={'class': INPUT_CLASSES}),
            'medico': forms.Select(attrs={'class': INPUT_CLASSES}),
            'fecha_validez': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'descuento_porcentaje': forms.NumberInput(
                attrs={'class': INPUT_CLASSES + ' max-w-[7rem]', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'impuesto_porcentaje': forms.NumberInput(
                attrs={'class': INPUT_CLASSES + ' max-w-[7rem]', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'estado': forms.Select(attrs={'class': INPUT_CLASSES}),
            'notas': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
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
            'proforma': forms.Select(attrs={'class': INPUT_CLASSES}),
            'paciente': forms.Select(attrs={'class': INPUT_CLASSES}),
            'medico': forms.Select(attrs={'class': INPUT_CLASSES}),
            'descuento_porcentaje': forms.NumberInput(
                attrs={'class': INPUT_CLASSES + ' max-w-[7rem]', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'impuesto_porcentaje': forms.NumberInput(
                attrs={'class': INPUT_CLASSES + ' max-w-[7rem]', 'step': '0.01', 'min': '0', 'max': '100'}
            ),
            'forma_pago': forms.Select(attrs={'class': INPUT_CLASSES}),
            'estado': forms.Select(attrs={'class': INPUT_CLASSES}),
            'fecha_pago': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'notas': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3
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
