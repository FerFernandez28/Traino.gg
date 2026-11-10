from django.contrib import admin
from .models.models import (
    User,
    Player,
    Event,
    Attendance,
    CompetitiveTeam2026,
    Map,
    MatchPerformance,
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'name', 'email', 'role_type')
    list_filter = ('role_type',)
    search_fields = ('username', 'name', 'email')

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'position_role', 'team_name')
    search_fields = ('user__username', 'position_role', 'team_name')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'event_type', 'date', 'scheduled_time', 'rival')
    list_filter = ('event_type', 'date')
    search_fields = ('title', 'rival')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'player', 'is_present', 'check_in', 'check_out')
    list_filter = ('is_present', 'event')

@admin.register(CompetitiveTeam2026)
class CompetitiveTeam2026Admin(admin.ModelAdmin):
    list_display = ('id', 'name', 'region', 'global_rank', 'created_at')
    list_filter = ('region',)
    search_fields = ('name',)

@admin.register(Map)
class MapAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(MatchPerformance)
class MatchPerformanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'player', 'map_played', 'match_type', 'result', 'kills', 'deaths', 'assists')
    list_filter = ('match_type', 'result', 'map_played')
    search_fields = ('player__user__username', 'map_played__name')