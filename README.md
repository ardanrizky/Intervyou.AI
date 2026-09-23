# Intervyou.AI

Aplikasi web simulasi wawancara kerja teknis berbasis Flask dan pemrosesan bahasa alami (NLP). Aplikasi ini dirancang untuk latihan menghadapi pertanyaan teknis pada 7 bidang pekerjaan: Data Scientist, Data Engineer, Machine Learning Engineer, Backend Developer, Frontend Developer, Web Developer, dan Mobile Developer.

## Fitur

- Pilihan 7 bidang pekerjaan teknis dengan masing-masing 7 pertanyaan acuan.
- Dua pilihan input jawaban: berbicara langsung menggunakan suara (Web Speech API) atau mengetik teks.
- Penilaian otomatis menggunakan preprocessing teks Bahasa Indonesia (PySastrawi), pembobotan TF-IDF, dan Cosine Similarity terhadap jawaban acuan.
- Analisis kesenjangan kata kunci (menampilkan istilah yang cocok dan istilah penting yang terlewat).
- Evaluasi kualitatif dan skor instan untuk setiap pertanyaan.
- Riwayat sesi yang tersimpan permanen menggunakan SQLite database lokal.
- Halaman riwayat dengan pagination dan fitur unduh laporan ke format Excel (.xlsx).

## Teknologi yang Digunakan

- Python 3.10+
- Flask (Web framework)
- Scikit-learn & NumPy (TF-IDF vectorizer dan Cosine Similarity)
- PySastrawi (Stemmer teks Bahasa Indonesia)
- SQLite3 (Penyimpanan data riwayat sesi)
- Pandas & OpenPyXL (Ekspor data ke Excel)
- HTML, CSS, dan JavaScript murni (Antarmuka pengguna)
- Web Speech Recognition API (Input suara)

## Cara Menjalankan Aplikasi

1. Clone repositori ini:
```bash
git clone https://github.com/USERNAME/Intervyou.AI.git
cd Intervyou.AI
```

2. Buat dan aktifkan virtual environment:
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / Mac
source .venv/bin/activate
```

3. Pasang dependensi yang dibutuhkan:
```bash
pip install -r requirements.txt
```

4. Jalankan aplikasi:
```bash
python app.py
```

5. Buka browser dan akses alamat:
```text
http://localhost:7070
```

## Struktur Folder

```text
Intervyou.AI/
├── app.py                  # Routing aplikasi, database SQLite, dan API
├── text_scoring.py         # Modul NLP (preprocessing, TF-IDF, similarity, kata kunci)
├── answer_keys.py          # Kunci jawaban acuan tiap peran
├── questions/              # Bank pertanyaan teknis terstruktur
│   ├── __init__.py
│   ├── data_scientist.py
│   ├── data_engineer.py
│   ├── ml_engineer.py
│   ├── backend_developer.py
│   ├── frontend_developer.py
│   ├── web_developer.py
│   └── mobile_developer.py
├── templates/              # File template HTML (Jinja2)
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── interview.html
│   └── history.html
├── static/                 # Aset statis CSS dan JavaScript
│   ├── css/style.css
│   └── js/interview.js
├── .gitignore              # Daftar file yang diabaikan Git
├── requirements.txt        # Daftar dependensi library
└── README.md               # Dokumentasi proyek
```

## Lisensi
Proyek ini dibuat untuk keperluan portofolio dan latihan akademik.
