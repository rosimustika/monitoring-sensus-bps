import os
import pickle
import pandas as pd
from datetime import date
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count

# Import seluruh model database pendukung proyek
from wilayah.models import Wilayah
from progres.models import Petugas, ProgresHarian, Kendala
from sensus.models import SensusEkonomi

# Library untuk Export Data
from openpyxl import Workbook
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

def redirect_dashboard(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard_admin')
        return redirect('dashboard_petugas')
    return redirect('login')


# ============================================================
# 1. DASHBOARD UTAMA ADMIN (HYBRID: DESA & K-MEANS KECAMATAN)
# ============================================================
@login_required
def dashboard_admin(request):
    from datetime import date
    today = date.today()

    # ---- A. QUERY KARTU STATISTIK MENTAH ----
    total_wilayah = Wilayah.objects.count()
    total_petugas = Petugas.objects.filter(status_aktif=True).count()
    total_laporan = ProgresHarian.objects.count()
    total_kendala = Kendala.objects.count()

    laporan_terbaru = ProgresHarian.objects.select_related('petugas', 'wilayah').order_by('-created_at')[:5]
    kendala_terbaru = Kendala.objects.select_related('progres').order_by('-created_at')[:5]

    # ============================================================
    # 🤖 [BAGIAN 1] PROSES MACHINE LEARNING K-MEANS (PER KECAMATAN)
    # ============================================================
    if ProgresHarian.objects.exists():
        kecamatan_stats = ProgresHarian.objects.values('wilayah__nama_kecamatan').annotate(
            total_selesai=Sum('jumlah_selesai'),
            total_bermasalah=Sum('jumlah_bermasalah')
        )

        data_wilayah = []
        for stat in kecamatan_stats:
            nama_kec = stat['wilayah__nama_kecamatan'] or "Tanpa Nama"
            selesai = stat['total_selesai'] or 0
            bermasalah = stat['total_bermasalah'] or 0
            target = Wilayah.objects.filter(nama_kecamatan=nama_kec).aggregate(Sum('target_usaha'))['target_usaha__sum'] or 1

            persentase = round((selesai / target) * 100, 1)
            data_wilayah.append({
                'kecamatan': nama_kec,
                'total_selesai': selesai,
                'total_bermasalah': bermasalah,
                'persentase': min(persentase, 100.0)
            })
    else:
        # Data simulasi fallback
        data_wilayah = [
            {'kecamatan': 'Bandung', 'total_selesai': 1676, 'total_bermasalah': 461, 'persentase': 62.3},
            {'kecamatan': 'Besuki', 'total_selesai': 756, 'total_bermasalah': 283, 'persentase': 46.5},
            {'kecamatan': 'Boyolangu', 'total_selesai': 2027, 'total_bermasalah': 415, 'persentase': 61.6},
            {'kecamatan': 'Gondang', 'total_selesai': 2197, 'total_bermasalah': 647, 'persentase': 68.0},
            {'kecamatan': 'Tulungagung Kota', 'total_selesai': 3105, 'total_bermasalah': 210, 'persentase': 85.2},
            {'kecamatan': 'Kauman', 'total_selesai': 1980, 'total_bermasalah': 340, 'persentase': 72.1},
        ]

    # Jalankan Model K-Means Prediksi (Skala Kecamatan)
    df_input = pd.DataFrame(data_wilayah)
    model_path = os.path.join(settings.BASE_DIR, 'saved_models')

    try:
        with open(os.path.join(model_path, 'kmeans_model.pkl'), 'rb') as f:
            kmeans = pickle.load(f)
        with open(os.path.join(model_path, 'scaler.pkl'), 'rb') as f:
            scaler = pickle.load(f)
        with open(os.path.join(model_path, 'status_map.pkl'), 'rb') as f:
            status_map = pickle.load(f)

        X = df_input[['total_selesai', 'total_bermasalah', 'persentase']]
        X_scaled = scaler.transform(X)
        hasil_prediksi = kmeans.predict(X_scaled)

        for idx, cluster_id in enumerate(hasil_prediksi):
            nama_status = status_map[cluster_id]
            data_wilayah[idx]['status'] = nama_status
            if nama_status == 'Lancar':
                data_wilayah[idx]['warna'] = '#28a745'
            elif nama_status == 'Perlu Perhatian':
                data_wilayah[idx]['warna'] = '#ffc107'
            else:
                data_wilayah[idx]['warna'] = '#dc3545'
    except Exception as e:
        # KITA SUNTIKKAN PESAN EROR ASLI DI SINI AGAR MUNCUL DI LAYAR WEB
        messages.error(request, f'Eror Modul K-Means ML: {e}')
        for idx in range(len(data_wilayah)):
            data_wilayah[idx]['status'] = 'Belum Terklaster'
            data_wilayah[idx]['warna'] = '#6c757d'


    # ============================================================
    # 📊 [BAGIAN 2] AGREGASI GRAFIK UTAMA & PROGRESS (PER DESA)
    # ============================================================
    wilayah_list = Wilayah.objects.all()
    grafik_labels = []
    grafik_selesai = []
    grafik_target = []
    grafik_bermasalah = []
    progres_wilayah = []

    for w in wilayah_list:
        total_selesai_desa = ProgresHarian.objects.filter(wilayah=w).aggregate(Sum('jumlah_selesai'))['jumlah_selesai__sum'] or 0
        total_bermasalah_desa = ProgresHarian.objects.filter(wilayah=w).aggregate(Sum('jumlah_bermasalah'))['jumlah_bermasalah__sum'] or 0

        label_desa = f"{w.nama_kecamatan}-{w.nama_kelurahan}"
        target_desa = w.target_usaha if w.target_usaha > 0 else 1
        persen_desa = round((total_selesai_desa / target_desa * 100), 1)

        grafik_labels.append(label_desa)
        grafik_selesai.append(total_selesai_desa)
        grafik_target.append(target_desa)
        grafik_bermasalah.append(total_bermasalah_desa)

        progres_wilayah.append({
            'label': label_desa,
            'selesai': total_selesai_desa,
            'target': target_desa,
            'persen': min(persen_desa, 100.0),
        })

    # ---- C. FITUR BARU TEMAN: MONITORING ABSENSI & NOTIFIKASI ----
    status_petugas = []
    petugas_all = Petugas.objects.filter(status_aktif=True)
    jumlah_belum_lapor = 0

    for p in petugas_all:
        laporan_terakhir = ProgresHarian.objects.filter(petugas=p).order_by('-tanggal_laporan').first()
        if laporan_terakhir:
            selisih = (today - laporan_terakhir.tanggal_laporan).days
            if selisih == 0:
                status = "sudah hari ini"
            else:
                status = f"belum ({selisih} hari)"
                jumlah_belum_lapor += 1
        else:
            status = "belum pernah lapor"
            selisih = None
            jumlah_belum_lapor += 1

        status_petugas.append({
            'nama': p.nama,
            'status': status,
            'selisih': selisih if laporan_terakhir else None
        })

    # ---- D. GRAFIK KENDALA & EVALUASI PROGRESS TOTAL ----
    total_target_all = sum(grafik_target)
    total_selesai_all = sum(grafik_selesai)
    progress_total = round((total_selesai_all / total_target_all * 100), 1) if total_target_all > 0 else 0

    kendala_labels = []
    kendala_data = []
    jenis_list = [
        ('tidak_ditemukan', 'Tidak Ditemukan'),
        ('menolak', 'Pemilik Menolak'),
        ('alamat_salah', 'Alamat Salah'),
        ('tutup', 'Usaha Tutup'),
        ('akses_jalan', 'Akses Jalan'),
        ('cuaca', 'Cuaca'),
        ('lainnya', 'Lainnya'),
    ]

    for kode, label in jenis_list:
        jumlah = Kendala.objects.filter(jenis_kendala=kode).count()
        if jumlah > 0:
            kendala_labels.append(label)
            kendala_data.append(jumlah)

    kendala_wilayah = Kendala.objects.values('progres__wilayah__nama_kecamatan').annotate(total=Count('id')).order_by('-total')[:5]
    kendala_terbaru_detail = Kendala.objects.select_related('progres__wilayah').order_by('-created_at')[:5]

    context = {
        'total_wilayah': total_wilayah,
        'total_petugas': total_petugas,
        'total_laporan': total_laporan,
        'total_kendala': total_kendala,
        'laporan_terbaru': laporan_terbaru,
        'kendala_terbaru': kendala_terbaru,

        # Variabel Grafik & Progress Bar
        'grafik_labels': grafik_labels,
        'grafik_selesai': grafik_selesai,
        'grafik_target': grafik_target,
        'grafik_bermasalah': grafik_bermasalah,
        'progres_wilayah': progres_wilayah,
        'wilayah_range': range(len(grafik_labels)),

        # Variabel Analisis K-Means
        'dashboard_data': data_wilayah,

        # Variabel Peringatan & Kendala
        'status_petugas': status_petugas,
        'kendala_wilayah': kendala_wilayah,
        'kendala_terbaru_detail': kendala_terbaru_detail,
        'kendala_labels': kendala_labels,
        'kendala_data': kendala_data,
        'belum_lapor': jumlah_belum_lapor,
        'progress_total': progress_total,
    }
    return render(request, 'dashboard/admin.html', context)


# ============================================================
# 2. LOGIKA INPUT LAPORAN HARIAN (PETUGAS)
# ============================================================
@login_required
def input_laporan(request):
    try:
        profil_petugas = request.user.petugas
    except Exception:
        messages.error(request, 'Akun Anda Admin. Gunakan akun khusus petugas untuk input.')
        return render(request, 'dashboard/input_laporan.html', {'wilayah_list': Wilayah.objects.all()})

    if request.method == 'POST':
        try:
            id_wilayah = request.POST.get('wilayah')
            tanggal = request.POST.get('tanggal_laporan')
            selesai = request.POST.get('jumlah_selesai', 0)
            bermasalah = request.POST.get('jumlah_bermasalah', 0)
            catatan = request.POST.get('catatan', '')

            wilayah_obj = Wilayah.objects.get(id=id_wilayah)

            progres = ProgresHarian.objects.create(
                petugas=profil_petugas,
                wilayah=wilayah_obj,
                tanggal_laporan=tanggal,
                jumlah_selesai=int(selesai) if selesai else 0,
                jumlah_bermasalah=int(bermasalah) if bermasalah else 0,
                catatan=catatan
            )

            jenis_list = request.POST.getlist('jenis_kendala[]')
            deskripsi_list = request.POST.getlist('deskripsi_kendala[]')

            for i, jenis in enumerate(jenis_list):
                deskripsi = deskripsi_list[i] if i < len(deskripsi_list) else ''
                if jenis:
                    Kendala.objects.create(
                        progres=progres,
                        jenis_kendala=jenis,
                        deskripsi=deskripsi
                    )

            messages.success(request, 'Laporan dan kendala berhasil disimpan!')
            return redirect('dashboard_petugas')
        except Exception as e:
            messages.error(request, f'Gagal menyimpan laporan: {e}')

    return render(request, 'dashboard/input_laporan.html', {'wilayah_list': Wilayah.objects.all()})


# ============================================================
# 3. DASHBOARD PENGGUNA PETUGAS
# ============================================================
@login_required
def dashboard_petugas(request):
    try:
        petugas = Petugas.objects.get(user=request.user)
        laporan = ProgresHarian.objects.filter(petugas=petugas).order_by('-tanggal_laporan')[:7]

        total_selesai = sum([l.jumlah_selesai for l in laporan])
        total_bermasalah = sum([l.jumlah_bermasalah for l in laporan])
        sudah_lapor = ProgresHarian.objects.filter(petugas=petugas, tanggal_laporan=date.today()).exists()
    except Petugas.DoesNotExist:
        laporan = []
        total_selesai = 0
        total_bermasalah = 0
        sudah_lapor = False

    context = {
        'laporan': laporan,
        'total_selesai': total_selesai,
        'total_bermasalah': total_bermasalah,
        'sudah_lapor': sudah_lapor,
    }
    return render(request, 'dashboard/petugas.html', context)


# ============================================================
# 4. MASTER DATA & VALIDASI UTAS
# ============================================================
@login_required
def daftar_wilayah(request):
    return render(request, 'dashboard/wilayah.html', {'wilayah': Wilayah.objects.all()})

@login_required
def daftar_petugas(request):
    return render(request, 'dashboard/petugas_list.html', {'petugas': Petugas.objects.all()})

@login_required
def validasi_laporan(request):
    if request.method == 'POST':
        laporan_id = request.POST.get('laporan_id')
        aksi = request.POST.get('aksi')
        try:
            laporan = ProgresHarian.objects.get(id=laporan_id)
            laporan.validator = request.user
            if aksi == 'approve':
                laporan.status_validasi = 'disetujui'
                messages.success(request, f'Laporan {laporan.petugas.nama} berhasil disetujui!')
            elif aksi == 'reject':
                laporan.status_validasi = 'ditolak'
                messages.warning(request, f'Laporan {laporan.petugas.nama} ditolak!')
            laporan.save()
        except Exception as e:
            messages.error(request, f'Gagal memproses validasi: {e}')
        return redirect('validasi_laporan')

    menunggu = ProgresHarian.objects.filter(status_validasi='menunggu').order_by('-created_at')
    selesai = ProgresHarian.objects.filter(status_validasi__in=['disetujui', 'ditolak']).order_by('-updated_at')[:10]
    return render(request, 'dashboard/validasi.html', {'laporan_menunggu': menunggu, 'laporan_selesai': selesai})

@login_required
def analisis_kendala(request):
    return render(request, 'dashboard/kendala.html', {'kendala': Kendala.objects.all().order_by('-created_at')})


# ============================================================
# 5. RIWAYAT LAPORAN DENGAN FILTER
# ============================================================
@login_required
def riwayat_laporan(request):
    try:
        petugas = Petugas.objects.get(user=request.user)
        laporan = ProgresHarian.objects.filter(petugas=petugas)

        tanggal = request.GET.get('tanggal')
        wilayah = request.GET.get('wilayah')

        if tanggal:
            laporan = laporan.filter(tanggal_laporan=tanggal)
        if wilayah:
            laporan = laporan.filter(wilayah_id=wilayah)
        laporan = laporan.order_by('-tanggal_laporan')
    except Petugas.DoesNotExist:
        laporan = []

    return render(request, 'dashboard/riwayat.html', {'laporan': laporan, 'wilayah_list': Wilayah.objects.all()})


# ============================================================
# 6. ENGINE PENCETAKAN LAPORAN (EXCEL & PDF)
# ============================================================
@login_required
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Laporan"
    ws.append(["Tanggal", "Petugas", "Wilayah", "Selesai", "Bermasalah"])

    laporan = ProgresHarian.objects.all()
    for item in laporan:
        ws.append([
            str(item.tanggal_laporan),
            item.petugas.nama,
            f"{item.wilayah.nama_kecamatan}-{item.wilayah.nama_kelurahan}",
            item.jumlah_selesai,
            item.jumlah_bermasalah
        ])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename=laporan_sensus.xlsx'
    wb.save(response)
    return response

@login_required
def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_sensus.pdf"'

    doc = SimpleDocTemplate(response)
    data = [['Tanggal', 'Petugas', 'Wilayah', 'Selesai', 'Bermasalah']]

    laporan = ProgresHarian.objects.all()
    for item in laporan:
        data.append([
            str(item.tanggal_laporan),
            item.petugas.nama,
            f"{item.wilayah.nama_kecamatan}-{item.wilayah.nama_kelurahan}",
            str(item.jumlah_selesai),
            str(item.jumlah_bermasalah),
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ]))
    doc.build([table])
    return response


