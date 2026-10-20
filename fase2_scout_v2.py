import json
import os
import re
import time
from datetime import datetime
from groq import Groq
from google import genai
from dotenv import load_dotenv
from jobspy import scrape_jobs
import requests

# Memuat variabel dari file .env
load_dotenv(dotenv_path="api_key.env")

# ==========================================
# 1. KONFIGURASI
# ==========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY").strip()

GROQ_MODEL = "openai/gpt-oss-120b"
GEMINI_MODEL = "gemini-3.5-flash-lite"
TEMPERATURE = 0.3

PROFIL_FILE = "profil_user.json"
LOWONGAN_FILE = "lowongan_cocok.json"

JRESULT = 5
JRESULT2 = 5
SITES = ["indeed", "linkedin"]
COUNTRY = "indonesia"
NEGARA = "Indonesia"
HOURS_OLD = 24 * 30
JEDA_DETIK = 5
PROXY = os.getenv("PROXY") or None

FREEHIRE_URL = "https://freehire.me/api/v1/jobs/search"
LOKASI_KE_KOTA = {"jakarta": "Jakarta", "bandung": "Bandung", "tangerang": "Tangerang"}
LOKASI_KE_NEGARA = {"indonesia": "ID", "singapore": "SG", "malaysia": "MY", "thailand": "TH", "vietnam": "VN", "qatar": "QA"}
TIPKE_MODE = {"remote": "remote", "hybrid": "hybrid", "onsite": "onsite", "on-site": "onsite", "wfo": "onsite"}

groq_client = Groq(api_key=GROQ_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. FUNGSI LOG & AI
# ==========================================
def log(agent, msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {agent}: {msg}")


def ask_ai(prompt, system=""):
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{system}\n\n{prompt}"
        )
        return response.text
    except Exception as e:
        log("⚠️ Gemini", f"Gagal ({str(e)[:80]}). Pindah ke Groq...")

    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            temperature=TEMPERATURE
        )
        return resp.choices[0].message.content
    except Exception as e:
        log("❌ Error AI", f"Kedua AI gagal: {str(e)[:60]}")
        return None


