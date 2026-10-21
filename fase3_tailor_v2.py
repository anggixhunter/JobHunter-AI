import json
import os
import re
from datetime import datetime
from google import genai
from groq import Groq
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pypdf
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Import untuk convert DOCX ke PDF
try:
    from docx2pdf import convert
    PDF_ENABLED = True
except ImportError:
    PDF_ENABLED = False
    print("Warning: docx2pdf tidak terinstall. CV akan disimpan dalam format .docx saja.")


# ==========================================
# 1. KONFIGURASI API & MODEL & PATH ABSOLUT
# ==========================================
# Memuat variabel dari file .env
load_dotenv(dotenv_path="api_key.env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY").strip()

GEMINI_MODEL = "gemini-3.5-flash-lite"
GROQ_MODEL = "openai/gpt-oss-120b"
TEMPERATURE = 0.3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROFIL_FILE = os.path.join(BASE_DIR, "profil_user.json")
LOWONGAN_FILE = os.path.join(BASE_DIR, "lowongan_cocok.json")
CV_PATHS_FILE = os.path.join(BASE_DIR, "PATH_CV", "cv_paths.json")
BASE_LAMAR_DIR = os.path.join(BASE_DIR, "PATH_CV", "LAMAR")

DEBUG_CV = False
FONT_NAME = "Calibri"

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def log(agent, msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {agent}: {msg}")


def ask_ai(prompt, system=""):
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{system}\n\n{prompt}"
        )
        if response and response.text:
            return response.text
    except Exception as e:
        log("Gemini", f"Gagal ({str(e)[:80]}). Pindah ke Groq...")

    if groq_client:
        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                temperature=TEMPERATURE
            )
            return resp.choices[0].message.content
        except Exception as e2:
            log("Error AI", f"Kedua AI gagal: {str(e2)[:60]}")
    return None


def baca_pdf_asli(pdf_path):
    if not os.path.exists(pdf_path):
        return None
    try:
        reader = pypdf.PdfReader(pdf_path)
        teks_pdf = ""
        for page in reader.pages:
            teks_pdf += (page.extract_text() or "") + "\n"
        return teks_pdf.strip()
    except Exception as e:
        log("PDF", f"Gagal membaca PDF: {e}")
        return None


