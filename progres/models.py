from django.db import models
from django.contrib.auth.models import User
from wilayah.models import Wilayah
import uuid

class Petugas(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nip = models.CharField(max_length=20, unique=True)
    nama = models.CharField(max_length=200)
    no_hp = models.CharField(max_length=15)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    status_aktif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama

    class Meta:
        verbose_name = 'Petugas'
        verbose_name_plural = 'Data Petugas'


class ProgresHarian(models.Model):
    STATUS_VALIDASI = [
        ('menunggu', 'Menunggu Validasi'),
        ('disetujui', 'Disetujui'),
        ('ditolak', 'Ditolak'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    petugas = models.ForeignKey(Petugas, on_delete=models.CASCADE)
    wilayah = models.ForeignKey(Wilayah, on_delete=models.SET_NULL, null=True, blank=True)  # field baru
    tanggal_laporan = models.DateField()
    jumlah_selesai = models.IntegerField(default=0)
    jumlah_bermasalah = models.IntegerField(default=0)
    catatan = models.TextField(blank=True)
    status_validasi = models.CharField(max_length=20, choices=STATUS_VALIDASI, default='menunggu')
    validator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Laporan {self.petugas.nama} - {self.tanggal_laporan}"

    class Meta:
        verbose_name = 'Progres Harian'
        verbose_name_plural = 'Data Progres Harian'


class Kendala(models.Model):
    JENIS_KENDALA = [
        ('tidak_ditemukan', 'Usaha Tidak Ditemukan'),
        ('menolak', 'Pemilik Menolak'),
        ('alamat_salah', 'Alamat Tidak Sesuai'),
        ('tutup', 'Usaha Sudah Tutup'),
        ('akses_jalan', 'Akses Jalan Sulit'),
        ('cuaca', 'Kendala Cuaca'),
        ('lainnya', 'Lainnya'),
    ]
    STATUS_PENANGANAN = [
        ('belum', 'Belum Ditangani'),
        ('proses', 'Sedang Diproses'),
        ('selesai', 'Sudah Diselesaikan'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    progres = models.ForeignKey(ProgresHarian, on_delete=models.CASCADE)
    jenis_kendala = models.CharField(max_length=50, choices=JENIS_KENDALA)
    deskripsi = models.TextField()
    status_penanganan = models.CharField(max_length=20, choices=STATUS_PENANGANAN, default='belum')
    solusi = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Kendala {self.get_jenis_kendala_display()} - {self.progres}"

    class Meta:
        verbose_name = 'Kendala'
        verbose_name_plural = 'Data Kendala'