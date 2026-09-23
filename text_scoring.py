import re
from typing import List, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    _factory = StemmerFactory()
    _stemmer = _factory.create_stemmer()
except ImportError:
    class _DummyStemmer:
        def stem(self, word: str) -> str:
            return word
    _stemmer = _DummyStemmer()

# daftar kata hubung dan kata umum bahasa indonesia yang diabaikan
INDO_STOPWORDS = {
    "dan", "yang", "di", "ke", "dari", "pada", "untuk", "dengan",
    "ini", "itu", "saya", "kami", "kita", "anda", "atau", "karena",
    "jadi", "sebagai", "jika", "bila", "agar", "adalah", "ialah",
    "dalam", "tidak", "ya", "juga", "sebuah", "suatu", "para", "oleh",
    "serta", "saat", "ketika", "lebih", "kurang", "akan", "telah",
    "sudah", "masih", "bisa", "biasa", "ada", "menggunakan", "pernah",
    "seperti", "lalu", "saja", "bagaimana", "apa", "halo", "tes"
}

def preprocess(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    tokens = text.split()
    
    filtered = []
    for tok in tokens:
        if tok in INDO_STOPWORDS or len(tok) <= 2:
            continue
        filtered.append(_stemmer.stem(tok))
    return " ".join(filtered)

def extract_meaningful_terms(text: str) -> List[str]:
    clean = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
    words = clean.split()
    seen = set()
    terms = []
    for w in words:
        if len(w) > 3 and w not in INDO_STOPWORDS and w not in seen:
            seen.add(w)
            terms.append(w)
    return terms

def evaluate_interview_answer(user_answer: str, ideal_answers: List[str], question_text: str = "") -> Dict:
    if not user_answer or not user_answer.strip():
        return {
            "score": 0,
            "similarity": 0.0,
            "feedback": "Jawaban masih kosong. Silakan berikan penjelasan Anda.",
            "matched_keywords": [],
            "missing_keywords": [],
            "is_irrelevant": True
        }

    # kumpulkan istilah acuan dari jawaban ideal dan pertanyaan
    combined_reference = " ".join(ideal_answers)
    reference_terms = extract_meaningful_terms(combined_reference)
    if question_text:
        q_terms = extract_meaningful_terms(question_text)
        for qt in q_terms:
            if qt not in reference_terms:
                reference_terms.append(qt)

    user_raw_lower = user_answer.lower()
    user_words = user_raw_lower.split()
    word_count = len(user_words)

    # cocokkan kata kunci yang disebut pengguna
    matched = []
    missing = []
    
    for term in reference_terms:
        stemmed_term = _stemmer.stem(term)
        if term in user_raw_lower or stemmed_term in user_raw_lower:
            matched.append(term)
        else:
            missing.append(term)

    # hitung kemiripan kalimat dengan tf-idf dan cosine similarity
    proc_user = preprocess(user_answer)
    proc_ideals = [preprocess(ans) for ans in ideal_answers]

    if not proc_user.strip():
        return {
            "score": 10,
            "similarity": 0.0,
            "feedback": "Jawaban terlalu singkat atau tidak mengandung kata yang dapat dianalisis.",
            "matched_keywords": [],
            "missing_keywords": missing[:5],
            "is_irrelevant": True
        }

    corpus = [proc_user] + proc_ideals
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
        sim = float(np.max(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])))
    except Exception:
        sim = 0.0

    # ukur juga kesamaan dengan pertanyaan
    if question_text:
        proc_q = preprocess(question_text)
        if proc_q:
            try:
                q_vecs = vectorizer.fit_transform([proc_user, proc_q])
                q_sim = float(cosine_similarity(q_vecs[0:1], q_vecs[1:2])[0][0])
            except Exception:
                q_sim = 0.0
        else:
            q_sim = 0.0
    else:
        q_sim = 0.0

    effective_sim = max(sim, q_sim * 0.75)

    # filter kalau jawaban terdeteksi ngawur atau sama sekali tidak nyambung
    if len(matched) == 0 and effective_sim < 0.10:
        return {
            "score": max(10, min(25, int(round(effective_sim * 100)))),
            "similarity": round(effective_sim, 4),
            "feedback": "Jawaban terdeteksi tidak relevan dengan pertanyaan wawancara teknis ini. Coba fokus pada konsep dan terminologi yang diminta.",
            "matched_keywords": [],
            "missing_keywords": missing[:5],
            "is_irrelevant": True
        }

    # perhitungan bobot: kemiripan semantik, cakupan kata kunci, dan panjang jawaban
    semantic_score = min(1.0, effective_sim * 2.0)
    target_kw_count = min(len(reference_terms), 5) if reference_terms else 3
    coverage_score = min(1.0, len(matched) / float(target_kw_count))

    if word_count < 10:
        depth_score = 0.4
    elif word_count < 25:
        depth_score = 0.75
    else:
        depth_score = 1.0

    raw_composite = (semantic_score * 0.45) + (coverage_score * 0.40) + (depth_score * 0.15)
    
    # skala skor akhir 45 sampai 98
    final_score = int(round(45 + raw_composite * 53))
    final_score = max(35, min(98, final_score))

    # feedback berdasarkan skor yang didapat
    if final_score >= 85:
        feedback = "Jawaban sangat komprehensif, tepat sasaran, dan mencakup terminologi teknis yang kuat."
    elif final_score >= 70:
        feedback = "Pemahaman konsep sudah baik dan relevan. Tambahkan detail implementasi agar argumen semakin meyakinkan."
    elif final_score >= 50:
        feedback = "Konsep dasar mulai terlihat, tetapi masih cukup umum. Sebutkan metode atau alat spesifik yang biasa Anda gunakan."
    else:
        feedback = "Jawaban masih kurang mendalam dan banyak poin penting yang belum tersentuh. Pelajari kata kunci saran di bawah."

    return {
        "score": final_score,
        "similarity": round(effective_sim, 4),
        "feedback": feedback,
        "matched_keywords": matched[:7],
        "missing_keywords": missing[:5],
        "is_irrelevant": False
    }

# fungsi pendukung tambahan
def tfidf_cosine_score(user_answer: str, ideal_answers: List[str]) -> float:
    res = evaluate_interview_answer(user_answer, ideal_answers)
    return res["similarity"]

def similarity_to_score(similarity: float) -> int:
    sim = max(0.0, min(1.0, similarity))
    return int(round(40 + sim * 55))

def analyze_keyword_gap(user_answer: str, ideal_answers: List[str]) -> Dict[str, List[str]]:
    res = evaluate_interview_answer(user_answer, ideal_answers)
    return {
        "matched": res["matched_keywords"],
        "missing": res["missing_keywords"]
    }