# ==========================================
# 3. TRACKING SYSTEM
# ==========================================
def load_existing_jobs():
    if os.path.exists(LOWONGAN_FILE):
        try:
            with open(LOWONGAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def is_duplicate_url(url, existing_jobs):
    return any(job['url'] == url for job in existing_jobs)


def merge_jobs(existing_jobs, new_jobs):
    merged = existing_jobs.copy()
    added_count = 0

    for new_job in new_jobs:
        if not is_duplicate_url(new_job['url'], existing_jobs):
            merged.append(new_job)
            added_count += 1
            log("✅ Baru", f"Lowongan baru: {new_job['title'][:50]}...")
        else:
            log("⏭️ Skip", f"Duplikat: {new_job['title'][:50]}...")

    return merged, added_count


# ==========================================
# 4. BERSIH-BERSIH DATA JOBSPY
# ==========================================
def bersih(nilai, default=""):
    if nilai is None:
        return default
    teks = str(nilai).strip()
    return default if teks.lower() in ("nan", "none", "") else teks


def ke_snippet(deskripsi, batas=600):
    teks = re.sub(r'<[^>]+>', ' ', bersih(deskripsi))
    teks = re.sub(r'[#*_`>\[\]]+', ' ', teks)
    return re.sub(r'\s+', ' ', teks).strip()[:batas]


def daftar_kata_kunci(profil):
    mentah = re.split(r'[/|,]', profil.get('posisi_target', 'Software Engineer'))
    return [k.strip() for k in mentah if k.strip()][:3]


def lokasi_pencarian(profil):
    kota = bersih(profil.get('lokasi'), NEGARA).split(',')[0].strip()
    if not kota or NEGARA.lower() in kota.lower():
        return NEGARA
    return f"{kota}, {NEGARA}"


# ==========================================
# 5. SCOUT - PENCARIAN (jobspy)
# ==========================================
def cari_jobspy(profil):
    lokasi = lokasi_pencarian(profil)
    kata_kunci = daftar_kata_kunci(profil)
    per_kata = max(1, JRESULT // len(kata_kunci))
    hasil = {}
    linkedin_mati = False

    for i, kata in enumerate(kata_kunci):
        if len(hasil) >= JRESULT:
            break
        if i > 0:
            time.sleep(JEDA_DETIK)

        sisa = JRESULT - len(hasil)
        situs = [s for s in SITES if not (s == "linkedin" and linkedin_mati)]
        if not situs:
            log("⚠️ jobspy", "Semua situs diblokir")
            break

        log("🕵️ Scout", f"jobspy: '{kata}' @ {lokasi} (maks {min(per_kata, sisa)})")
        try:
            df = scrape_jobs(
                site_name=situs,
                search_term=kata,
                location=lokasi,
                results_wanted=min(per_kata, sisa),
                country_indeed=COUNTRY,
                hours_old=HOURS_OLD,
                linkedin_fetch_description=True,
                verbose=0,
                proxies=[PROXY] if PROXY else None,
            )
        except Exception as e:
            pesan = str(e)
            if "429" in pesan and "linkedin" in pesan.lower():
                linkedin_mati = True
                log("⚠️ LinkedIn", "Diblokir 429. Lanjut Indeed saja untuk sesi ini.")
            else:
                log("⚠️ jobspy", f"Gagal '{kata}': {pesan[:80]}")
            continue

        for _, baris in df.iterrows():
            url = bersih(baris.get('job_url_direct')) or bersih(baris.get('job_url'))
            if not url or url in hasil:
                continue
            hasil[url] = {
                "title": bersih(baris.get('title'), "No Title"),
                "company": bersih(baris.get('company'), "Unknown"),
                "snippet": ke_snippet(baris.get('description')),
                "url": url,
                "sumber": bersih(baris.get('site')),
                "lokasi": bersih(baris.get('location')),
                "tanggal_post": bersih(baris.get('date_posted')),
            }

    log("✅ jobspy", f"{len(hasil)} lowongan unik (target {JRESULT}, {len(kata_kunci)} kata kunci)")
    return list(hasil.values())


# ==========================================
# 5b. FREEHIRE - SUMBER GRATIS (API KEYLESS)
# ==========================================
def cari_freehire(profil, limit=JRESULT2):
    posisi = profil.get('posisi_target', 'Software Engineer')
    lokasi = profil.get('lokasi', 'Indonesia').strip().lower()

    base = {"q": posisi, "limit": limit, "sort": "posted_at", "order": "desc"}
    extras = {}

    skills = ",".join(profil.get('hard_skills', [])[:3])
    if skills:
        extras['skills'] = skills

    modes = []
    for tipe in profil.get('tipe_kerja', []):
        mode = TIPKE_MODE.get(str(tipe).strip().lower())
        if mode and mode not in modes:
            modes.append(mode)
    if modes:
        extras['work_mode'] = ",".join(modes)

    kota = next((v for k, v in LOKASI_KE_KOTA.items() if k in lokasi), None)
    if kota:
        extras['cities'] = kota
    else:
        kode = next((v for k, v in LOKASI_KE_NEGARA.items() if k in lokasi), None)
        if kode:
            extras['countries'] = kode

    attempts = [
        extras,
        {k: v for k, v in extras.items() if k != 'skills'},
        {k: v for k, v in extras.items() if k not in ('skills', 'work_mode')},
        {},
    ]

    data = []
    for extra in attempts:
        try:
            r = requests.get(FREEHIRE_URL, params={**base, **extra}, timeout=15)
            r.raise_for_status()
            data = r.json().get("data", [])
        except Exception as e:
            log("⚠️ Freehire", f"Gagal: {str(e)[:80]}")
            return []
        if data:
            if extra is not attempts[0]:
                log("🛟 Freehire", f"Hasil kosong dengan filter penuh, longgarkan: {list(extra.keys()) or 'tanpa filter'}")
            break

    if not data:
        log("⚠️ Freehire", "0 hasil walau filter dilepas")
        return []

    results = []
    for j in data:
        deskripsi = re.sub(r'<[^>]+>', ' ', j.get("description") or "")
        deskripsi = re.sub(r'\s+', ' ', deskripsi).strip()
        results.append({
            "title": j.get("title", "No Title"),
            "company": j.get("company", "Unknown"),
            "snippet": deskripsi[:600],
            "url": j.get("url", ""),
            "sumber": "freehire",
            "lokasi": "",
            "tanggal_post": "",
        })
    log("✅ Freehire", f"{len(results)} hasil (langsung dari ATS perusahaan)")
    return results


# ==========================================
# 5c. GABUNGKAN SUMBER
# ==========================================
def gabung_lowongan(jobs_jobspy, jobs_freehire):
    hasil = {}
    for job in jobs_jobspy + jobs_freehire:
        url = job.get('url', '')
        if url and url not in hasil:
            hasil[url] = job
    return list(hasil.values())


# ==========================================
# 6. MATCHER - PENILAI
# ==========================================
def nilai_kecocokan(job, profil):
    prompt = f"""
Kamu adalah ahli rekrutmen. Nilai kecocokan lowongan ini dengan profil kandidat.

PROFIL KANDIDAT:
- Posisi Target: {profil.get('posisi_target')}
- Hard Skills: {', '.join(profil.get('hard_skills', []))}
- Tipe Kerja: {', '.join(profil.get('tipe_kerja', []))}
- Lokasi: {profil.get('lokasi')}

LOWONGAN:
- Judul: {job['title']}
- Perusahaan: {job.get('company', '-')}
- Deskripsi: {job['snippet']}

Format output:
Skor: [0-100]
Alasan: [1 kalimat]
"""
    hasil = ask_ai(prompt, "Kamu matcher objektif. Jawab singkat.")
    if hasil:
        skor = "N/A"
        alasan = "Tidak ada alasan."
        for line in hasil.strip().split('\n'):
            if line.lower().startswith("skor:"):
                skor = line.replace("Skor:", "").strip()
            elif line.lower().startswith("alasan:"):
                alasan = line.replace("Alasan:", "").strip()
        return skor, alasan
    return "N/A", "Gagal menilai."


# ==========================================
# 7. MAIN
# ==========================================
def main():
    print("\n" + "="*60)
    print("🎯 JOB HUNTER AI - FASE 2: SCOUT (jobspy)")
    print(f"📊 Sumber: jobspy ({', '.join(SITES)}) + Freehire")
    print("="*60)

    if not os.path.exists(PROFIL_FILE):
        log("❌ Error", f"'{PROFIL_FILE}' tidak ditemukan!")
        return

    with open(PROFIL_FILE, "r", encoding="utf-8") as f:
        profil = json.load(f)

    log("💾 Memori", f"{profil.get('nama_lengkap')} - {profil.get('posisi_target')}")

    existing_jobs = load_existing_jobs()
    if existing_jobs:
        pending = sum(1 for j in existing_jobs if j.get('status', 'pending') == 'pending')
        applied = sum(1 for j in existing_jobs if j.get('status') == 'applied')
        rejected = sum(1 for j in existing_jobs if j.get('status') in ['not_suitable', 'rejected'])
        log("📂 Database", f"{len(existing_jobs)} lowongan sebelumnya")
        log("📊 Status", f"Pending: {pending} | Applied: {applied} | Rejected: {rejected}")
    else:
        log("📂 Database", "Pencarian pertama")

    jobs_jobspy = cari_jobspy(profil)
    jobs_freehire = cari_freehire(profil)
    jobs = gabung_lowongan(jobs_jobspy, jobs_freehire)
    log("🔎 Gabungan", f"{len(jobs)} unik (jobspy {len(jobs_jobspy)} + freehire {len(jobs_freehire)})")

    if not jobs:
        log("⚠️ Scout", "Tidak ada hasil")
        return

    print("\n" + "="*60)
    print("📊 HASIL (Skor >= 60%)")
    print("="*60)

    lowongan_cocok = []
    for i, job in enumerate(jobs, 1):
        log("⚖️ Matcher", f"#{i}: {job['title'][:40]}...")
        skor_str, alasan = nilai_kecocokan(job, profil)

        try:
            skor = int(''.join(filter(str.isdigit, str(skor_str))))
        except Exception:
            skor = 0

        if skor >= 60:
            print(f"\n[{len(lowongan_cocok)+1}] ✅ {job['title']}")
            print(f"    🏢 {job['company']}")
            print(f"    🔗 {job['url']}")
            print(f"    🎯 Skor: {skor}%")
            print(f"    💡 {alasan}")
            print("-" * 60)

            lowongan_cocok.append({
                **job,
                "skor": skor,
                "alasan": alasan,
                "status": "pending",
                "tanggal_ditemukan": datetime.now().strftime("%Y-%m-%d"),
                "tanggal_dilamar": None,
                "catatan": ""
            })

    if lowongan_cocok:
        all_jobs, added = merge_jobs(existing_jobs, lowongan_cocok)

        with open(LOWONGAN_FILE, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)

        print("\n" + "="*60)
        print("💾 DATABASE UPDATE:")
        print(f"   • Ditemukan: {len(lowongan_cocok)}")
        print(f"   • Ditambahkan: {added}")
        print(f"   • Duplikat: {len(lowongan_cocok) - added}")
        print(f"   • Total: {len(all_jobs)}")
        print("="*60)
        log("🎉 Sukses", "Fase 2 selesai!")
    else:
        log("⚠️ Sistem", "Tidak ada lowongan >= 60%")


if __name__ == "__main__":
    main()
