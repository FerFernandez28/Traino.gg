import datetime
import calendar
import json
import pandas as pd
import os  # para poder leer variables de entorno - .env
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.contrib.auth.hashers import make_password, check_password
from ..models.models import User, Player, Map, MatchPerformance, Attendance, Event, CompetitiveTeam2026
from ..src.singleton import SystemConfigSingleton
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.core.mail import send_mail
from django.core.management import call_command
from django.utils.html import strip_tags
from django.conf import settings

MIRO_BOARDS = [
    {
        'name': 'BANCO-KAFE-LABS', 
        'url': os.environ.get('MIRO_BOARD_BANCO', 'https://miro.com/app/live-embed/uXjVIfN6qy0=/?embedMode=view_only_without_ui&moveToViewport=-136889,-39560,76800,37800&embedId=64892924449')
    },
    {
        'name': 'BORDER-FORTALEZA', 
        'url': os.environ.get('MIRO_BOARD_BORDER', 'https://miro.com/app/live-embed/OTRA_URL_AQUI=/?embedMode=view_only_without_ui')
    },
    {
        'name': 'CLUB-CHALET-LAIR', 
        'url': os.environ.get('MIRO_BOARD_CLUB', 'https://miro.com/app/live-embed/OTRA_URL_MAS_AQUI=/?embedMode=view_only_without_ui')
    },
]

def generar_agenda(mes_filtro=None):
    DIAS_SEMANA_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    BLOQUES = [f"{h:02d}:00" for h in range(24)]
    
    hoy = datetime.date.today()
    anio = hoy.year
    
    try:
        mes = int(mes_filtro)
    except (TypeError, ValueError):
        mes = hoy.month
    
    _, num_dias = calendar.monthrange(anio, mes)
    
    agenda = {}
    for dia in range(1, num_dias + 1):
        fecha_obj = datetime.date(anio, mes, dia)
        dia_nombre = DIAS_SEMANA_ES[fecha_obj.weekday()]
        fila_label = f"{dia_nombre} {dia:02d}/{mes:02d}"
        agenda[fila_label] = {bloque: None for bloque in BLOQUES}
        
    eventos = Event.objects.filter(date__month=mes, date__year=anio)
    
    for evento in eventos:
        dia_nombre = DIAS_SEMANA_ES[evento.date.weekday()]
        fila_label = f"{dia_nombre} {evento.date.day:02d}/{evento.date.month:02d}"
        
        if fila_label in agenda:
            hora_inicio = evento.scheduled_time.hour
            duracion = evento.duration_hours if evento.duration_hours else 1
            
            for i in range(duracion):
                hora_actual = hora_inicio + i
                if hora_actual < 24:
                    bloque_actual = f"{hora_actual:02d}:00"
                    if i == 0:
                        agenda[fila_label][bloque_actual] = evento
                    else:
                        if agenda[fila_label][bloque_actual] is None:
                            agenda[fila_label][bloque_actual] = 'spanned'
            
    return agenda, BLOQUES

def index(request):
    return redirect('login')

