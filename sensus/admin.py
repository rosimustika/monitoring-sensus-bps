from django.contrib import admin
from .models import SensusEkonomi

@admin.register(SensusEkonomi)
class SensusEkonomiAdmin(admin.ModelAdmin):
    list_display = ['nama_sensus', 'tahun_sensus', 'tanggal_mulai', 'tanggal_selesai', 'status']
    list_filter = ['status', 'tahun_sensus']