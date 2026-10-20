import json
import os
from datetime import datetime

# ==========================================
# KONFIGURASI PATH
# ==========================================
PROFIL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profil_user.json")
LOWONGAN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lowongan_cocok.json")
CV_PATHS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PATH_CV", "cv_paths.json")

FASE1_SCRIPT = os.path.join(os.path.dirname(__file__), "job_hunter.py")
FASE2_SCRIPT = os.path.join(os.path.dirname(__file__), "fase2_scout_v2.py")
FASE3_SCRIPT = os.path.join(os.path.dirname(__file__), "fase3_tailor_v2.py")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def load_lowongan():
    if os.path.exists(LOWONGAN_FILE):
        try:
            with open(LOWONGAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_lowongan(jobs):
    with open(LOWONGAN_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

def validasi_dependencies():
    """Cek file script ada atau tidak"""
    missing = []

    if not os.path.exists(FASE1_SCRIPT):
        missing.append("❌ Fase 1: job_hunter.py tidak ditemukan")
    if not os.path.exists(FASE2_SCRIPT):
        missing.append("❌ Fase 2: fase2_scout_v2.py tidak ditemukan")
    if not os.path.exists(FASE3_SCRIPT):
        missing.append("❌ Fase 3: fase3_tailor_v2.py tidak ditemukan")

    if missing:
        print("\n⚠️ FILE TIDAK DITEMUKAN:")
        for m in missing:
            print(f"   {m}")
        return False

    return True

# ==========================================
# QUICK UPDATE PROMPT (CEK STATUS LOKER)
# ==========================================
def quick_update_prompt():
    """Cek status loker yang sudah di-apply atau belum"""
    jobs = load_lowongan()

    if not jobs:
        return

    # Filter pending & applied dalam 7 hari terakhir
    pending_jobs = [j for j in jobs if j.get('status', 'pending') == 'pending']

    recent_applied = []
    for j in jobs:
        if j.get('status') == 'applied' and j.get('tanggal_dilamar'):
            try:
                tanggal = datetime.strptime(j['tanggal_dilamar'], "%Y-%m-%d")
                if (datetime.now() - tanggal).days <= 7:
                    recent_applied.append(j)
            except:
                pass

    review_jobs = pending_jobs #+ recent_applied

    if not review_jobs:
        return

    print("\n" + "="*60)
    print("📋 CEK STATUS LOKER - Lowongan yang perlu review:")
    print("="*60)

    for i, job in enumerate(review_jobs, 1):
        status_icon = {
            'pending': '🟡',
            'applied': '🟢'
        }.get(job.get('status', 'pending'), '⚪')

        print(f"\n[{i}] {status_icon} {job['title'][:45]}")
        print(f"    🏢 {job.get('company', 'N/A')[:30]}")
        print(f"    📅 {job.get('tanggal_ditemukan', 'N/A')}")
        if job.get('tanggal_dilamar'):
            print(f"    ✅ Dilamar: {job['tanggal_dilamar']}")

    print("\n" + "="*60)
    update_choice = input("Ada yang mau diupdate statusnya? (y/n): ").strip().lower()

    if update_choice != 'y':
        return

    while True:
        pilihan = input(f"\nPilih nomor (1-{len(review_jobs)}, 0=selesai): ").strip()

        if pilihan == '0':
            break

        try:
            idx = int(pilihan) - 1
            if idx < 0 or idx >= len(review_jobs):
                print("❌ Nomor tidak valid!")
                continue
        except:
            print("❌ Input tidak valid!")
            continue

        selected_job = review_jobs[idx]
        original_idx = next(i for i, j in enumerate(jobs) if j['url'] == selected_job['url'])

        updated = update_single_job(jobs, original_idx)

        if updated:
            jobs = load_lowongan()

        lanjut = input("\nUpdate lowongan lain? (y/n): ").strip().lower()
        if lanjut != 'y':
            break

    print("\n✅ Update status selesai!\n")

def update_single_job(jobs, idx):
    """Helper untuk update status satu job"""
    selected = jobs[idx]

    print(f"\n📋 Lowongan: {selected['title']}")
    print(f"   Status saat ini: {selected.get('status', 'pending')}")

    print("\n🔄 Ubah status ke:")
    print("[1] pending")
    print("[2] applied (sudah dilamar)")
    print("[3] not_suitable (tidak cocok)")
    print("[4] rejected (ditolak perusahaan)")
    print("[0] Batal")

    status_choice = input("\nPilihan (0-4): ").strip()

    status_map = {
        "1": "pending",
        "2": "applied",
        "3": "not_suitable",
        "4": "rejected"
    }

    if status_choice == "0":
        return False

    if status_choice not in status_map:
        print("❌ Pilihan tidak valid!")
        return False

    new_status = status_map[status_choice]
    catatan = input("\n📝 Catatan (opsional, Enter untuk skip): ").strip()

    jobs[idx]['status'] = new_status
    if new_status == "applied" and not jobs[idx].get('tanggal_dilamar'):
        jobs[idx]['tanggal_dilamar'] = datetime.now().strftime("%Y-%m-%d")
    if catatan:
        jobs[idx]['catatan'] = catatan

    save_lowongan(jobs)

    log(f"✅ Status berhasil diupdate ke '{new_status}'")
    return True

# ==========================================
# MENU FUNCTIONS
# ==========================================
def tampilkan_header():
    clear_screen()
    print("\n" + "="*60)
    print("🎯 JOB HUNTER AI - MAIN ORCHESTRATOR")
    print("="*60)

def tampilkan_stats():
    """Tampilkan statistik lowongan"""
    jobs = load_lowongan()

    if not jobs:
        print("\n📊 STATUS: Belum ada lowongan di database\n")
        return

    pending = sum(1 for j in jobs if j.get('status', 'pending') == 'pending')
    applied = sum(1 for j in jobs if j.get('status') == 'applied')
    not_suitable = sum(1 for j in jobs if j.get('status') == 'not_suitable')
    rejected = sum(1 for j in jobs if j.get('status') == 'rejected')

    print(f"\n📊 DATABASE LOWONGAN: {len(jobs)} total")
    print(f"   🟡 Pending: {pending}")
    print(f"   🟢 Applied: {applied}")
    print(f"   🔴 Not Suitable: {not_suitable}")
    print(f"   ⚫ Rejected: {rejected}\n")

def menu_lihat_lowongan():
    """Menu lihat detail lowongan"""
    jobs = load_lowongan()

    if not jobs:
        print("\n⚠️ Belum ada lowongan di database.")
        input("\nTekan Enter untuk kembali...")
        return

    tampilkan_header()
    print("\n📋 DAFTAR LOWONGAN:\n")

    print("Filter berdasarkan status:")
    print("[1] Semua")
    print("[2] Pending saja")
    print("[3] Applied saja")
    print("[4] Not Suitable saja")
    print("[5] Rejected saja")

    filter_choice = input("\nPilih filter (1-5): ").strip()

    filtered = jobs
    if filter_choice == "2":
        filtered = [j for j in jobs if j.get('status', 'pending') == 'pending']
    elif filter_choice == "3":
        filtered = [j for j in jobs if j.get('status') == 'applied']
    elif filter_choice == "4":
        filtered = [j for j in jobs if j.get('status') == 'not_suitable']
    elif filter_choice == "5":
        filtered = [j for j in jobs if j.get('status') == 'rejected']

    if not filtered:
        print("\n⚠️ Tidak ada lowongan dengan filter tersebut.")
        input("\nTekan Enter untuk kembali...")
        return

    print(f"\n{'='*60}")
    print(f"Total: {len(filtered)} lowongan\n")

    for i, job in enumerate(filtered, 1):
        status_icon = {
            'pending': '🟡',
            'applied': '🟢',
            'not_suitable': '🔴',
            'rejected': '⚫'
        }.get(job.get('status', 'pending'), '⚪')

        print(f"[{i}] {status_icon} {job['title']}")
        print(f"    🏢 {job.get('company', 'N/A')}")
        print(f"    🎯 Skor: {job.get('skor', 'N/A')}%")
        print(f"    📅 Ditemukan: {job.get('tanggal_ditemukan', 'N/A')}")
        if job.get('tanggal_dilamar'):
            print(f"    ✅ Dilamar: {job['tanggal_dilamar']}")
        if job.get('catatan'):
            print(f"    📝 Catatan: {job['catatan']}")
        print(f"    🔗 {job['url']}")
        print("-" * 60)

    input("\nTekan Enter untuk kembali...")

def menu_update_status():
    """Menu update status lowongan"""
    jobs = load_lowongan()

    if not jobs:
        print("\n⚠️ Belum ada lowongan di database.")
        input("\nTekan Enter untuk kembali...")
        return

    tampilkan_header()
    print("\n✏️ UPDATE STATUS LOWONGAN\n")

    for i, job in enumerate(jobs, 1):
        status_icon = {
            'pending': '🟡',
            'applied': '🟢',
            'not_suitable': '🔴',
            'rejected': '⚫'
        }.get(job.get('status', 'pending'), '⚪')

        print(f"[{i}] {status_icon} {job['title'][:50]} - {job.get('company', 'N/A')}")

    print(f"\n[0] Kembali")

    pilihan = input(f"\nPilih nomor lowongan (0-{len(jobs)}): ").strip()

    if pilihan == "0":
        return

    try:
        idx = int(pilihan) - 1
        if idx < 0 or idx >= len(jobs):
            print("❌ Nomor tidak valid!")
            input("\nTekan Enter untuk kembali...")
            return
    except:
        print("❌ Input tidak valid!")
        input("\nTekan Enter untuk kembali...")
        return

    update_single_job(jobs, idx)
    input("\nTekan Enter untuk kembali...")

def menu_bersihkan_database():
    """Menu archive lowongan lama"""
    jobs = load_lowongan()

    if not jobs:
        print("\n⚠️ Belum ada lowongan di database.")
        input("\nTekan Enter untuk kembali...")
        return

    tampilkan_header()
    print("\n🗑️ ARSIPKAN DATABASE\n")
    print("Lowongan berstatus 'not_suitable' (tidak cocok) dan 'rejected' (ditolak)")
    print("akan DIPINDAHKAN ke file arsip bulan ini, bukan dihapus permanen.")
    print("Lowongan pending & applied tetap di database.\n")

    not_suitable = [j for j in jobs if j.get('status') == 'not_suitable']
    rejected = [j for j in jobs if j.get('status') == 'rejected']

    print(f"Lowongan yang akan di-archive:")
    print(f"   • Not Suitable: {len(not_suitable)}")
    print(f"   • Rejected: {len(rejected)}")
    print(f"   • Total: {len(not_suitable) + len(rejected)}")

    if len(not_suitable) + len(rejected) == 0:
        print("\n✅ Tidak ada lowongan yang perlu di-archive.")
        input("\nTekan Enter untuk kembali...")
        return

    confirm = input("\n⚠️ Pindahkan ke arsip? (y/n): ").strip().lower()

    if confirm != 'y':
        print("❌ Dibatalkan.")
        input("\nTekan Enter untuk kembali...")
        return

    archive_file = f"lowongan_archive_{datetime.now().strftime('%Y-%m')}.json"
    archive_path = os.path.join(os.path.dirname(LOWONGAN_FILE), archive_file)

    archived = not_suitable + rejected

    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(archived, f, indent=2, ensure_ascii=False)

    remaining = [j for j in jobs if j.get('status') not in ['not_suitable', 'rejected']]
    save_lowongan(remaining)

    log(f"✅ {len(archived)} lowongan di-archive ke: {archive_file}")
    log(f"📊 Sisa di database: {len(remaining)} lowongan")
    log(f"♻️  Pulihkan manual dari: {archive_path}")
    input("\nTekan Enter untuk kembali...")

# ==========================================
# MAIN MENU
# ==========================================
def main_menu():
    while True:
        tampilkan_header()
        tampilkan_stats()

        print("MENU:")
        print("[1] 🔍 Fase 1 - Profiler      (buat/ubah profil & baca CV)")
        print("[2] 🕵️  Fase 2 - Scout         (cari lowongan baru dari jobspy + Freehire)")
        print("[3] ✂️  Fase 3 - Tailor        (buat CV + surat lamar untuk lowongan pending)")
        print("[4] 🚀 Auto-pilot             (jalankan Fase 2 lalu Fase 3)")
        print("[5] 📊 Lihat Detail Lowongan  (semua lowongan + skor, alasan, status)")
        print("[6] ✏️  Update Status          (tandai applied / not_suitable / rejected)")
        print("[7] 🗑️  Arsipkan Database      (pindahkan lowongan not_suitable + rejected ke file arsip, tidak dihapus permanen)")
 #       print("[8] 🖥️  Buka UI Desktop")
        print("[0] ❌ Keluar")

        pilihan = input("\n👉 Pilihan Anda: ").strip()

        if pilihan == "0":
            print("\n👋 Terima kasih! Sampai jumpa.")
            break

        elif pilihan == "1":
            # Fase 1 - Profiler (LAZY IMPORT)
            print("\n" + "="*60)
            print("▶️  MENJALANKAN FASE 1: PROFILER")
            print("="*60 + "\n")

            try:
                import job_hunter
                import importlib
                importlib.reload(job_hunter)
            except Exception as e:
                print(f"❌ Error menjalankan Fase 1: {e}")

            input("\nTekan Enter untuk kembali ke menu...")

        elif pilihan == "2":
            # Fase 2 - Scout (LAZY IMPORT)
            if not os.path.exists(PROFIL_FILE):
                print("\n❌ Profil belum dibuat! Jalankan Fase 1 dulu.")
                input("\nTekan Enter untuk kembali...")
                continue

            print("\n" + "="*60)
            print("▶️  MENJALANKAN FASE 2: SCOUT")
            print("="*60 + "\n")

            try:
                import fase2_scout_v2
                import importlib
                importlib.reload(fase2_scout_v2)
                fase2_scout_v2.main()
                log("✅ Fase 2 selesai")
            except Exception as e:
                print(f"❌ Error menjalankan Fase 2: {e}")

            input("\nTekan Enter untuk kembali ke menu...")

        elif pilihan == "3":
            # Fase 3 - Tailor (LAZY IMPORT)
            if not os.path.exists(PROFIL_FILE):
                print("\n❌ Profil belum dibuat! Jalankan Fase 1 dulu.")
                input("\nTekan Enter untuk kembali...")
                continue

            if not os.path.exists(LOWONGAN_FILE):
                print("\n❌ Belum ada lowongan! Jalankan Fase 2 dulu.")
                input("\nTekan Enter untuk kembali...")
                continue

            jobs = load_lowongan()
            pending = [j for j in jobs if j.get('status', 'pending') == 'pending']

            if not pending:
                print(f"\n⚠️ Tidak ada lowongan pending untuk diproses.")
                print(f"   Total di database: {len(jobs)}")
                input("\nTekan Enter untuk kembali...")
                continue

            print(f"\n📊 {len(pending)} lowongan pending akan diproses.")
            confirm = input("Lanjutkan? (y/n): ").strip().lower()

            if confirm != 'y':
                continue

            print("\n" + "="*60)
            print("▶️  MENJALANKAN FASE 3: TAILOR")
            print("="*60 + "\n")

            try:
                import fase3_tailor_v2
                fase3_tailor_v2.main()
                log("✅ Fase 3 selesai")
            except Exception as e:
                print(f"❌ Error menjalankan Fase 3: {e}")

            input("\nTekan Enter untuk kembali ke menu...")

        elif pilihan == "4":
            # Auto-pilot (LAZY IMPORT)
            if not os.path.exists(PROFIL_FILE):
                print("\n❌ Profil belum dibuat! Jalankan Fase 1 dulu.")
                input("\nTekan Enter untuk kembali...")
                continue

            print("\n🚀 AUTO-PILOT MODE")
            print("   Akan menjalankan: Fase 2 → Fase 3")
            confirm = input("\nLanjutkan? (y/n): ").strip().lower()

            if confirm != 'y':
                continue

            # Jalankan Fase 2
            print("\n" + "="*60)
            print("▶️  MENJALANKAN FASE 2: SCOUT")
            print("="*60 + "\n")

            try:
                import fase2_scout_v2
                import importlib
                importlib.reload(fase2_scout_v2)
                fase2_scout_v2.main()
                log("✅ Fase 2 selesai")
            except Exception as e:
                print(f"❌ Error Fase 2: {e}")
                input("\nTekan Enter untuk kembali...")
                continue

            # Cek pending jobs
            jobs = load_lowongan()
            pending = [j for j in jobs if j.get('status', 'pending') == 'pending']

            if not pending:
                log("⚠️ Tidak ada lowongan pending untuk Fase 3")
                input("\nTekan Enter untuk kembali ke menu...")
                continue

            log(f"📊 {len(pending)} lowongan pending, lanjut ke Fase 3...")

            # Jalankan Fase 3
            print("\n" + "="*60)
            print("▶️  MENJALANKAN FASE 3: TAILOR")
            print("="*60 + "\n")

            try:
                import fase3_tailor_v2
                fase3_tailor_v2.main()
                log("✅ Fase 3 selesai")
            except Exception as e:
                print(f"❌ Error Fase 3: {e}")

            print("\n" + "="*60)
            print("🎉 AUTO-PILOT SELESAI!")
            print("="*60)
            input("\nTekan Enter untuk kembali ke menu...")

        elif pilihan == "5":
            menu_lihat_lowongan()

        elif pilihan == "6":
            menu_update_status()

        elif pilihan == "7":
            menu_bersihkan_database()

#        elif pilihan == "8":
#            # UI Desktop
#            print("\n🖥️ Launching UI Desktop...")
#            try:
#                import subprocess
#                import sys
#                subprocess.Popen([sys.executable, "start.py"])
#                log("✅ UI Desktop diluncurkan di window terpisah")
#            except Exception as e:
#                print(f"❌ Error launching UI: {e}")
#            input("\nTekan Enter untuk kembali...")

        else:
            print("\n❌ Pilihan tidak valid!")
            input("\nTekan Enter untuk kembali...")

# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    print("\n🚀 Memulai Job Hunter AI...")

    if not validasi_dependencies():
        print("\n⚠️ Perbaiki file yang hilang dulu!")
        input("\nTekan Enter untuk keluar...")
        exit()

    log("✅ Semua dependencies OK")

    # 🔥 STEP 1: CEK STATUS LOKER DULU (AKAN DI-SKIP KALAU TIDAK ADA LOWONGAN)
    quick_update_prompt()

    # 🔥 STEP 2: TAMPILKAN MENU
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        input("\nTekan Enter untuk keluar...")
