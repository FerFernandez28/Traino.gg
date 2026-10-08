from django.db import models

class User(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('coach', 'Coach'),
        ('player', 'Player'),
    ]
    
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=254, null=True, blank=True) 
    password = models.CharField(max_length=255)
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES, default='player')

    def __str__(self):
        return f"{self.username} ({self.get_role_type_display()})"
    
class Player(models.Model):
    position_role = models.CharField(max_length=50)
    team_name = models.CharField(max_length=50, default='9z Team')
    # Mantenemos related_name='player_profile' que usa el backend unificado para cruzar sesiones
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player_profile')

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Foto de Perfil Oficial")
    biography = models.TextField(blank=True, null=True, default='', verbose_name="Nota Táctica o Historial Personal")

    def __str__(self):
        return f"Player: {self.user.username} - {self.position_role}"

class Event(models.Model):
    EVENT_TYPES = [
        ('training', 'Entrenamiento'),
        ('match', 'Partido'),
        ('tactics', 'Táctico'),
        ('offday', 'Día Libre'),
        ('other', 'Otro'),
    ]
    
    title = models.CharField(max_length=100, default="Entrenamiento R6")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='training')
    date = models.DateField()                  
    scheduled_time = models.TimeField()         
    
    duration_hours = models.IntegerField(default=1)
    video_link = models.URLField(blank=True, default='')
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events_created', null=True, blank=True)
    # campos de soporte para R6
    rival = models.CharField(max_length=100, blank=True, default='')
    maps = models.CharField(max_length=100, blank=True, default='') 
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.title} - {self.date} {self.scheduled_time}"
    
class Attendance(models.Model):
    # Eventos_idEventos INT
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    # Jugadores_Usuarios_idUsuarios INT(perfil de Player)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='attendances')
    is_present = models.BooleanField(default=False) 
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)

    def __str__(self):
        estado = "Presente" if self.is_present else "Ausente"
        return f"{self.player.user.username} en {self.event.title}: {estado}"

class CompetitiveTeam2026(models.Model):
    REGIONES_CHOICES = [
        ('LATAM', 'Latinoamérica'),
        ('BR', 'Brasil'),
        ('NA', 'Norteamérica'),
        ('EU', 'Europa'),
        ('APAC', 'Asia-Pacífico'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nombre del Equipo")
    # Con esto manejamos cualquier pais o region
    region = models.CharField(max_length=20, choices=REGIONES_CHOICES, default='LATAM', verbose_name="Región Competitiva")
    logo_url = models.CharField(max_length=255, blank=True, null=True)
    global_rank = models.IntegerField(blank=True, null=True, verbose_name="Puesto en Ranking Global")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_region_display()})"