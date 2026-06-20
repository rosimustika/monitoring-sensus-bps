from django.contrib import admin
from .models import Wilayah

@admin.register(Wilayah)
class WilayahAdmin(admin.ModelAdmin):
    # 🔄 UBAH 'kode_wilayah' MENJADI 'kode' DI SINI:
    list_display = ('kode', 'nama_kecamatan', 'nama_kelurahan', 'target_usaha')
    search_fields = ('nama_kecamatan', 'nama_kelurahan')