def ambil_deskripsi_loker(url):
    log("Scraper", "Mengambil detail dari URL...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
            return ' '.join(soup.get_text(separator=' ').split())[:4000]
    except Exception:
        pass
    return None


# ==========================================
# 2. TRACKING SYSTEM - UPDATE STATUS
# ==========================================
def update_job_status(job_url, new_status, catatan=""):
    """Update status lowongan setelah diproses"""
    if not os.path.exists(LOWONGAN_FILE):
        return

    with open(LOWONGAN_FILE, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    for job in jobs:
        if job['url'] == job_url:
            job['status'] = new_status
            if new_status == "applied":
                job['tanggal_dilamar'] = datetime.now().strftime("%Y-%m-%d")
            if catatan:
                job['catatan'] = catatan
            log("Status", f"Updated ke '{new_status}': {job['title'][:40]}")
            break

    with open(LOWONGAN_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


# ==========================================
# 3. AI GENERATOR (FIXED - PAKAI PENCAPAIAN)
# ==========================================
def _ekstrak_json(teks):
    awal = teks.find("{")
    akhir = teks.rfind("}")
    if awal == -1 or akhir == -1:
        raise ValueError("JSON tidak ditemukan")
    return json.loads(teks[awal:akhir + 1], strict=False)


def generate_dokumen_lamaran(profil, cv_asli_teks, job_title, company, job_description):
    log("Tailor", f"Menyesuaikan untuk {job_title} di {company}...")

    # FIX: Gabungkan CV + pencapaian dari profil
    pencapaian = profil.get('pencapaian_kunci', [])
    ringkasan_profesi = profil.get('ringkasan_profesi', '')
    pencapaian_text = "\n".join([f"• {p}" for p in pencapaian]) if pencapaian else ""

    prompt = f"""
Kamu adalah Expert Career Coach & ATS Resume Writer profesional.

TEKS CV ASLI (dari PDF):
{cv_asli_teks[:2500]}

RINGKASAN PROFESI:
{ringkasan_profesi}

PENCAPAIAN KUNCI (dari interview):
{pencapaian_text}

TARGET LOWONGAN:
- Posisi: {job_title}
- Perusahaan: {company}
- Deskripsi: {job_description}

ATURAN:
1. Buat "ringkasan_tailored" (2-3 kalimat, Bahasa Inggris, keyword dari lowongan).
   GUNAKAN pencapaian kunci untuk summary yang kuat.
2. Buat "cover_letter" formal profesional (Bahasa Inggris).
   MANFAATKAN pencapaian kunci untuk show value.
3. Buat "email_body" singkat.

Output HANYA JSON:
{{
  "ringkasan_tailored": "string",
  "cover_letter": "string",
  "email_body": "string"
}}
"""

    hasil = ask_ai(prompt, "Output HANYA JSON murni valid.")
    if hasil:
        try:
            return _ekstrak_json(hasil)
        except Exception as e:
            log("Error", f"Gagal parse JSON: {e}")
    return None


# ==========================================
# 4. PARSER CV
# ==========================================
PUA_RE = re.compile(r"[\ue000-\uf8ff]")
BULLET_CHARS = "\u2022\u25aa\u25cf\u25e6\u25a0\u2023\u2043\u2219\u00b7"
DATE_RE = re.compile(
    r"^(?:[A-Za-z]{3,9}\s+)?\d{4}\s*[–—-]\s*(?:(?:[A-Za-z]{3,9}\s+)?\d{4}|present|now|sekarang)$",
    re.I,
)
SECTION_MAP = {
    "professional summary": "summary", "summary": "summary", "profile": "summary",
    "key skills": "skills", "skills": "skills", "technical skills": "skills",
    "domain expertise": "domain",
    "professional experience": "experience", "work experience": "experience",
    "experience": "experience",
    "education": "education",
}


def _normalisasi_baris(teks):
    teks = teks.replace("\r", "")
    for ch in BULLET_CHARS:
        teks = teks.replace(ch, "\n• ")
    teks = PUA_RE.sub("\n• ", teks)
    teks = re.sub(r"(?<=[a-z]\.)(?=PT\.)", "\n", teks)
    teks = re.sub(r"(?<=\.)[ \t]{2,}(?=[A-Z])", "\n• ", teks)
    return [ln.rstrip() for ln in teks.split("\n") if ln.strip()]


def _dedup_csv(teks):
    seen, out = set(), []
    for part in [p.strip() for p in teks.split(",") if p.strip()]:
        if part.lower() not in seen:
            seen.add(part.lower())
            out.append(part)
    return ", ".join(out)


def _is_header_line(it):
    t = it["text"]
    return (not it["bullet"] and len(t) <= 80 and not t.endswith(".")
            and not t.lower().startswith("programming/tools") and not DATE_RE.match(t))


def _parse_experience(exp):
    date_idx = [i for i, it in enumerate(exp) if not it["bullet"] and DATE_RE.match(it["text"])]
    heads = []
    prev = -1
    for d in date_idx:
        hdr = []
        j = d - 1
        while j > prev and len(hdr) < 2 and _is_header_line(exp[j]):
            hdr.insert(0, exp[j]["text"])
            j -= 1
        heads.append((d, hdr))
        prev = d

    jobs = []
    for n, (d, hdr) in enumerate(heads):
        if n + 1 < len(heads):
            nd, nhdr = heads[n + 1]
            end = nd - len(nhdr)
        else:
            end = len(exp)
        tools, bullets, in_tools = "", [], False
        for it in exp[d + 1:end]:
            t = it["text"]
            if not it["bullet"] and t.lower().startswith("programming/tools"):
                tools = t.split(":", 1)[1].strip() if ":" in t else ""
                in_tools = True
            elif it["bullet"]:
                bullets.append(t)
                in_tools = False
            elif in_tools:
                tools += " " + t
            elif bullets:
                bullets[-1] += " " + t
            else:
                bullets.append(t)
        jobs.append({
            "header": hdr,
            "dates": exp[d]["text"],
            "tools": _dedup_csv(tools),
            "bullets": bullets,
        })
    return jobs


def parse_cv(teks):
    lines = _normalisasi_baris(teks)
    has_markers = any(ln.strip().startswith("•") for ln in lines)

    items, section = [], None
    for raw in lines:
        s = raw.strip()
        is_b = s.startswith("•")
        if not is_b:
            key = s.lower().rstrip(":").strip()
            if key in SECTION_MAP:
                section = SECTION_MAP[key]
                continue
            if not has_markers and raw[:1] in (" ", "\t"):
                is_b = True
        if section is None:
            continue
        text = s.lstrip("•").strip()
        if text:
            items.append({"sec": section, "bullet": is_b, "text": text})

    def kelompok(sec):
        hasil = []
        for it in (x for x in items if x["sec"] == sec):
            if re.match(r"^technical skills", it["text"], re.I) and not it["bullet"]:
                continue
            if it["bullet"] or not hasil:
                hasil.append(it["text"])
            else:
                hasil[-1] += " " + it["text"]
        return hasil

    return {
        "summary": " ".join(x["text"] for x in items if x["sec"] == "summary"),
        "skills": kelompok("skills"),
        "domain": kelompok("domain"),
        "experience": _parse_experience([x for x in items if x["sec"] == "experience"]),
        "education": [x["text"] for x in items if x["sec"] == "education"],
    }


# ==========================================
# 5. RENDER DOCX
# ==========================================
def _font(run, size=None, bold=None, italic=None):
    run.font.name = FONT_NAME
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT_NAME)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def _setup_doc(doc):
    normal = doc.styles["Normal"]
    normal.font.name = FONT_NAME
    normal.font.size = Pt(10.5)
    normal.element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT_NAME)
    lb = doc.styles["List Bullet"]
    lb.font.name = FONT_NAME
    lb.font.size = Pt(10.5)
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Inches(0.8)
        s.left_margin = s.right_margin = Inches(0.8)


def _heading(doc, teks):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "000000")):
        bottom.set(qn(k), v)
    bdr.append(bottom)
    pPr.append(bdr)
    _font(p.add_run(teks.upper()), size=11.5, bold=True)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    return p


