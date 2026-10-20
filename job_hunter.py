import json
import os
from datetime import datetime
from groq import Groq
from google import genai
from docx import Document
import PyPDF2
from dotenv import load_dotenv

# ==========================================
# 1. KONFIGURASI API & MODEL
# ==========================================
# Memuat variabel dari file .env
load_dotenv(dotenv_path="api_key.env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY").strip()

GROQ_MODEL = "qwen/qwen3.8-27b"
GEMINI_MODEL = "gemini-3.5-flash-lite"
TEMPERATURE = 0.7

PROFIL_FILE = "profil_user.json"
PATH_CV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PATH_CV")
CV_PATHS_FILE = os.path.join(PATH_CV_DIR, "cv_paths.json")

groq_client = Groq(api_key=GROQ_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. FUNGSI LOG & AI
# ==========================================
def log(agent, msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {agent}: {msg}")

def ask_ai(prompt, system=""):
    log("🧠 AI", f"Mencoba {GEMINI_MODEL}...")
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{system}\n\n{prompt}"
        )
        log("✅ Gemini", f"Berhasil dengan {GEMINI_MODEL}")
        return response.text
    except Exception as e:
        log("⚠️ Gemini", f"Error: {str(e)[:80]}. Pindah ke {GROQ_MODEL}...")
        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                temperature=TEMPERATURE
            )
            log("✅ Groq", f"Berhasil dengan {GROQ_MODEL}")
            return resp.choices[0].message.content
        except Exception as e2:
            log("❌ Error", f"Kedua AI gagal: {str(e2)[:100]}")
            return None

# ==========================================
# 3. FUNGSI PATH CV MANAGER
# ==========================================
def setup_path_cv_dir():
    """Buat folder PATH_CV jika belum ada"""
    if not os.path.exists(PATH_CV_DIR):
        os.makedirs(PATH_CV_DIR)
        log("📁 Sistem", f"Folder dibuat: {PATH_CV_DIR}")

def simpan_cv_paths(paths_list):
    """Simpan daftar path CV ke file JSON"""
    with open(CV_PATHS_FILE, "w", encoding="utf-8") as f:
        json.dump(paths_list, f, indent=2, ensure_ascii=False)

