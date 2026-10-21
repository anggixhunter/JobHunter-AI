import json
import os
import re
import requests

# ==========================================
# CONFIG
# ==========================================
PROFIL_FILE = "profil_user.json"
FREEHIRE_URL = "https://freehire.me/api/v1/jobs/search"
JRESULT = 5  # jumlah hasil

LOKASI_KE_KOTA = {"jakarta": "Jakarta", "bandung": "Bandung", "tangerang": "Tangerang"}
LOKASI_KE_NEGARA = {"indonesia": "ID", "singapore": "SG", "malaysia": "MY", "thailand": "TH", "vietnam": "VN", "qatar": "QA"}
TIPKE_MODE = {"remote": "remote", "hybrid": "hybrid", "onsite": "onsite", "on-site": "onsite", "wfo": "onsite"}

# ==========================================
# FUNGSI
# ==========================================
def cari_freehire(profil, limit=JRESULT):
    posisi = profil.get('posisi_target', 'Software Engineer')
    lokasi = profil.get('lokasi', 'Indonesia').strip().lower()

    base = {"q": posisi, "limit": limit, "sort": "posted_at", "order": "desc"}
    extras = {}

    # Skills
    skills = ",".join(profil.get('hard_skills', [])[:50])
    if skills:
        extras['skills'] = skills

    # Work mode
    modes = []
    for tipe in profil.get('tipe_kerja', []):
        mode = TIPKE_MODE.get(str(tipe).strip().lower())
        if mode and mode not in modes:
            modes.append(mode)
    if modes:
        extras['work_mode'] = ",".join(modes)

    # Lokasi
    kota = next((v for k, v in LOKASI_KE_KOTA.items() if k in lokasi), None)
    if kota:
        extras['cities'] = kota
    else:
        kode = next((v for k, v in LOKASI_KE_NEGARA.items() if k in lokasi), None)
        if kode:
            extras['countries'] = kode

    # Fallback ladder
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
            payload = r.json()
            data = payload.get("data", [])
        except Exception as e:
            print(f"Error: {str(e)[:80]}")
            return []
        if data:
            if extra is not attempts[0]:
                print(f"Filter dilonggarkan: {list(extra.keys()) or 'tanpa filter'}")
            break

    if not data:
        print("0 hasil")
        return []

    results = []
    for j in data:
        # Bersihkan HTML
        deskripsi = re.sub(r'<[^>]+>', ' ', j.get("description") or "")
        deskripsi = re.sub(r'\s+', ' ', deskripsi).strip()
        results.append({
            "title": j.get("title", "No Title"),
            "company": j.get("company", "Unknown"),
            "snippet": deskripsi[:400],
            "url": j.get("url", ""),
            "location": j.get("location", "N/A"),
            "work_mode": j.get("work_mode", "N/A"),
            "posted_at": j.get("posted_at", "N/A")
        })
    return results

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CEK FREEHIRE MANUAL")
    print("="*60)

    if not os.path.exists(PROFIL_FILE):
        print(f"File '{PROFIL_FILE}' tidak ditemukan!")
        exit()

    with open(PROFIL_FILE, "r", encoding="utf-8") as f:
        profil = json.load(f)

    print(f"\nProfil: {profil.get('nama_lengkap')}")
    print(f"Target: {profil.get('posisi_target')}")
    print(f"Lokasi: {profil.get('lokasi')}")
    print(f"Skills: {', '.join(profil.get('hard_skills', [])[:50])}")
    print(f"Tipe: {', '.join(profil.get('tipe_kerja', []))}")

    print("\nMencari di Freehire...")
    jobs = cari_freehire(profil)

    if not jobs:
        print("\nTidak ada hasil")
        exit()

    print(f"\nDitemukan {len(jobs)} lowongan:\n")
    print("="*60)

    for i, job in enumerate(jobs, 1):
        print(f"\n[{i}] {job['title']}")
        print(f"    {job['company']}")
        print(f"    {job['location']} | {job['work_mode']}")
        print(f"    {job['posted_at']}")
        print(f"    {job['url']}")
        print(f"    {job['snippet'][:150]}...")
        print("-" * 60)

    print("\nSelesai!")