# ============================================================
# ➕ UTILITY: TAMBAH WILAYAH BARU (DIUPDATE & DISECURE)
# ============================================================
@login_required
def tambah_wilayah(request):
    if request.method == 'POST':
        kode = request.POST.get('kode_wilayah', '').strip()
        kecamatan = request.POST.get('nama_kecamatan', '').strip()
        kelurahan = request.POST.get('nama_kelurahan', '').strip()
        target = request.POST.get('target_usaha', '0').strip()

        # Validasi ketat menggunakan strip() untuk menghindari bypass spasi
        if kode and kecamatan and kelurahan:
            Wilayah.objects.create(
                kode=kode,
                nama_kecamatan=kecamatan,
                nama_kelurahan=kelurahan,
                target_usaha=int(target) if target.isdigit() else 0
            )
            messages.success(request, f'Wilayah {kecamatan} - {kelurahan} berhasil ditambahkan!')
            return redirect('daftar_wilayah')
        else:
            messages.error(request, 'Gagal: Kolom Kode, Kecamatan, dan Kelurahan wajib diisi!')

    return render(request, 'dashboard/tambah_wilayah.html')


# ============================================================
# ✏️ UTILITY: EDIT DATA WILAYAH
# ============================================================
@login_required
def edit_wilayah(request, pk):
    try:
        wilayah = Wilayah.objects.get(id=pk)
    except Wilayah.DoesNotExist:
        messages.error(request, 'Data wilayah tidak ditemukan!')
        return redirect('daftar_wilayah')

    if request.method == 'POST':
        wilayah.kode = request.POST.get('kode_wilayah', '').strip()
        wilayah.nama_kecamatan = request.POST.get('nama_kecamatan', '').strip()
        wilayah.nama_kelurahan = request.POST.get('nama_kelurahan', '').strip()

        target = request.POST.get('target_usaha', '0').strip()
        wilayah.target_usaha = int(target) if target.isdigit() else 0

        wilayah.save()
        messages.success(request, f'Wilayah {wilayah.nama_kecamatan} berhasil diperbarui!')
        return redirect('daftar_wilayah')

    return render(request, 'dashboard/edit_wilayah.html', {'wilayah': wilayah})


