from django.db import models
from django.contrib.auth.models import User
from django.core.cache import cache


# ===========================================================================
#  EMPRESA (Tenant)
# ===========================================================================

class Empresa(models.Model):
    """Representa una empresa/clínica odontológica (tenant del sistema)."""
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nombre']

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    ruc = models.CharField(
        max_length=20, unique=True, verbose_name='RUC'
    )
    direccion = models.TextField(blank=True, verbose_name='Dirección')
    telefono = models.CharField(
        max_length=20, blank=True, verbose_name='Teléfono'
    )
    email = models.EmailField(blank=True, verbose_name='Correo electrónico')
    subdominio = models.CharField(
        max_length=100, unique=True, blank=True, null=True,
        verbose_name='Subdominio',
        help_text='Subdominio para acceso (ej: clinica1.odontsmart.com)'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de registro'
    )

    def __str__(self):
        return self.nombre


# ===========================================================================
#  CONFIGURACIÓN DE EMPRESA
# ===========================================================================

class ConfiguracionEmpresa(models.Model):
    """Configuración visual y funcional por empresa."""
    class Meta:
        verbose_name = 'Configuración de empresa'
        verbose_name_plural = 'Configuraciones de empresa'

    empresa = models.OneToOneField(
        Empresa, on_delete=models.CASCADE,
        related_name='configuracion',
        verbose_name='Empresa'
    )
    logo = models.ImageField(
        upload_to='empresas/logos/', blank=True, null=True,
        verbose_name='Logo'
    )
    color_principal = models.CharField(
        max_length=7, default='#2563eb', verbose_name='Color principal',
        help_text='Código hex, ej: #2563eb'
    )
    color_secundario = models.CharField(
        max_length=7, default='#1e40af', verbose_name='Color secundario',
        help_text='Código hex, ej: #1e40af'
    )
    frase_pie = models.CharField(
        max_length=200, blank=True, default='Tu sonrisa, nuestra prioridad',
        verbose_name='Frase o lema'
    )
    moneda = models.CharField(
        max_length=10, default='USD', verbose_name='Moneda'
    )
    zona_horaria = models.CharField(
        max_length=50, default='America/Guayaquil',
        verbose_name='Zona horaria'
    )

    def __str__(self):
        return f'Configuración: {self.empresa.nombre}'


# ===========================================================================
#  SISTEMA DE PERMISOS DINÁMICO
# ===========================================================================

class Permiso(models.Model):
    """Catálogo global de permisos del sistema."""
    class Meta:
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
        ordering = ['modulo', 'nombre']

    MODULO_CHOICES = [
        ('PACIENTES', 'Pacientes'),
        ('MEDICOS', 'Médicos'),
        ('CITAS', 'Citas'),
        ('HISTORIAS', 'Historias Clínicas'),
        ('REPORTES', 'Reportes'),
        ('USUARIOS', 'Usuarios'),
        ('CONFIGURACION', 'Configuración'),
        ('TAREAS', 'Tareas Programadas'),
        ('FACTURACION', 'Facturación'),
        ('SRI', 'SRI'),
        ('SERVICIOS', 'Servicios'),
    ]

    nombre = models.CharField(max_length=100, verbose_name='Nombre del permiso')
    codigo = models.CharField(
        max_length=100, unique=True, verbose_name='Código',
        help_text='Identificador único del permiso (ej: crear_pacientes)'
    )
    modulo = models.CharField(
        max_length=50, choices=MODULO_CHOICES, verbose_name='Módulo'
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción')

    def __str__(self):
        return f'[{self.get_modulo_display()}] {self.nombre}'


class PermisoRol(models.Model):
    """Permisos asignados a un rol dentro de una empresa."""
    class Meta:
        verbose_name = 'Permiso de rol'
        verbose_name_plural = 'Permisos de roles'
        unique_together = ('empresa', 'rol', 'permiso')

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        related_name='permisos_roles',
        verbose_name='Empresa'
    )
    rol = models.ForeignKey(
        'usuarios.Role', on_delete=models.CASCADE,
        related_name='permisos_asignados',
        verbose_name='Rol'
    )
    permiso = models.ForeignKey(
        Permiso, on_delete=models.CASCADE,
        related_name='roles_asignados',
        verbose_name='Permiso'
    )
    fecha_asignacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de asignación'
    )

    def __str__(self):
        return f'{self.rol.get_nombre_display()} → {self.permiso.codigo}'