def home(request):
    # sesion y autenticacion
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        usuario_id = request.GET.get('usuario_id')
        
    if not usuario_id:
        return redirect('login')
        
    try:
        usuario = User.objects.get(id=usuario_id)
        request.session['usuario_id'] = usuario.id
    except User.DoesNotExist:
        request.session.flush()
        return redirect('login')
        
    config_sistema = SystemConfigSingleton() if 'SystemConfigSingleton' in globals() else None
        
    # agenda y asistencias
    meses = [
        {'numero': 1, 'nombre': 'Enero'}, {'numero': 2, 'nombre': 'Febrero'},
        {'numero': 3, 'nombre': 'Marzo'}, {'numero': 4, 'nombre': 'Abril'},
        {'numero': 5, 'nombre': 'Mayo'}, {'numero': 6, 'nombre': 'Junio'},
        {'numero': 7, 'nombre': 'Julio'}, {'numero': 8, 'nombre': 'Agosto'},
        {'numero': 9, 'nombre': 'Septiembre'}, {'numero': 10, 'nombre': 'Octubre'},
        {'numero': 11, 'nombre': 'Noviembre'}, {'numero': 12, 'nombre': 'Diciembre'},
    ]

    mes_query = request.GET.get('mes_filtro')
    try:
        mes_seleccionado = int(mes_query)
    except (TypeError, ValueError):
        mes_seleccionado = datetime.date.today().month
        
    agenda, bloques_horarios = generar_agenda(mes_filtro=mes_seleccionado) if 'generar_agenda' in globals() else ([], [])
        
    historial_asistencias = []
    player_profile = getattr(usuario, 'player_profile', None)
    
    if player_profile:
        asistencias_qs = Attendance.objects.filter(player=player_profile).order_by('-id')
        for item in asistencias_qs:
            item.fecha = item.event.date if item.event else datetime.date.today()
            item.hora_entrada = item.check_in
            item.hora_salida = item.check_out
            if item.check_in and item.check_out:
                dt_in = datetime.datetime.combine(item.fecha, item.check_in)
                dt_out = datetime.datetime.combine(item.fecha, item.check_out)
                diff = dt_out - dt_in
                horas, rem = divmod(diff.seconds, 3600)
                minutos, _ = divmod(rem, 60)
                item.duracion_display = f"{horas}h {minutos}m"
            else:
                item.duracion_display = "--h --m"
            historial_asistencias.append(item)

    # pandas en home

    todos_los_jugadores = Player.objects.select_related('user').all()
    jugador_actual = None

    if usuario.role_type == 'player':
        jugador_actual = player_profile
    else:
        player_id = request.GET.get('player_id')
        if player_id:
            jugador_actual = Player.objects.filter(id=player_id).first()
        else:
            for p in todos_los_jugadores:
                if MatchPerformance.objects.filter(player=p).exists():
                    jugador_actual = p
                    break

    sin_datos = True
    kd_general = winrate_general = hs_promedio = total_fk = total_clutches = 0
    mapas_nombres = "[]"
    mapas_winrate = "[]"
    historial_partidas = []

    if jugador_actual:
        partidas_qs = MatchPerformance.objects.filter(player=jugador_actual).values(
            'map_played__name', 'match_type', 'result', 
            'kills', 'deaths', 'assists', 
            'headshot_percentage', 'first_kills', 'clutches', 'date_played'
        ).order_by('-date_played')

        if partidas_qs.exists():
            sin_datos = False
            df = pd.DataFrame(list(partidas_qs))

            total_kills = int(df['kills'].sum())
            total_deaths = int(df['deaths'].sum())
            kd_general = round(total_kills / total_deaths, 2) if total_deaths > 0 else total_kills
            winrate_general = round((df['result'] == 'WIN').mean() * 100, 1)
            hs_promedio = round(df['headshot_percentage'].mean(), 1)
            total_fk = int(df['first_kills'].sum())
            total_clutches = int(df['clutches'].sum())

            df['kd_partida'] = (df['kills'] / df['deaths'].replace(0, 1)).round(2)
            df['es_victoria'] = (df['result'] == 'WIN').astype(int) * 100
            
            stats_por_mapa = df.groupby('map_played__name').agg(
                winrate=('es_victoria', 'mean')
            ).reset_index()

            mapas_nombres = json.dumps(stats_por_mapa['map_played__name'].tolist())
            mapas_winrate = json.dumps(stats_por_mapa['winrate'].round(1).tolist())
            historial_partidas = df.to_dict('records')

    # metemos todo en un contexto para mandarlo al front
    context = {
        'usuario': usuario,
        'agenda': agenda,
        'bloques_horarios': bloques_horarios,
        'mes_seleccionado': mes_seleccionado,
        'meses': meses,
        'config': config_sistema,
        'miro_boards': globals().get('MIRO_BOARDS', []),
        'historial_asistencias': historial_asistencias,
        
        # Las variables que recibe el include de estadisticas:
        'jugadores': todos_los_jugadores,
        'jugador_actual': jugador_actual,
        'sin_datos': sin_datos,
        'kd_general': kd_general,
        'winrate_general': winrate_general,
        'hs_promedio': hs_promedio,
        'total_fk': total_fk,
        'total_clutches': total_clutches,
        'mapas_nombres': mapas_nombres,
        'mapas_winrate': mapas_winrate,
        'historial_partidas': historial_partidas
    }
        
    # Renderizados según el rol
    if usuario.role_type == 'coach':
        context['mensaje_exito'] = request.session.pop('mensaje_exito', None)
        context['mensaje_error'] = request.session.pop('mensaje_error', None)
        context['is_connected'] = request.session.get('coach_connected', False)
        context['pool_mapas'] = ['Chalet', 'Banco', 'Clubhouse', 'Oregon', 'Border']
        
        anio_actual = datetime.date.today().year
        context['todos_los_jugadores'] = User.objects.filter(role_type='player')
        context['proximos_eventos'] = Event.objects.filter(date__month=mes_seleccionado, date__year=anio_actual).order_by('date', 'scheduled_time')[:3]
        
        return render(request, 'dashboard_coach.html', context)
        
    elif usuario.role_type == 'player':
        context['estado_conexion'] = request.session.get('estado_conexion', 'desconectado')
        context['mensaje_asistencia'] = request.session.pop('mensaje_asistencia', None)
        return render(request, 'dashboard_player.html', context)
        
    else:
        context['players'] = User.objects.filter(role_type='player')
        context['coaches'] = User.objects.filter(role_type='coach')
        context['equipos'] = CompetitiveTeam2026.objects.all().order_by('global_rank')
        return render(request, 'dashboard_admin.html', context)
    
