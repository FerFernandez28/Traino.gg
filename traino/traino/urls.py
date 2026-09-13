from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from traino.controllers import views

urlpatterns = [
    path('', views.index, name='inicio'),
    path('admin/', admin.site.urls),   
    path('home', views.home, name='home'),

    path('register/', views.UsuarioController.as_view(), name='register_user'),
    path('login/', views.LoginController.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'), 
    
    # Endpoints Agenda
    path('crear-evento/', views.CrearEventoController.as_view(), name='create_event'),
    path('marcar-asistencia/', views.RegistrarAsistenciaController.as_view(), name='mark_attendance'),
    path('editar-evento/', views.EditarEventoController.as_view(), name='edit_event'),
    
    # Gestion de Perfiles y Estado Operativo
    path('coach/toggle-status/', views.toggle_coach_status, name='toggle_coach_status'),
    path('profile/update/', views.EditarPerfilController.as_view(), name='update_profile'),

    # panel admin
    path('guardar-equipo/', views.guardar_equipo, name='guardar_equipo'),
    path('actualizar-equipo/', views.actualizar_equipo, name='actualizar_equipo'),
    path('eliminar-equipo/', views.eliminar_equipo, name='eliminar_equipo'),
    #panel admin editar jugador
    path('editar_jugador_admin/', views.editar_jugador_admin, name='editar_jugador_admin'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)