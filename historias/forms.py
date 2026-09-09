from django import forms
from .models import HistoriaClinica, Evolucion
from medicos.models import Medico


class HistoriaClinicaForm(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        exclude = ['paciente', 'registrado_por', 'fecha_creacion', 'fecha_actualizacion', 'version']
        widgets = {
            'alergia_drogas': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'exceso_saliva': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'cicatrizacion': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'sangrado': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'diabetes': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'diabetes_controlado': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Controlado con insulina, dieta...'
            }),
            'cardiacos': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'aspirina': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'frecuencia_aspirina': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Cada 8 horas, diario...'
            }),
            'alergias': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'hipertension': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'medicacion': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'observaciones_medicas': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Detalles adicionales sobre las condiciones marcadas'
            }),
            'tipo_sangre': forms.Select(attrs={'class': 'form-input'}),
            'observaciones_habitos': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 2,
                'placeholder': 'Observaciones adicionales'
            }),
            'antecedentes_familiares': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Enfermedades relevantes en la familia'
            }),
            'diagnostico_presuntivo': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Diagnóstico presuntivo del paciente'
            }),
            'plan_tratamiento': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Plan de tratamiento recomendado'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
            'consentimiento': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'consentimiento_fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'consentimiento_paciente': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre completo del paciente'
            }),
            'consentimiento_direccion': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Dirección de residencia'
            }),
            'consentimiento_cedula': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Cédula de identidad'
            }),
            'fumador': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'alcohol': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'embarazo': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'consentimiento_medico' in self.fields:
            medicos = Medico.objects.filter(activo=True)
            choices = [('', 'Seleccione un médico')]
            for m in medicos:
                choices.append((m.id, f'Dr. {m.nombres} {m.apellidos} - {m.get_especialidad_display()}'))
            self.fields['consentimiento_medico'].widget = forms.Select(
                attrs={'class': 'form-input'},
                choices=choices
            )
            self.fields['consentimiento_medico'].required = False


class EvolucionForm(forms.ModelForm):
    class Meta:
        model = Evolucion
        fields = ['medico', 'fecha', 'motivo', 'diagnostico', 'tratamiento', 'observaciones',
                  'consentimiento_acepta', 'consentimiento_fecha', 'consentimiento_medico',
                  'costo', 'proxima_consulta', 'proxima_consulta_nota']
        widgets = {
            'medico': forms.Select(attrs={'class': 'form-input'}),
            'fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'motivo': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Motivo de la consulta'
            }),
            'diagnostico': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Diagnóstico del odontólogo'
            }),
            'tratamiento': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Tratamiento o procedimiento realizado'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
            'consentimiento_acepta': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'consentimiento_fecha': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'proxima_consulta': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-input', 'type': 'date'}
            ),
            'proxima_consulta_nota': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Control de rutina, revisión...'
            }),
            'costo': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['medico'].queryset = Medico.objects.filter(activo=True)
        self.fields['medico'].empty_label = 'Seleccione un médico'
        # Consentimiento_medico es CharField, se llena automáticamente vía JS
        if 'consentimiento_medico' in self.fields:
            self.fields['consentimiento_medico'].widget.attrs['readonly'] = 'readonly'
            self.fields['consentimiento_medico'].widget.attrs['class'] = 'form-input'
            self.fields['consentimiento_medico'].required = False