@require_POST
def toggle_coach_status(request):
    usuario_id = request.POST.get('usuario_id', '')
    mes_filtro = request.GET.get('mes_filtro', '')
    estado_actual = request.session.get('coach_connected', False)
    request.session['coach_connected'] = not estado_actual
    
    url_redireccion = f'/home?usuario_id={usuario_id}'
    if mes_filtro: 
        url_redireccion += f'&mes_filtro={mes_filtro}'
    return redirect(url_redireccion)

def logout_view(request):
    logout(request)
    return redirect('login')

class UsuarioController(View):
    def get(self, request):
        return render(request, 'register_user.html')

    def post(self, request):
        nickname_web = request.POST.get('nickname')
        email_web = request.POST.get('email')
        password_web = request.POST.get('password')
        # que rol nos trae el form (por defecto player)
        role_web = request.POST.get('role_type', 'player')

        if not nickname_web or not email_web or not password_web:
            return render(request, 'register_user.html', {'mensaje_error': 'Error: Todos los campos son obligatorios.'})

        if len(password_web) < 4:
            return render(request, 'register_user.html', {'mensaje_error': 'Error: La contraseña debe tener al menos 4 caracteres.'})

        if User.objects.filter(username=nickname_web).exists():
            return render(request, 'register_user.html', {'mensaje_error': 'Error: El Nickname ya está en uso por otra escuadra.'})
            
        if User.objects.filter(email=email_web).exists():
            return render(request, 'register_user.html', {'mensaje_error': 'Error: Ese correo ya está registrado en el Búnker.'})

        password_hasheada = make_password(password_web)

        try:
            nuevo_usuario = User.objects.create(
                name=nickname_web, 
                username=nickname_web, 
                email=email_web, 
                password=password_hasheada, 
                role_type=role_web 
            )

            # se crea sola la ficha de la tabla player si el rol no es Coach
            if role_web == 'player':
                Player.objects.create(position_role='A Definir', team_name='9z Team', user=nuevo_usuario)

            return redirect('login')
        except Exception as e:
            return render(request, 'register_user.html', {'mensaje_error': f'Error crítico de Human Resources: {str(e)}'})

