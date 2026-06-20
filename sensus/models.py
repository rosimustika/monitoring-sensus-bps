from django.db import models
import uuid

class SensusEkonomi(models.Model):
    STATUS_CHOICES = [
        ('persiapan', 'Persiapan'),
        ('berjalan', 'Sedang Berjalan'),
        ('selesai', 'Selesai'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tahun_sensus = models.CharField(max_length=4)
    nama_sensus = models.CharField(max_length=200)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='persiapan')
    deskripsi = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama_sensus} {self.tahun_sensus}"

    class Meta:
        verbose_name = 'Sensus Ekonomi'
        verbose_name_plural = 'Data Sensus Ekonomi'