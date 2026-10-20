import random
from django.core.management.base import BaseCommand
from traino.models.models import Player, Map, MatchPerformance

class Command(BaseCommand):
    help = 'Genera 10 partidas de prueba para TODOS los jugadores'

    def handle(self, *args, **kwargs):
        # jugadores y mapas
        jugadores = Player.objects.all()
        mapas = list(Map.objects.all())

        if not jugadores or not mapas:
            self.stdout.write(self.style.ERROR('Faltan jugadores o mapas en la base de datos.'))
            return

        # borramos todo x si hay algo viejo
        MatchPerformance.objects.all().delete()

        resultados = ['WIN', 'LOSS']
        tipos = ['RANKED', 'SCRIM']
        
        # a cada jugador le creamos 10 partidas a cada uno
        for jugador in jugadores:
            for i in range(10):
                MatchPerformance.objects.create(
                    player=jugador,
                    map_played=random.choice(mapas),
                    match_type=random.choice(tipos),
                    result=random.choices(resultados, weights=[60, 40])[0],
                    kills=random.randint(2, 15),
                    deaths=random.randint(3, 10),
                    assists=random.randint(0, 5),
                    headshot_percentage=round(random.uniform(30.0, 65.0), 1),
                    first_kills=random.randint(0, 3),
                    clutches=random.randint(0, 2)
                )
            self.stdout.write(self.style.SUCCESS(f'10 partidas creadas para {jugador.user.username} (Player ID: {jugador.id})'))