def _bullet(doc, teks, label_bold=True):
    p = doc.add_paragraph(style="List Bullet")
    m = re.match(r"^([^:]{2,60}):\s*(.+)$", teks) if label_bold else None
    if m:
        _font(p.add_run(m.group(1) + ": "), bold=True)
        _font(p.add_run(m.group(2)))
    else:
        _font(p.add_run(teks))
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.1
    return p


def _judul_pekerjaan(header):
    if len(header) >= 2:
        return f"{header[1]} | {header[0]}"
    if len(header) == 1:
        h = header[0]
        if " – " in h:
            perusahaan, jabatan = h.split(" – ", 1)
            return f"{jabatan} | {perusahaan}"
        return h
    return ""


def render_cv(doc, profil, nama_user, summary, parsed):
    _setup_doc(doc)

    p = doc.add_paragraph()
    _font(p.add_run(nama_user), size=18, bold=True)
    p.paragraph_format.space_after = Pt(2)

    kontak = profil.get('kontak', {}) or {}
    bagian = [kontak.get('email') or '', kontak.get('telepon') or '']
    bagian = [b for b in bagian if b]
    ln = (kontak.get('linkedin') or '').strip()
    if ln and ln != '-':
        bagian.append(ln)
    p = doc.add_paragraph()
    _font(p.add_run(" | ".join(bagian)))
    p.paragraph_format.space_after = Pt(4)

    _heading(doc, "Professional Summary")
    p = doc.add_paragraph()
    _font(p.add_run(summary or parsed["summary"]))
    p.paragraph_format.space_after = Pt(4)

    if parsed["skills"]:
        _heading(doc, "Skills")
        for s in parsed["skills"]:
            _bullet(doc, s)

    if parsed["domain"]:
        _heading(doc, "Domain Expertise")
        for s in parsed["domain"]:
            _bullet(doc, s, label_bold=False)

    if parsed["experience"]:
        _heading(doc, "Professional Experience")
        for job in parsed["experience"]:
            p = doc.add_paragraph()
            _font(p.add_run(_judul_pekerjaan(job["header"])), bold=True)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True

            p = doc.add_paragraph()
            _font(p.add_run(job["dates"]), italic=True)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_with_next = True

            if job["tools"]:
                p = doc.add_paragraph()
                _font(p.add_run("Tools: "), bold=True)
                _font(p.add_run(job["tools"]))
                p.paragraph_format.space_after = Pt(2)

            for b in job["bullets"]:
                _bullet(doc, b, label_bold=False)

    if parsed["education"]:
        _heading(doc, "Education")
        for i, e in enumerate(parsed["education"]):
            p = doc.add_paragraph()
            _font(p.add_run(e), bold=(i == 0))
            p.paragraph_format.space_after = Pt(1)


