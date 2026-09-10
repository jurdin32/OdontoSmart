from django import forms
from .models import Cita
from pacientes.models import Paciente
from medicos.models import Medico
from facturacion.models import Servicio
from datetime import date, time

# Clases compartidas para los campos (Tailwind CSS)
INPUT_CLASSES = (
    'mt-1 block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 '
    'text-sm text-slate-800 shadow-sm outline-none transition '
    'placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100'
)


class CitaForm(forms.ModelForm):
    """Formulario de registro de citas"""

    class Meta:
        model = Cita
        fields = ['paciente', 'doctor', 'fecha', 'hora', 'motivo', 'estado', 'servicio', 'notas']
        widgets = {
            'paciente': forms.Select(attrs={'class': INPUT_CLASSES}),
            'doctor': forms.Select(attrs={'class': INPUT_CLASSES}),
            'servicio': forms.Select(attrs={'class': INPUT_CLASSES}),
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'hora': forms.TimeInput(
                attrs={'class': INPUT_CLASSES, 'type': 'time'}
            ),
            'motivo': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Describe el motivo de la consulta',
                'rows': 3
            }),
            'estado': forms.Select(attrs={'class': INPUT_CLASSES}),
            'notas': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Notas adicionales (opcional)',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        qs_paciente = Paciente.objects.filter(activo=True)
        qs_medico = Medico.objects.filter(activo=True)
        if empresa:
            qs_paciente = qs_paciente.filter(empresa=empresa)
            qs_medico = qs_medico.filter(empresa=empresa)
        if self.instance.pk:
            # Al editar, garantizar que el valor actual esté en el queryset
            if self.instance.paciente_id:
                qs_paciente = qs_paciente | Paciente.objects.filter(
                    pk=self.instance.paciente_id
                )
            if self.instance.doctor_id:
                qs_medico = qs_medico | Medico.objects.filter(
                    pk=self.instance.doctor_id
                )
        self.fields['paciente'].queryset = qs_paciente
        self.fields['doctor'].queryset = qs_medico

        qs_servicio = Servicio.objects.filter(activo=True)
        if empresa:
            qs_servicio = qs_servicio.filter(empresa=empresa)
        self.fields['servicio'].queryset = qs_servicio
        self.fields['servicio'].empty_label = 'Sin servicio (opcional)'
        self.fields['servicio'].required = False
        self.fields['paciente'].empty_label = 'Seleccione un paciente'
        self.fields['doctor'].empty_label = 'Seleccione un doctor'
        self.fields['estado'].initial = 'PENDIENTE'
        # Quitar required del HTML para que Select2 allowClear funcione
        self.fields['paciente'].widget.attrs.pop('required', None)
        self.fields['doctor'].widget.attrs.pop('required', None)

        if self.instance.pk:
            self.fields['fecha'].widget.attrs['type'] = 'date'
            self.fields['hora'].widget.attrs['type'] = 'time'

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        # Permitir fechas pasadas para registros históricos
        return fecha
