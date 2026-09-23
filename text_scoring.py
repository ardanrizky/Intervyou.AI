import re
from typing import List, Dict, Tuple
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

INDO_STOPWORDS = {
    "dan", "yang", "di", "ke", "dari", "pada", "untuk", "dengan",
    "ini", "itu", "saya", "kami", "kita", "anda", "atau", "karena",
    "jadi", "sebagai", "jika", "bila", "agar", "adalah", "ialah",
    "dalam", "tidak", "ya", "juga", "sebuah", "suatu", "para", "oleh",
    "serta", "saat", "ketika", "lebih", "kurang", "akan", "telah",
    "sudah", "masih", "bisa", "biasa", "ada", "menggunakan", "pernah"
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

def extract_keywords(text: str) -> List[str]:
    clean = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
    words = clean.split()
    seen = set()
    keywords = []
    for w in words:
        if len(w) > 3 and w not in INDO_STOPWORDS and w not in seen:
            seen.add(w)
            keywords.append(w)
    return keywords[:8]

def analyze_keyword_gap(user_answer: str, ideal_answers: List[str]) -> Dict[str, List[str]]:
    combined_ideal = " ".join(ideal_answers)
    ideal_keywords = extract_keywords(combined_ideal)
    user_lower = user_answer.lower()
    
    matched = [kw for kw in ideal_keywords if kw in user_lower]
    missing = [kw for kw in ideal_keywords if kw not in user_lower][:5]
    
    return {
        "matched": matched,
        "missing": missing
    }

def tfidf_cosine_score(user_answer: str, ideal_answers: List[str]) -> float:
    if not user_answer or not ideal_answers:
        return 0.0

    processed_user = preprocess(user_answer)
    processed_ideals = [preprocess(ans) for ans in ideal_answers]

    if not processed_user.strip():
        return 0.0

    corpus = [processed_user] + processed_ideals
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)

    user_vec = tfidf_matrix[0:1]
    ideal_vecs = tfidf_matrix[1:]

    sim = cosine_similarity(user_vec, ideal_vecs)
    return float(np.max(sim))

def similarity_to_score(similarity: float) -> int:
    sim = max(0.0, min(1.0, similarity))
    score = 40 + sim * 55
    return int(round(score))