def baca_cv_paths():
    """Baca daftar path CV yang tersimpan"""
    if os.path.exists(CV_PATHS_FILE):
        with open(CV_PATHS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def tambah_cv_path(new_path):
    """Tambah path CV baru ke daftar (hindari duplikat)"""
    paths = baca_cv_paths()
    if new_path not in paths:
        paths.append(new_path)
        simpan_cv_paths(paths)
        log("💾 Path CV", f"Path baru tersimpan: {new_path}")
    else:
        log("ℹ️ Path CV", "Path sudah ada di daftar.")

def daftar_cv_di_folder():
    """Scan file CV (PDF/DOCX) langsung di folder PATH_CV"""
    if not os.path.isdir(PATH_CV_DIR):
        return []
    return sorted(
        os.path.join(PATH_CV_DIR, f)
        for f in os.listdir(PATH_CV_DIR)
        if f.lower().endswith(('.pdf', '.docx')) and os.path.isfile(os.path.join(PATH_CV_DIR, f))
    )

def minta_taruh_cv():
    """Minta user menaruh CV di folder PATH_CV, Enter untuk cek ulang"""
    print("\n📂 PILIH CV:")
    print(f"   Folder CV: {PATH_CV_DIR}")
    print("   Taruh file CV (.pdf / .docx) di folder tersebut.")
    input("   Tekan Enter untuk cek ulang...")

def pilih_cv():
    """Pilih CV dari isi folder PATH_CV"""
    while True:
        files = daftar_cv_di_folder()

        if not files:
            minta_taruh_cv()
            continue

        print("\n📂 PILIH CV:")
        for i, path in enumerate(files, 1):
            print(f"   [{i}] {os.path.basename(path)}")

        if len(files) > 1:
            print("   [R] Cek ulang folder")
        print("   [0] Keluar")

        pilihan = input(f"\nPilihan Anda (1-{len(files)}/R/0): ").strip()

        if pilihan == "0":
            return None
        if pilihan.lower() == "r":
            continue
        if pilihan.isdigit():
            idx = int(pilihan)
            if 1 <= idx <= len(files):
                path = files[idx - 1]
                simpan_cv_paths([path])
                return path
        log("❌ Error", "Pilihan tidak valid.")

def baca_cv(file_path):
    """Baca isi file CV (PDF/DOCX)"""
    if not os.path.exists(file_path):
        return None
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.docx':
        doc = Document(file_path)
        return '\n'.join([p.text for p in doc.paragraphs])
    elif ext == '.pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return ''.join([page.extract_text() for page in reader.pages])
    return None

# ==========================================
# 4. FUNGSI MEMORI
# ==========================================
def simpan_profil(data):
    data["diperbarui_pada"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(PROFIL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log("💾 Memori", f"Profil tersimpan di '{PROFIL_FILE}'")

def baca_profil():
    if os.path.exists(PROFIL_FILE):
        with open(PROFIL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def tampilkan_profil(data):
    print("\n" + "="*60)
    print("📇 PROFIL YANG TERSIMPAN")
    print("="*60)
    display_data = {k: v for k, v in data.items() if k not in ["diperbarui_pada", "cv_mentah"]}
    print(json.dumps(display_data, indent=2, ensure_ascii=False))
    print("="*60)

# ==========================================
# 5. SESI INTERAKTIF (DENGAN MODE)
# ==========================================
def jalankan_sesi(mode="baru", profil_lama=None):
    cv_text = None
    jawaban_pengalaman = ""
    preferensi_text = ""
    
    # --- MODE: GANTI CV SAJA ---
    if mode == "ganti_cv" and profil_lama:
        print("\n📄 Ganti CV (pengalaman & preferensi tetap)")
        cv_path = pilih_cv()
        if not cv_path:
            return None
        cv_text = baca_cv(cv_path)
        if not cv_text:
            log("❌ Error", "Gagal membaca CV.")
            return None
        
        jawaban_pengalaman = '\n'.join(profil_lama.get("pencapaian_kunci", []))
        preferensi_text = f"""
        Posisi: {profil_lama.get('posisi_target', '')}
        Tipe Kerja: {', '.join(profil_lama.get('tipe_kerja', []))}
        Lokasi: {profil_lama.get('lokasi', '')}
        Gaji: {profil_lama.get('range_gaji', '')}
        """
        log("✅ Sistem", "CV baru dibaca. Pengalaman & preferensi lama dipertahankan.")
    
    # --- MODE: TAMBAH PENGALAMAN ---
    elif mode == "tambah_pengalaman" and profil_lama:
        cv_text = profil_lama.get("cv_mentah", "")
        if not cv_text:
            log("⚠️ Warning", "CV lama tidak ditemukan. Upload CV baru.")
            cv_path = pilih_cv()
            if not cv_path:
                return None
            cv_text = baca_cv(cv_path)
            if not cv_text:
                return None
        
        preferensi_text = f"""
        Posisi: {profil_lama.get('posisi_target', '')}
        Tipe Kerja: {', '.join(profil_lama.get('tipe_kerja', []))}
        Lokasi: {profil_lama.get('lokasi', '')}
        Gaji: {profil_lama.get('range_gaji', '')}
        """
        
        print("\n💼 Tambah Pengalaman Baru")
        print("💬 Ceritakan pengalaman/proyek tambahan. (Ketik 'Bungkus' untuk selesai)")
        print("-" * 60)
        
        jawaban_list = []
        while True:
            user_input = input("\nAnda: ").strip()
            if user_input.lower() == 'bungkus':
                break
            if not user_input:
                continue
            jawaban_list.append(user_input)
            if len(jawaban_list) % 2 == 0:
                respons = ask_ai(
                    "User menceritakan pengalaman kerja. Beri respons 1-2 kalimat suportif, minta lanjut.",
                    "Kamu pendengar aktif dan suportif."
                )
                if respons:
                    print(f"\n🧠 AI: {respons}")
        
        pengalaman_lama = '\n'.join(profil_lama.get("pencapaian_kunci", []))
        pengalaman_baru = '\n'.join([f"- {j}" for j in jawaban_list])
        jawaban_pengalaman = f"{pengalaman_lama}\n{pengalaman_baru}"
        
        log("✅ Sistem", f"Menambahkan {len(jawaban_list)} pengalaman baru.")
    
    # --- MODE: BARU (DARI NOL) ---
    else:
        print("\n📄 Upload CV Anda")
        cv_path = pilih_cv()
        if not cv_path:
            return None
        cv_text = baca_cv(cv_path)
        if not cv_text:
            log("❌ Error", "Gagal membaca CV.")
            return None
        
        log("✅ Sistem", f"CV berhasil dibaca ({len(cv_text)} karakter)")
        
        # --- SESI PENGALAMAN ---
        print("\n💼 Ceritakan Pengalaman Tambahan")
        pertanyaan = ask_ai(
            f"Berdasarkan CV berikut, buat 3 pertanyaan untuk menggali pengalaman.\nCV:\n{cv_text}\n\nKeluarkan HANYA 3 pertanyaan, satu per baris.",
            "Kamu rekruter ramah."
        )
        print("\n" + (pertanyaan if pertanyaan else "1. Pencapaian terbesar?\n2. Proyek membanggakan?\n3. Skill yang ingin ditonjolkan?"))
        print("\n💬 Ngobrol bebas. (Ketik 'Bungkus' untuk selesai)")
        print("-" * 60)
        
        jawaban_list = []
        while True:
            user_input = input("\nAnda: ").strip()
            if user_input.lower() == 'bungkus':
                break
            if not user_input:
                continue
            jawaban_list.append(user_input)
            if len(jawaban_list) % 2 == 0:
                respons = ask_ai(
                    "User menceritakan pengalaman. Beri respons 1-2 kalimat suportif.",
                    "Kamu pendengar aktif."
                )
                if respons:
                    print(f"\n🧠 AI: {respons}")
        
        jawaban_pengalaman = '\n'.join([f"- {j}" for j in jawaban_list])
        
        # --- SESI PREFERENSI ---
        print("\n" + "-" * 60)
        print("\n🎯 Preferensi Kerja (posisi, tipe/lokasi, gaji)")
        print("   (Ketik 'Bungkus' untuk selesai)")
        print("-" * 60)
        
        preferensi_list = []
        while True:
            user_input = input("\nAnda: ").strip()
            if user_input.lower() == 'bungkus':
                break
            if not user_input:
                continue
            preferensi_list.append(user_input)
        
        preferensi_text = '\n'.join(preferensi_list)
    
    # --- GABUNGKAN MENJADI JSON (DENGAN AUTO-TRANSLATE) ---
    log("🧠 Profiler", "Menggabungkan & menerjemahkan ke bahasa Inggris profesional...")
    
    final_prompt = f"""
Gabungkan informasi berikut menjadi JSON rapi dalam BAHASA INGGRIS PROFESIONAL:

CV MENTAH (bahasa asli):
{cv_text}

PENGALAMAN TAMBAHAN (bahasa Indonesia):
{jawaban_pengalaman}

PREFERENSI:
{preferensi_text}

ATURAN PENTING:
1. TERJEMAHKAN semua pencapaian dan ringkasan ke bahasa Inggris profesional
2. Gunakan action verbs (Led, Developed, Optimized, Implemented, dll)
3. Pertahankan angka, metrik, dan teknologi secara akurat
4. Optimalkan kata kunci untuk ATS (Applicant Tracking System)

Format JSON:
{{
  "nama_lengkap": "string",
  "kontak": {{"email": "string", "telepon": "string", "linkedin": "string"}},
  "posisi_target": "string",
  "tipe_kerja": ["list"],
  "lokasi": "string",
  "range_gaji": "string",
  "total_tahun_pengalaman": "integer",
  "hard_skills": ["list"],
  "soft_skills": ["list"],
  "pencapaian_kunci": ["list dalam bahasa Inggris profesional"],
  "ringkasan_profesi": "string dalam bahasa Inggris (2-3 kalimat)",
  "cv_mentah": "string (CV asli dalam bahasa aslinya, untuk referensi)"
}}

HANYA keluarkan JSON murni.
"""
    hasil = ask_ai(final_prompt, "Kamu ahli HR internasional. Keluarkan HANYA JSON.")
    
    if hasil:
        if hasil.startswith("```json"):
            hasil = hasil[7:-4]
        elif hasil.startswith("```"):
            hasil = hasil[3:-4]
        try:
            return json.loads(hasil)
        except:
            log("❌ Error", "JSON tidak valid.")
            print(hasil)
    return None

# ==========================================
# 6. ALUR UTAMA APLIKASI
# ==========================================
setup_path_cv_dir()

print("\n" + "="*60)
print("🎯 JOB HUNTER AI - FASE 1: PROFILER INTERAKTIF")
print(f"🤖 Model: {GEMINI_MODEL} (Primary) → {GROQ_MODEL} (Backup)")
print("="*60)

profil_lama = baca_profil()
data_final = None

if profil_lama:
    tampilkan_profil(profil_lama)
    print(f"\n📅 Terakhir diperbarui: {profil_lama.get('diperbarui_pada', 'tidak diketahui')}")
    
    print("\nPilih:")
    print("[1] Pakai profil lama (load profil lama)")
    print("[2] Buat profil baru (RESET SEMUA)")
    print("[3] Tambah pengalaman (pengalaman lama tetap)")
    print("[4] Ganti CV saja (pengalaman & preferensi tetap)")
    
    pilihan = input("\nPilihan Anda (1/2/3/4): ").strip()
    
    if pilihan == "1":
        log("💾 Memori", "Profil lama dimuat.")
        data_final = profil_lama
    elif pilihan == "2":
        log("🔄 Reset", "Membuat profil baru dari nol...")
        data_final = jalankan_sesi(mode="baru")
        if data_final:
            simpan_profil(data_final)
            tampilkan_profil(data_final)
    elif pilihan == "3":
        log("➕ Tambah", "Menambah pengalaman baru...")
        data_final = jalankan_sesi(mode="tambah_pengalaman", profil_lama=profil_lama)
        if data_final:
            simpan_profil(data_final)
            tampilkan_profil(data_final)
    elif pilihan == "4":
        log("📄 Ganti CV", "Mengganti CV saja...")
        data_final = jalankan_sesi(mode="ganti_cv", profil_lama=profil_lama)
        if data_final:
            simpan_profil(data_final)
            tampilkan_profil(data_final)
    else:
        log("❌ Error", "Pilihan tidak valid.")
else:
    log("💾 Memori", "Belum ada profil. Mulai sesi pertama...")
    data_final = jalankan_sesi(mode="baru")
    if data_final:
        simpan_profil(data_final)
        tampilkan_profil(data_final)

if data_final:
    log("🎉 Sukses", "Profil siap! Semua pencapaian sudah dalam bahasa Inggris profesional.")
    log("🚀 Next", "Fase 2 (Scout) akan membaca 'profil_user.json' untuk mencari lowongan.")