from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile, Role


class CustomUserCreationForm(UserCreationForm):
    """Formulario de registro con campos adicionales"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'correo@ejemplo.com'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombres',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Tus nombres'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Apellidos',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Tus apellidos'
        })
    )
    telefono = forms.CharField(
        max_length=20,
        required=False,
        label='Teléfono',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+57 300 123 4567'
        })
    )
    rol = forms.ChoiceField(
        choices=[],
        required=True,
        label='Rol',
        widget=forms.Select(attrs={
            'class': 'form-input'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'telefono', 'rol', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'nombre_usuario'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': '••••••••'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
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
    """Formulario de inicio de sesión personalizado"""
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Nombre de usuario'
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••'
        })
    )