class LoginController(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        nickname_web = request.POST.get('nickname') or request.POST.get('username')
        password_web = request.POST.get('password')

        if not nickname_web or not password_web:
            return render(request, 'login.html', {'mensaje_error': 'Todos los campos son obligatorios.'})

        try:
            usuario_encontrado = User.objects.get(username=nickname_web)
            if check_password(password_web, usuario_encontrado.password):
                # guardamos el ID en la sesion del servidor
                request.session['usuario_id'] = usuario_encontrado.id
                
                # Sincronizamos el estado de conexion inicial para el coach si corresponde
                if usuario_encontrado.role_type == 'coach':
                    request.session['coach_connected'] = True
                
                return redirect(f'/home?usuario_id={usuario_encontrado.id}')
            else:
                return render(request, 'login.html', {'mensaje_error': 'Credenciales incorrectas. Verificá tus datos.'})
        except User.DoesNotExist:
            return render(request, 'login.html', {'mensaje_error': 'Credenciales incorrectas. Verificá tus datos.'})

class CrearEventoController(View):
    def post(self, request):
        titulo_web = request.POST.get('titulo')
        tipo_web = request.POST.get('tipo_evento')
        fecha_web = request.POST.get('fecha')
        hora_web = request.POST.get('hora')
        coach_id = request.POST.get('usuario_id')

        try:
            coach = User.objects.get(id=coach_id)
            if titulo_web and tipo_web and fecha_web and hora_web:
                fecha_objeto = datetime.datetime.strptime(fecha_web, '%Y-%m-%d').date()
                hora_objeto = datetime.datetime.strptime(hora_web, '%H:%M:%S').time() if len(hora_web) > 5 else datetime.datetime.strptime(hora_web, '%H:%M').time()

                Event.objects.create(
                    title=titulo_web, event_type=tipo_web, date=fecha_objeto, scheduled_time=hora_objeto,
                    duration_hours=int(request.POST.get('duration_hours', 1)), maps=request.POST.get('maps', ''),
                    notes=request.POST.get('notes', ''), rival=request.POST.get('rival', ''), coach=coach
                )
                request.session['mensaje_exito'] = '¡Actividad agendada con éxito en la agenda del plantel!'
            else:
                request.session['mensaje_error'] = 'Error: Todos los campos son obligatorios.'
        except Exception as e:
            request.session['mensaje_error'] = f'Hubo un problema al procesar los datos horarios: {e}'

        mes = request.POST.get('mes_filtro', '')
        url = f'/home?usuario_id={coach_id}'
        if mes: url += f'&mes_filtro={mes}'
        return redirect(url)

class RegistrarAsistenciaController(View):
    def post(self, request):
        jugador_id = request.POST.get('usuario_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        mes = request.POST.get('mes')
        
        try:
            player = User.objects.get(id=jugador_id).player_profile
            eventos_hoy = Event.objects.filter(date=datetime.date.today())
            ahora = datetime.datetime.now().time()
            
            if nuevo_estado == 'conectado':
                request.session['estado_conexion'] = 'conectado'
                
                if not eventos_hoy.exists():
                    coach_comodin = User.objects.filter(role_type='coach').first()
                    evento_autonomo = Event.objects.create(
                        title="Sesión de Práctica Autónoma", event_type='training',
                        date=datetime.date.today(), scheduled_time=ahora, duration_hours=1, coach=coach_comodin
                    )
                    Attendance.objects.create(event=evento_autonomo, player=player, is_present=True, check_in=ahora)
                else:
                    for evento in eventos_hoy:
                        Attendance.objects.update_or_create(
                            event=evento, player=player, defaults={'is_present': True, 'check_in': ahora}
                        )
                request.session['mensaje_asistencia'] = "Has cambiado tu estado a CONECTADO. ¡Buen entrenamiento!"
            else:
                request.session['estado_conexion'] = 'desconectado'
                asistencias_hoy = Attendance.objects.filter(player=player, event__date=datetime.date.today())
                for asist in asistencias_hoy:
                    asist.check_out = ahora
                    asist.save()
                request.session['mensaje_asistencia'] = "Te has desconectado del panel."
        except Exception as e:
            request.session['mensaje_asistencia'] = f"Error de persistencia en Asistencia: {str(e)}"
        
        url = f'/home?usuario_id={jugador_id}'
        if mes: url += f'&mes_filtro={mes}'
        return redirect(url)

class EditarEventoController(View):
    def post(self, request):
        evento_id = request.POST.get('evento_id')
        usuario_id = request.POST.get('usuario_id')
        try:
            evento = Event.objects.get(id=evento_id)
            evento.rival = request.POST.get('rival', '')
            evento.maps = request.POST.get('maps', '')
            evento.notes = request.POST.get('notes', '')
            evento.save()
            request.session['mensaje_exito'] = '¡Detalles del evento actualizados correctamente!'
        except Exception as e:
            request.session['mensaje_error'] = f'Error crítico en edición: {str(e)}'
            
        mes = request.POST.get('mes_filtro', '')
        url = f'/home?usuario_id={usuario_id}'
        if mes: url += f'&mes_filtro={mes}'
        return redirect(url)
    
class EditarPerfilController(View):
    def post(self, request):
        usuario_id = request.POST.get('usuario_id')
        nuevo_nombre = request.POST.get('name') 
        biografia_web = request.POST.get('biography', '').strip()
        avatar_web = request.FILES.get('avatar')

        if not usuario_id:
            return redirect('login')

        try:
            usuario_actual = User.objects.get(id=usuario_id)
            if nuevo_nombre:
                usuario_actual.name = nuevo_nombre
                usuario_actual.save()

            if hasattr(usuario_actual, 'player_profile'):
                player_profile = usuario_actual.player_profile
                
                if 'biography' in request.POST:
                    player_profile.biography = biografia_web
                
                if avatar_web:
                    player_profile.avatar = avatar_web
                
                player_profile.save()

            request.session['mensaje_exito'] = "Ficha actualizada con éxito."
            
        except Exception as e:
            request.session['mensaje_error'] = f"Error al guardar expediente: {str(e)}"

        return redirect(f'/home?usuario_id={usuario_id}')

def guardar_equipo(request):
    if request.method == 'POST':
        nombre_web = request.POST.get('name')
        region_web = request.POST.get('region')
        logo_web = request.POST.get('logo_url')
        rank_web = request.POST.get('global_rank')
        
        if nombre_web and region_web:
            try:
                CompetitiveTeam2026.objects.create(
                    name=nombre_web, region=region_web,
                    logo_url=logo_web if logo_web else '/static/images/logos/default-team.png',
                    global_rank=int(rank_web) if rank_web else 99
                )
            except Exception as e:
                print(f"Error al guardar equipo en Laragon: {e}")
        
        admin_actual = User.objects.filter(role_type='admin').first()
        if admin_actual:
            return redirect(f'/home?usuario_id={admin_actual.id}')
            
        return redirect('home')
    
@require_POST
def actualizar_equipo(request):
    equipo_id = request.POST.get('equipo_id')
    admin_id = request.POST.get('usuario_id')
    
    nombre_web = request.POST.get('name')
    region_web = request.POST.get('region')
    logo_web = request.POST.get('logo_url')
    rank_web = request.POST.get('global_rank')
    
    try:
        if equipo_id:
            equipo = CompetitiveTeam2026.objects.get(id=equipo_id)
            equipo.name = nombre_web
            equipo.region = region_web
            equipo.logo_url = logo_web if logo_web else '/static/images/default-team.png'
            equipo.global_rank = int(rank_web) if rank_web else 99
            equipo.save()
    except Exception as e:
        print(f"Error al actualizar equipo: {e}")
        
    return redirect(f'/home?usuario_id={admin_id}')

@require_POST
def eliminar_equipo(request):
    equipo_id = request.POST.get('equipo_id')
    admin_id = request.POST.get('usuario_id')
    
    try:
        if equipo_id:
            CompetitiveTeam2026.objects.filter(id=equipo_id).delete()
    except Exception as e:
        print(f"Error al eliminar equipo: {e}")
        
    return redirect(f'/home?usuario_id={admin_id}')

@require_POST
def editar_jugador_admin(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        
        nuevo_nombre = request.POST.get('name')
        nuevo_username = request.POST.get('username')
        nuevo_rol = request.POST.get('position_role')
        nuevo_equipo = request.POST.get('team_name')
        nueva_bio = request.POST.get('biography')
        
        try:
            # actualizamo el modelo User
            usuario = User.objects.get(id=usuario_id)
            usuario.name = nuevo_nombre
            usuario.username = nuevo_username 
            usuario.save()
            
            # Actualizamos el perfil del jugador
            if hasattr(usuario, 'player_profile'):
                profile = usuario.player_profile
                profile.position_role = nuevo_rol
                profile.team_name = nuevo_equipo
                profile.biography = nueva_bio
                profile.save()
            
            request.session['mensaje_exito'] = "Perfil actualizado correctamente."
        except Exception as e:
            request.session['mensaje_error'] = str(e)
            
    return redirect('/home')


@csrf_exempt
def google_login(request):
    if request.method == 'POST':
        token = request.POST.get('credential')
        try:
            # Valida el token oficial con tu ID de Google y 30 segundos de tolerancia
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                '238189205547-irh68sqouu752u27uea1v47m5dg3uvpr.apps.googleusercontent.com',
                clock_skew_in_seconds=30
            )
            
            email = idinfo['email']
            nombre = idinfo.get('name', 'Usuario Google')
            
            # Usamos la primera parte del mail como username
            base_username = email.split('@')[0] 
            
            # Busca si ya existe en tu base de datos
            usuario = User.objects.filter(username=base_username).first()
            
            if not usuario:
                # Si es nuevo, lo registramos automaticamente
                usuario = User.objects.create(
                    name=nombre,
                    username=base_username,
                    email=email,
                    password=make_password('login_seguro_google_2026'), 
                    role_type='player'
                )
                # Creamos su ficha de jugador
                Player.objects.create(position_role='A Definir', team_name='9z Team', user=usuario)

            # Le iniciamos la sesion
            request.session['usuario_id'] = usuario.id
            
            return redirect(f'/home?usuario_id={usuario.id}')
            
        except ValueError as e:
            # error si hay de google
            print(f"ERROR DE GOOGLE: {str(e)}")
            return redirect('/login?error=Error al iniciar sesion con Google')
            
        except Exception as e:
            # Para cualquier otro error
            print(f"ERROR GENERAL: {str(e)}")
            return redirect('/login?error=Error general')
            
    return redirect('login')


# Fabricante de tokens seguros
signer = TimestampSigner()

def solicitar_recuperacion(request):
    if request.method == 'POST':
        email_web = request.POST.get('email')
        usuario = User.objects.filter(email=email_web).first()
        
        if usuario:
            # Fabricamos un Token firmado con el ID del usuario
            token = signer.sign(str(usuario.id))
            
            # Armamos el link exacto
            reset_link = f"http://localhost:8000/reset/{token}/"
            
            # Diseñamos el mail modo Búnker
            asunto = 'Traino.GG - Recuperación de Acceso'
            html_message = f"""
            <div style="background-color: #0f172a; color: white; padding: 30px; font-family: sans-serif; text-align: center; border-radius: 10px;">
                <h2 style="color: #ff0055; letter-spacing: 1px;">TRAINO&#8203;.GG</h2>
                <p style="color: #94a3b8;">Usuario <b>{usuario.username}</b>,</p>
                <p style="color: #e2e8f0;">Se ha solicitado un cambio de contraseña para tu usuario. Ingresá al siguiente enlace seguro para crear una nueva (caduca en 1 hora):</p>
                <a href="{reset_link}" style="background-color: #ff0055; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin-top: 15px; font-weight: bold;">RESTABLECER CONTRASEÑA</a>
                <p style="margin-top: 30px; font-size: 12px; color: #64748b;">Si no solicitaste este cambio, ignorá este mensaje.</p>
            </div>
            """
            plain_message = strip_tags(html_message)
            
            try:
                # Manda el correo
                send_mail(
                    asunto, plain_message, settings.EMAIL_HOST_USER, [usuario.email], html_message=html_message, fail_silently=False
                )
            except Exception as e:
                print(f"ERROR AL ENVIAR MAIL: {e}")
                
        return redirect('password_reset_done')
    
    return render(request, 'password_reset.html')

def recuperacion_enviada(request):
    return render(request, 'password_reset_sent.html')

def confirmar_recuperacion(request, token):
    try:
        # verificamos que el token sea valido y no tenga mas de 1 hora
        usuario_id = signer.unsign(token, max_age=3600)
        usuario = User.objects.get(id=usuario_id)
    except (SignatureExpired, BadSignature, User.DoesNotExist):
        return render(request, 'password_reset_form.html', {'validlink': False})

    error = None # guardamos mensajes de error
    
    if request.method == 'POST':
        nueva_clave = request.POST.get('new_password')
        confirmar_clave = request.POST.get('confirm_password')

        # primero validamos que las dos contraseñas coincidan
        if nueva_clave != confirmar_clave:
            error = "Las contraseñas no coinciden. Revisá e intentá de nuevo."
        
        # segundo validar que la nueva no sea igual a la vieja con check_password
        elif check_password(nueva_clave, usuario.password):
            error = "La nueva contraseña no puede ser igual a la anterior."
            
        # tercero validar longitud minima por seguridad en el backend
        elif len(nueva_clave) < 4:
            error = "La contraseña debe tener al menos 4 caracteres."
            
        else:
            # si pasa todos los filtros, encriptamos y guardamos
            usuario.password = make_password(nueva_clave)
            usuario.save()
            return render(request, 'password_reset_done.html')
            
    return render(request, 'password_reset_form.html', {'validlink': True, 'error': error})

def dashboard_stats(request):
    # 1. Obtenemos el usuario igual que en la función home
    usuario_id = request.session.get('usuario_id') or request.GET.get('usuario_id')
    usuario = User.objects.filter(id=usuario_id).first() if usuario_id else None

    todos_los_jugadores = Player.objects.select_related('user').all()
    jugador_actual = None

    # 2. Si es player ve sus propias stats automáticamente. Si es coach/admin, puede elegir por GET.
    if usuario and usuario.role_type == 'player':
        jugador_actual = Player.objects.filter(user=usuario).first()
    else:
        player_id = request.GET.get('player_id')
        if player_id:
            jugador_actual = Player.objects.filter(id=player_id).first()
        else:
            # Si no eligió ninguno, agarramos el primero disponible con partidas
            for p in todos_los_jugadores:
                if MatchPerformance.objects.filter(player=p).exists():
                    jugador_actual = p
                    break
            if not jugador_actual:
                jugador_actual = todos_los_jugadores.first()

    if not jugador_actual:
        return render(request, 'dashboard_stats.html', {
            'usuario': usuario,
            'jugadores': todos_los_jugadores,
            'jugador_actual': None,
            'sin_datos': True
        })

    # 3. Traemos las partidas de la base de datos
    partidas_qs = MatchPerformance.objects.filter(player=jugador_actual).values(
        'map_played__name', 'match_type', 'result', 
        'kills', 'deaths', 'assists', 
        'headshot_percentage', 'first_kills', 'clutches', 'date_played'
    ).order_by('-date_played')

    if not partidas_qs.exists():
        return render(request, 'dashboard_stats.html', {
            'usuario': usuario,
            'jugadores': todos_los_jugadores,
            'jugador_actual': jugador_actual,
            'sin_datos': True
        })

    #PANDAS
    df = pd.DataFrame(list(partidas_qs))

    total_kills = int(df['kills'].sum())
    total_deaths = int(df['deaths'].sum())
    kd_general = round(total_kills / total_deaths, 2) if total_deaths > 0 else total_kills
    winrate_general = round((df['result'] == 'WIN').mean() * 100, 1)
    hs_promedio = round(df['headshot_percentage'].mean(), 1)
    total_fk = int(df['first_kills'].sum())
    total_clutches = int(df['clutches'].sum())

    df['kd_partida'] = (df['kills'] / df['deaths'].replace(0, 1)).round(2)
    df['es_victoria'] = (df['result'] == 'WIN').astype(int) * 100
    
    stats_por_mapa = df.groupby('map_played__name').agg(
        winrate=('es_victoria', 'mean')
    ).reset_index()

    mapas_nombres = json.dumps(stats_por_mapa['map_played__name'].tolist())
    mapas_winrate = json.dumps(stats_por_mapa['winrate'].round(1).tolist())
    historial_partidas = df.to_dict('records')

    context = {
        'usuario': usuario,
        'jugadores': todos_los_jugadores,
        'jugador_actual': jugador_actual,
        'kd_general': kd_general,
        'winrate_general': winrate_general,
        'hs_promedio': hs_promedio,
        'total_fk': total_fk,
        'total_clutches': total_clutches,
        'mapas_nombres': mapas_nombres,
        'mapas_winrate': mapas_winrate,
        'historial_partidas': historial_partidas,
        'sin_datos': False
    }

    return render(request, 'dashboard_stats.html', context)


def generar_stats_simuladas(request):
    if request.method == 'POST':
        player_id = request.POST.get('player_id')
        if player_id:
            jugador = Player.objects.filter(id=player_id).first()
            mapas = Map.objects.all()
            
            # le suma al jugador faltante, sin borrar el historial del equipo
            if jugador and mapas.exists():
                for _ in range(5):
                    MatchPerformance.objects.create(
                        player=jugador,
                        map_played=random.choice(mapas),
                        match_type=random.choice(['SCRIM', 'RANKED']),
                        result=random.choices(['WIN', 'LOSS'], weights=[60, 40])[0],
                        kills=random.randint(4, 15),
                        deaths=random.randint(3, 10),
                        assists=random.randint(0, 6),
                        headshot_percentage=round(random.uniform(30.0, 65.0), 1),
                        first_kills=random.randint(0, 4),
                        clutches=random.randint(0, 2)
                    )
                    
    return redirect(f"/home?usuario_id={request.session.get('usuario_id')}&player_id={player_id}")