from django import forms
from .models import Cita
from pacientes.models import Paciente
from medicos.models import Medico
from datetime import date, time


class CitaForm(forms.ModelForm):
    """Formulario de registro de citas"""

    class Meta:
        model = Cita
        fields = ['paciente', 'doctor', 'fecha', 'hora', 'motivo', 'estado', 'notas']
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-input'}),
            'doctor': forms.Select(attrs={'class': 'form-input'}),
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'hora': forms.TimeInput(
                attrs={'class': 'form-input', 'type': 'time'}
            ),
            'motivo': forms.Textarea(attrs={
                'class': 'form-input', 'placeholder': 'Describe el motivo de la consulta',
                'rows': 3
            }),
            'estado': forms.Select(attrs={'class': 'form-input'}),
            'notas': forms.Textarea(attrs={
                'class': 'form-input', 'placeholder': 'Notas adicionales (opcional)',
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
