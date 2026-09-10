from django import forms
from .models import HistoriaClinica, Evolucion
from medicos.models import Medico
from facturacion.models import Servicio

INPUT_CLASSES = ('mt-1 block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100')

CHECKBOX_CLASSES = 'h-4 w-4 cursor-pointer rounded border-slate-300 accent-sky-600 focus:ring-2 focus:ring-sky-100'


class HistoriaClinicaForm(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        exclude = ['paciente', 'registrado_por', 'fecha_creacion', 'fecha_actualizacion', 'version']
        widgets = {
            'alergia_drogas': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'exceso_saliva': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'cicatrizacion': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'sangrado': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'diabetes': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'diabetes_controlado': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ej: Controlado con insulina, dieta...'
            }),
            'cardiacos': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'aspirina': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'frecuencia_aspirina': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ej: Cada 8 horas, diario...'
            }),
            'alergias': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'hipertension': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'medicacion': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'observaciones_medicas': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Detalles adicionales sobre las condiciones marcadas'
            }),
            'tipo_sangre': forms.Select(attrs={'class': INPUT_CLASSES}),
            'observaciones_habitos': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 2,
                'placeholder': 'Observaciones adicionales'
            }),
            'antecedentes_familiares': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Enfermedades relevantes en la familia'
            }),
            'diagnostico_presuntivo': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Diagnóstico presuntivo del paciente'
            }),
            'plan_tratamiento': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Plan de tratamiento recomendado'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
            'consentimiento': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'consentimiento_fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'consentimiento_paciente': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Nombre completo del paciente'
            }),
            'consentimiento_direccion': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Dirección de residencia'
            }),
            'consentimiento_cedula': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Cédula de identidad'
            }),
            'fumador': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'alcohol': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'embarazo': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'consentimiento_medico' in self.fields:
            medicos = Medico.objects.filter(activo=True)
            choices = [('', 'Seleccione un médico')]
            for m in medicos:
                choices.append((m.id, f'Dr. {m.nombres} {m.apellidos} - {m.get_especialidad_display()}'))
            self.fields['consentimiento_medico'].widget = forms.Select(
                attrs={'class': INPUT_CLASSES},
                choices=choices
            )
            self.fields['consentimiento_medico'].required = False


class EvolucionForm(forms.ModelForm):
    class Meta:
        model = Evolucion
        fields = ['medico', 'fecha', 'motivo', 'diagnostico', 'tratamiento', 'observaciones',
                  'servicio',
                  'consentimiento_acepta', 'consentimiento_fecha', 'consentimiento_medico',
                  'costo', 'proxima_consulta', 'proxima_consulta_nota']
        widgets = {
            'medico': forms.Select(attrs={'class': INPUT_CLASSES}),
            'servicio': forms.Select(attrs={'class': INPUT_CLASSES}),
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'motivo': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Motivo de la consulta'
            }),
            'diagnostico': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Diagnóstico del odontólogo'
            }),
            'tratamiento': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Tratamiento o procedimiento realizado'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
            'consentimiento_acepta': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'consentimiento_fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'proxima_consulta': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': INPUT_CLASSES, 'type': 'date'}
            ),
            'proxima_consulta_nota': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Ej: Control de rutina, revisión...'
            }),
            'costo': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.fields['medico'].queryset = Medico.objects.filter(activo=True)
        self.fields['medico'].empty_label = 'Seleccione un médico'

        qs_servicio = Servicio.objects.filter(activo=True)
        if self.empresa:
            qs_servicio = qs_servicio.filter(empresa=self.empresa)
        self.fields['servicio'].queryset = qs_servicio
        self.fields['servicio'].empty_label = 'Sin servicio (opcional)'
        self.fields['servicio'].required = False
        # Consentimiento_medico es CharField, se llena automáticamente vía JS
        if 'consentimiento_medico' in self.fields:
            self.fields['consentimiento_medico'].widget.attrs['readonly'] = 'readonly'
            self.fields['consentimiento_medico'].widget.attrs['class'] = INPUT_CLASSES
            self.fields['consentimiento_medico'].required = False
