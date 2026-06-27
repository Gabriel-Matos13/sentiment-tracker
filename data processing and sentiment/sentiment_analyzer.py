"""
sentiment_analyzer.py
Reads raw_comments.csv, cleans text, detects language,
scores sentiment with pysentimiento + DR utility lexicon boost,
and writes scored_comments.csv.
"""

import os
import re
import unicodedata
import pandas as pd
from langdetect import detect, LangDetectException
from pysentimiento import create_analyzer

# ---------------------------------------------------------------------------
# Dominican utility lexicon
# ---------------------------------------------------------------------------
DR_NEGATIVE_LEXICON = [
    "apagón", "apagones", "avería", "averías", "sin luz", "sin electricidad",
    "sin corriente", "se fue la luz", "se fue el agua", "sin agua",
    "circuito fuera", "corte de luz", "corte de agua",
    "pésimo servicio", "mal servicio", "no llega", "no tienen agua",
    "no tenemos agua", "no hay agua", "no hay luz", "no nos llega",
    "meses sin agua", "días sin luz", "horas sin luz",
    "edeeste", "coraabo", "caasd", "eted",
    "coño", "diablo", "maldito", "maldita", "jodia", "jodido",
    "harto", "hartos", "cansado", "cansados", "abusadores",
    "ladrones", "inútil", "inútiles", "vergüenza",
]

DR_POSITIVE_LEXICON = [
    "gracias", "excelente", "bien hecho", "buen trabajo", "enhorabuena",
    "felicitaciones", "bravo", "resolvieron", "arreglaron", "volvió la luz",
    "llegó el agua", "trabajando", "gestión",
]

# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(
        r"[^\w\s\u00C0-\u024F\u1E00-\u1EFF.,!?;:\-\'\"]",
        "", text, flags=re.UNICODE,
    )
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_language(text: str) -> str:
    if not text or len(text.split()) < 2:
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"

# ---------------------------------------------------------------------------
# Lexicon boost
# ---------------------------------------------------------------------------

def apply_lexicon_boost(cleaned, score_pos, score_neu, score_neg):
    boosted = False
    BOOST   = 0.15

    neg_match = any(term in cleaned for term in DR_NEGATIVE_LEXICON)
    pos_match = any(term in cleaned for term in DR_POSITIVE_LEXICON)

    if neg_match:
        score_neg = min(1.0, score_neg + BOOST)
        score_neu = max(0.0, score_neu - BOOST)
        boosted   = True

    if pos_match and not neg_match:
        score_pos = min(1.0, score_pos + BOOST)
        score_neu = max(0.0, score_neu - BOOST)
        boosted   = True

    total = score_pos + score_neu + score_neg
    if total > 0:
        score_pos /= total
        score_neu /= total
        score_neg /= total

    return round(score_pos, 4), round(score_neu, 4), round(score_neg, 4), boosted

def label_from_scores(pos, neu, neg):
    scores = {"POS": pos, "NEU": neu, "NEG": neg}
    return max(scores, key=scores.get)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    base       = os.path.dirname(__file__)
    input_path = os.path.normpath(os.path.join(base, "..", "getting the data", "raw_comments.csv"))
    out_path   = os.path.join(base, "scored_comments.csv")

    print(f"\n=== Sentiment Analyzer ===")
    print(f"  Input : {input_path}")
    print(f"  Output: {out_path}\n")

    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"  Rows loaded: {len(df)}")

    print("  Loading pysentimiento model (first run may take a few minutes) ...")
    analyzer = create_analyzer(task="sentiment", lang="es")
    print("  Model ready.\n")

    results = []

    for i, row in df.iterrows():
        raw     = str(row.get("raw_text", ""))
        cleaned = clean_text(raw)
        lang    = detect_language(cleaned)

        is_excluded = (
            lang not in ("es", "unknown")
            or len(cleaned.split()) < 2
            or not cleaned
        )

        score_pos = score_neu = score_neg = 0.0
        sentiment_label = ""
        lexicon_boosted = False

        if not is_excluded:
            try:
                result      = analyzer.predict(cleaned)
                score_pos   = round(result.probas.get("POS", 0.0), 4)
                score_neu   = round(result.probas.get("NEU", 0.0), 4)
                score_neg   = round(result.probas.get("NEG", 0.0), 4)
                score_pos, score_neu, score_neg, lexicon_boosted = apply_lexicon_boost(
                    cleaned, score_pos, score_neu, score_neg
                )
                sentiment_label = label_from_scores(score_pos, score_neu, score_neg)
            except Exception as exc:
                print(f"  Warning — row {i}: {exc}")
                is_excluded = True

        results.append({
            **row.to_dict(),
            "cleaned_text":    cleaned,
            "lang_detected":   lang,
            "sentiment_label": sentiment_label,
            "score_pos":       score_pos if not is_excluded else None,
            "score_neu":       score_neu if not is_excluded else None,
            "score_neg":       score_neg if not is_excluded else None,
            "lexicon_boosted": lexicon_boosted,
            "is_excluded":     is_excluded,
        })

        if (i + 1) % 25 == 0:
            print(f"  Processed {i + 1}/{len(df)} rows ...")

    out_df = pd.DataFrame(results)
    cols = [
        "comment_id", "scraped_at", "post_url", "source_handle",
        "platform", "utility_type", "raw_text", "cleaned_text",
        "lang_detected", "sentiment_label", "score_pos", "score_neu",
        "score_neg", "lexicon_boosted", "is_excluded",
    ]
    out_df = out_df[cols]
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    scored   = out_df[out_df["is_excluded"] == False]
    n_scored = len(scored)
    excluded = len(out_df) - n_scored

    print(f"\n=== Done ===")
    print(f"  Total rows  : {len(out_df)}")
    print(f"  Scored      : {n_scored}")
    print(f"  Excluded    : {excluded}")

    if n_scored > 0:
        dist = scored["sentiment_label"].value_counts()
        print(f"\n  Sentiment distribution:")
        for label in ["NEG", "NEU", "POS"]:
            count = dist.get(label, 0)
            pct   = round(count / n_scored * 100, 1)
            bar   = "█" * int(pct / 3)
            print(f"    {label}: {bar} {count} ({pct}%)")
        boosted = scored["lexicon_boosted"].sum()
        print(f"\n  Lexicon-boosted: {boosted} ({round(boosted/n_scored*100,1)}%)")

    print(f"\n  Output: {out_path}\n")

if __name__ == "__main__":
    main()