# ============================================================
# ❌ UTILITY: HAPUS DATA WILAYAH
# ============================================================
@login_required
def hapus_wilayah(request, pk):
    try:
        wilayah = Wilayah.objects.get(id=pk)
        nama_target = f"{wilayah.nama_kecamatan} - {wilayah.nama_kelurahan}"
        wilayah.delete()
        messages.warning(request, f'Wilayah {nama_target} berhasil dihapus dari sistem!')
    except Exception as e:
        messages.error(request, f'Gagal menghapus data: {e}')

    return redirect('daftar_wilayah')


# ============================================================
# ➕ UTILITY: TAMBAH USER / PETUGAS BARU (FIXED & SECURE)
# ============================================================
@login_required
def tambah_petugas(request):
    from django.db import transaction
    import random # Kita gunakan library ini untuk generate NIP unik otomatis

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        nama_lengkap = request.POST.get('nama', '').strip()

        if username and password and nama_lengkap:
            # 1. Cek manual di awal apakah username sudah terdaftar
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Gagal menambah petugas: Username tersebut sudah dipakai.')
            else:
                try:
                    # 2. Amankan dengan transaction.atomic
                    with transaction.atomic():
                        user_baru = User.objects.create_user(username=username, password=password)

                        # Buat NIP dummy acak 18 digit unik khusus untuk BPS Sensus
                        dummy_nip = str(random.randint(100000000000000000, 999999999999999999))

                        # Simpan ke tabel Petugas lengkap dengan NIP-nya
                        Petugas.objects.create(
                            user=user_baru,
                            nama=nama_lengkap,
                            nip=dummy_nip, # <--- NIP otomatis disuntikkan di sini
                            status_aktif=True
                        )
                    messages.success(request, f'Petugas {nama_lengkap} berhasil didaftarkan!')
                    return redirect('daftar_petugas')
                except Exception as e:
                    messages.error(request, f'Eror Database pada tabel Petugas: {e}')
        else:
            messages.error(request, 'Gagal: Kolom Nama, Username, dan Password wajib diisi!')

    return render(request, 'dashboard/tambah_petugas.html')


