from django.contrib import admin
from .models import Petugas, ProgresHarian, Kendala

@admin.register(Petugas)
class PetugasAdmin(admin.ModelAdmin):
    list_display = ['nip', 'nama', 'no_hp', 'status_aktif']
    search_fields = ['nip', 'nama']
    list_filter = ['status_aktif']

@admin.register(ProgresHarian)
class ProgresHarianAdmin(admin.ModelAdmin):
    list_display = ['petugas', 'tanggal_laporan', 'jumlah_selesai', 'jumlah_bermasalah', 'status_validasi']
    list_filter = ['status_validasi', 'tanggal_laporan']
    search_fields = ['petugas__nama']

@admin.register(Kendala)
class KendalaAdmin(admin.ModelAdmin):
    list_display = ['progres', 'jenis_kendala', 'status_penanganan', 'created_at']
    list_filter = ['jenis_kendala', 'status_penanganan']