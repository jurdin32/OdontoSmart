from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('pacientes/', include('pacientes.urls')),
    path('citas/', include('citas.urls')),
    path('medicos/', include('medicos.urls')),
    path('historias/', include('historias.urls')),
    path('reportes/', include('reportes.urls')),
    path('facturacion/', include('facturacion.urls')),
    path('sri/', include('sri.urls')),
    path('api/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
