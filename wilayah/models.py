from django.db import models
import uuid

class Wilayah(models.Model):
    # Jika kamu menggunakan UUID sebagai primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # ➕ TAMBAHKAN BARIS BARU INI (Untuk menampung Kode Wilayah BPS):
    kode = models.CharField(max_length=50, blank=True, null=True)
    
    nama_kecamatan = models.CharField(max_length=100)
    nama_kelurahan = models.CharField(max_length=100)
    target_usaha = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.nama_kecamatan} - {self.nama_kelurahan}"