class PermisoUsuario(models.Model):
    """Permisos asignados a un usuario dentro de una empresa."""
    class Meta:
        verbose_name = 'Permiso de usuario'
        verbose_name_plural = 'Permisos de usuarios'
        unique_together = ('empresa', 'usuario', 'permiso')

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        related_name='permisos_usuarios',
        verbose_name='Empresa'
    )
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='permisos_empresa',
        verbose_name='Usuario'
    )
    permiso = models.ForeignKey(
        Permiso, on_delete=models.CASCADE,
        related_name='usuarios_asignados',
        verbose_name='Permiso'
    )
    concedido = models.BooleanField(
        default=True, verbose_name='Concedido',
        help_text='Si está activo o denegado'
    )
    fecha_asignacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de asignación'
    )

    def __str__(self):
        return f'{self.usuario.username} → {self.permiso.codigo}'


# ===========================================================================
#  UTILITY: Obtener empresa actual desde request
# ===========================================================================

def get_empresa_from_request(request):
    """Obtiene la empresa actual desde el request (helper central en core.tenant)."""
    from core.tenant import get_empresa
    return get_empresa(request)


# ===========================================================================
#  TENANT MIXIN
# ===========================================================================

class TenantMixin(models.Model):
    """
    Mixin abstracto que añade el campo `empresa` para aislamiento multi-tenant.
    Todos los modelos específicos de cada empresa deben heredar de este mixin.
    """
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        verbose_name='Empresa'
    )

    class Meta:
        abstract = True

    @classmethod
    def for_empresa(cls, empresa):
        """Filtra queryset por empresa."""
        return cls.objects.filter(empresa=empresa)


# ===========================================================================
#  BACKGROUND TASK LOG (actualizado con empresa)
# ===========================================================================

class BackgroundTaskLog(models.Model):
    """Registro de ejecución de tareas en segundo plano."""
    class Meta:
        verbose_name = 'Registro de Tarea'
        verbose_name_plural = 'Registros de Tareas'
        ordering = ['-fecha_ejecucion']

    TAREA_CHOICES = [
        ('RECORDATORIO_CITAS', 'Recordatorio de Citas'),
        ('FACTURACION_MENSUAL', 'Facturación Mensual'),
        ('RESPALDO_DB', 'Respaldo de Base de Datos'),
        ('LIMPIEZA_LOCKS', 'Limpieza de Locks'),
        ('ENVIAR_WHATSAPP', 'Envío de WhatsApp'),
        ('OTRA', 'Otra'),
    ]

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADO', 'Completado'),
        ('ERROR', 'Error'),
        ('SIMULADO', 'Simulado'),
    ]

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        null=True, blank=True, verbose_name='Empresa'
    )
    tarea = models.CharField(
        max_length=50, choices=TAREA_CHOICES, verbose_name='Tarea'
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE',
        verbose_name='Estado'
    )
    detalle = models.TextField(
        blank=True, verbose_name='Detalle / Resultado'
    )
    ejecutado_por = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Ejecutado por'
    )
    fecha_ejecucion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de ejecución'
    )
    duracion_segundos = models.FloatField(
        null=True, blank=True, verbose_name='Duración (segundos)'
    )

    def __str__(self):
        return f'{self.get_tarea_display()} - {self.get_estado_display()} [{self.fecha_ejecucion.strftime("%d/%m/%Y %H:%M")}]'
