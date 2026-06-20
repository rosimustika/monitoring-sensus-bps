from django.urls import path
from . import views

urlpatterns = [
    # Rute Utama & Dashboard
    path('', views.redirect_dashboard, name='home'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/petugas/', views.dashboard_petugas, name='dashboard_petugas'),
    
    # Rute Master Data & Validasi
    path('wilayah/', views.daftar_wilayah, name='daftar_wilayah'),
    path('petugas/', views.daftar_petugas, name='daftar_petugas'),
    path('validasi/', views.validasi_laporan, name='validasi_laporan'),
    path('kendala/', views.analisis_kendala, name='analisis_kendala'),
    
    # Rute Laporan Harian
    path('laporan/input/', views.input_laporan, name='input_laporan'),
    path('laporan/riwayat/', views.riwayat_laporan, name='riwayat_laporan'),
    
    # Rute Ekspor Berkas (Excel & PDF)
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    
    # Rute Fitur Tambah Data
    path('wilayah/tambah/', views.tambah_wilayah, name='tambah_wilayah'),
    path('petugas/tambah/', views.tambah_petugas, name='tambah_petugas'),
    
    # 🔄 SEKSI EDIT & HAPUS YANG SUDAH DIPERBAIKI (MENGGUNAKAN UUID):
    path('wilayah/edit/<uuid:pk>/', views.edit_wilayah, name='edit_wilayah'),
    path('wilayah/hapus/<uuid:pk>/', views.hapus_wilayah, name='hapus_wilayah'),

# ... rute jalur yang sudah ada sebelumnya ...
    path('petugas/tambah/', views.tambah_petugas, name='tambah_petugas'),
    
    # ➕ TAMBAHKAN KEDUA BARIS JALUR BARU INI:
    path('petugas/edit/<uuid:pk>/', views.edit_petugas, name='edit_petugas'),
    path('petugas/hapus/<uuid:pk>/', views.hapus_petugas, name='hapus_petugas'),
    
]