# ============================================================
# ✏️ UTILITY: EDIT DATA & AKUN PETUGAS
# ============================================================
@login_required
def edit_petugas(request, pk):
    try:
        petugas = Petugas.objects.get(id=pk)
    except Petugas.DoesNotExist:
        messages.error(request, 'Data petugas tidak ditemukan!')
        return redirect('daftar_petugas')

    if request.method == 'POST':
        petugas.nama = request.POST.get('nama', '').strip()
        petugas.status_aktif = request.POST.get('status_aktif') == 'True'
        petugas.save()

        user = static_user = petugas.user
        username_baru = request.POST.get('username', '').strip()
        if username_baru and username_baru != user.username:
            if User.objects.filter(username=username_baru).exclude(id=user.id).exists():
                messages.error(request, 'Username sudah digunakan oleh akun lain!')
            else:
                user.username = username_baru
                user.save()

        messages.success(request, f'Data petugas {petugas.nama} berhasil diperbarui!')
        return redirect('daftar_petugas')

    return render(request, 'dashboard/edit_petugas.html', {'petugas': petugas})


# ============================================================
# ❌ UTILITY: HAPUS PROFIL & USER LOGIN PETUGAS
# ============================================================
@login_required
def hapus_petugas(request, pk):
    try:
        petugas = Petugas.objects.get(id=pk)
        user_login = petugas.user
        nama_petugas = petugas.nama

        petugas.delete()
        if user_login:
            user_login.delete()

        messages.warning(request, f'Petugas {nama_petugas} dan akun loginnya berhasil dihapus!')
    except Exception as e:
        messages.error(request, f'Gagal menghapus data petugas: {e}')

    return redirect('daftar_petugas')