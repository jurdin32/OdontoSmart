from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile, Role

# Clases Tailwind compartidas por los widgets de los formularios (excepto CustomLoginForm)
INPUT_CLASSES = (
    'mt-1 block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 '
    'text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 '
    'focus:border-sky-500 focus:ring-2 focus:ring-sky-100'
)


class CustomUserCreationForm(UserCreationForm):
    """Formulario de registro con campos adicionales"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'correo@ejemplo.com'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombres',
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Tus nombres'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Apellidos',
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Tus apellidos'
        })
    )
    telefono = forms.CharField(
        max_length=20,
        required=False,
        label='Teléfono',
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': '+57 300 123 4567'
        })
    )
    rol = forms.ChoiceField(
        choices=[],
        required=True,
        label='Rol',
        widget=forms.Select(attrs={
            'class': INPUT_CLASSES
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'telefono', 'rol', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': INPUT_CLASSES,
            'placeholder': 'nombre_usuario'
        })
        self.fields['password1'].widget.attrs.update({
            'class': INPUT_CLASSES,
            'placeholder': '••••••••'
        })
        self.fields['password2'].widget.attrs.update({
            'class': INPUT_CLASSES,
            'placeholder': 'Repite la contraseña'
        })
        # Cargar roles disponibles (excluyendo ADMIN y PATIENT para registro público)
        self.fields['rol'].choices = [
            (role.nombre, role.get_nombre_display())
            for role in Role.objects.all()
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            profile = Profile.objects.get(user=user)
            profile.telefono = self.cleaned_data.get('telefono', '')
            rol_nombre = self.cleaned_data.get('rol')
            if rol_nombre:
                try:
                    profile.rol = Role.objects.get(nombre=rol_nombre)
                except Role.DoesNotExist:
                    pass
            profile.save()
        return user


class CustomLoginForm(AuthenticationForm):
    """Formulario de inicio de sesión personalizado (Tailwind CSS)"""
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-xl border-0 bg-white py-3 pl-11 pr-4 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100',
            'placeholder': 'Nombre de usuario'
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-xl border-0 bg-white py-3 pl-11 pr-12 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-100',
            'placeholder': '••••••••'
        })
    )