# ==========================================
# 6. EXPORTER (WITH PATH LENGTH PROTECTION)
# ==========================================
def _safe_filename(text, max_len=50):
    """Bersihkan karakter ilegal & potong jika terlalu panjang"""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text)
    cleaned = re.sub(r'\s+', "_", cleaned.strip())
    return cleaned[:max_len].strip("_")

def simpan_hasil_lamaran(job, data_dokumen, cv_asli_teks, profil):
    company = job.get('company', 'Perusahaan')
    job_title = job['title']
    url = job['url']

    tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")

    # FIX: Limit panjang nama untuk cegah error Windows Path Limit (260 char)
    safe_company = _safe_filename(company, max_len=50)
    safe_title = _safe_filename(job_title, max_len=50)

    folder_name = f"{safe_company}_{safe_title}"
    folder_path = os.path.join(BASE_LAMAR_DIR, tanggal_hari_ini, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    nama_user = profil.get('nama_lengkap', 'Nama Lengkap')
    # Ambil 2 kata pertama nama user untuk filename
    short_user_name = "_".join(nama_user.split()[:2])
    safe_user_name = _safe_filename(short_user_name, max_len=20)

    cv_filename = f"CV_{safe_user_name}_{safe_title}.docx"
    cl_filename = f"Resume_{safe_user_name}.docx"

    # ---------- 1. CV ----------
    parsed = parse_cv(cv_asli_teks or "")
    if not parsed["experience"] and profil.get('cv_mentah'):
        log("Parser", "Pakai cv_mentah dari profil")
        parsed = parse_cv(profil['cv_mentah'])
    if not parsed["experience"]:
        log("Parser", "Pengalaman kosong. Set DEBUG_CV=True")

    cv_doc = Document()
    render_cv(cv_doc, profil, nama_user, data_dokumen.get('ringkasan_tailored', ''), parsed)
    cv_docx_path = os.path.join(folder_path, cv_filename)
    cv_doc.save(cv_docx_path)

    # CONVERT DOCX KE PDF (OTOMATIS)
    if PDF_ENABLED:
        try:
            cv_pdf_filename = cv_filename.replace('.docx', '.pdf')
            cv_pdf_path = os.path.join(folder_path, cv_pdf_filename)
            convert(cv_docx_path, cv_pdf_path)
            log("PDF", f"CV berhasil dikonversi ke PDF: {cv_pdf_filename}")

            # Hapus file DOCX agar hanya tersisa PDF (opsional)
            try:
                os.remove(cv_docx_path)
                log("Cleanup", "File .docx sementara dihapus, tersisa file .pdf")
            except:
                pass
        except Exception as e:
            log("PDF Error", f"Gagal convert ke PDF: {e}. File .docx tetap disimpan.")

    if DEBUG_CV:
        with open(os.path.join(folder_path, "cv_parsed_debug.json"), "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)

    # ---------- 2. COVER LETTER ----------
    cl_doc = Document()
    _setup_doc(cl_doc)
    p = cl_doc.add_paragraph()
    _font(p.add_run(nama_user), size=14, bold=True)
    p.paragraph_format.space_after = Pt(0)
    kontak = profil.get('kontak', {}) or {}
    p = cl_doc.add_paragraph()
    _font(p.add_run(" | ".join(b for b in [kontak.get('email'), kontak.get('telepon')] if b)))
    p = cl_doc.add_paragraph()
    _font(p.add_run(datetime.now().strftime('%B %d, %Y')))
    p.paragraph_format.space_after = Pt(8)
    for para in re.split(r"\n\s*\n", (data_dokumen.get('cover_letter', '') or '').strip()):
        para = para.strip()
        if para:
            p = cl_doc.add_paragraph()
            _font(p.add_run(para.replace("\n", " ") if len(para) > 120 else para))
            p.paragraph_format.space_after = Pt(8)
    cl_docx_path = os.path.join(folder_path, cl_filename)
    cl_doc.save(cl_docx_path)

    # Convert Cover Letter juga ke PDF
    if PDF_ENABLED:
        try:
            cl_pdf_filename = cl_filename.replace('.docx', '.pdf')
            cl_pdf_path = os.path.join(folder_path, cl_pdf_filename)
            convert(cl_docx_path, cl_pdf_path)
            log("PDF", f"Cover Letter berhasil dikonversi ke PDF: {cl_pdf_filename}")
            try:
                os.remove(cl_docx_path)
            except:
                pass
        except Exception as e:
            log("PDF Error", f"Gagal convert Cover Letter: {e}")

    # ---------- 3. EMAIL BODY ----------
    with open(os.path.join(folder_path, f"Email_Body_{safe_company}.txt"), "w", encoding="utf-8") as f:
        f.write(data_dokumen.get('email_body', ''))

    # ---------- 4. INFO LOKER ----------
    with open(os.path.join(folder_path, "info_loker.txt"), "w", encoding="utf-8") as f:
        f.write("=== INFORMASI LOWONGAN KERJA ===\n")
        f.write(f"Perusahaan : {company}\n")
        f.write(f"Posisi     : {job_title}\n")
        f.write(f"Skor Match : {job.get('skor', 'N/A')}%\n")
        f.write(f"URL Loker  : {url}\n")

    log("Success", f"Tersimpan di: {folder_path}")
    return folder_path


# ==========================================
# 7. MAIN (WITH AUTO STATUS UPDATE)
# ==========================================
def main():
    print("\n" + "=" * 60)
    print("JOB HUNTER AI - FASE 3: TAILOR (v2 WITH TRACKING)")
    print("=" * 60)

    if not os.path.exists(PROFIL_FILE) or not os.path.exists(LOWONGAN_FILE) or not os.path.exists(CV_PATHS_FILE):
        log("Error", "File memori tidak lengkap!")
        return

    with open(PROFIL_FILE, "r", encoding="utf-8") as f:
        profil = json.load(f)
    with open(LOWONGAN_FILE, "r", encoding="utf-8") as f:
        list_lowongan = json.load(f)
    with open(CV_PATHS_FILE, "r", encoding="utf-8") as f:
        cv_paths = json.load(f)

    if not cv_paths:
        log("Error", "CV path tidak ditemukan!")
        return

    cv_pdf_path = cv_paths[0]
    log("CV Asli", f"Membaca: {cv_pdf_path}")
    cv_asli_teks = baca_pdf_asli(cv_pdf_path)

    if not cv_asli_teks:
        log("Warning", "Pakai cv_mentah dari profil")
        cv_asli_teks = profil.get('cv_mentah', '')

    # FILTER: Hanya proses yang status 'pending'
    pending_jobs = [j for j in list_lowongan if j.get('status', 'pending') == 'pending']

    if not pending_jobs:
        log("Warning", "Tidak ada lowongan pending.")
        return

    print(f"\nMemproses {len(pending_jobs)} lowongan pending...")
    print("-" * 60)

    sukses_count = 0
    for i, job in enumerate(pending_jobs, 1):
        job_title = job['title']
        company = job.get('company', 'Perusahaan')
        url = job['url']
        snippet = job['snippet']

        print(f"\n[{i}/{len(pending_jobs)}] {job_title} ({company})")

        deskripsi_full = ambil_deskripsi_loker(url)
        if not deskripsi_full or len(deskripsi_full) < 100:
            deskripsi_full = snippet

        hasil_ai = generate_dokumen_lamaran(profil, cv_asli_teks, job_title, company, deskripsi_full)

        if hasil_ai:
            simpan_hasil_lamaran(job, hasil_ai, cv_asli_teks, profil)

            # AUTO UPDATE STATUS jadi 'applied'
            #update_job_status(url, "applied")

            sukses_count += 1
            log("OK", "Dokumen dibuat & status updated")
        else:
            log("Gagal", "AI gagal generate")

    print("\n" + "=" * 60)
    print(f"SELESAI! {sukses_count} lowongan diproses.")
    print("=" * 60)


if __name__ == "__main__":
    main()
