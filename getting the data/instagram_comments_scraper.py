"""
instagram_comments_scraper.py
Fixed for apify-client >= 1.0 where .call() returns a Run object.
"""

import os
import json
import hashlib
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

SOURCES = {
    "edeeste.rd":          {"platform": "instagram", "utility_type": "EDEESTE"},
    "ededeje":             {"platform": "facebook",  "utility_type": "EDEESTE"},
    "coraabord":           {"platform": "instagram", "utility_type": "CORAABO"},
    "coraabo.do":          {"platform": "facebook",  "utility_type": "CORAABO"},
    "alcaldiabc":          {"platform": "instagram", "utility_type": "ALCALDIA_BC"},
    "AlcaldiaBC":          {"platform": "facebook",  "utility_type": "ALCALDIA_BC"},
    "bocachicard04":       {"platform": "instagram", "utility_type": "MEDIA"},
    "bocachicainformando": {"platform": "instagram", "utility_type": "MEDIA"},
    "mediosilustradostv":  {"platform": "instagram", "utility_type": "MEDIA"},
}

ACTOR_INSTAGRAM = "apify/instagram-comment-scraper"
ACTOR_FACEBOOK  = "apify/facebook-comments-scraper"
COMMENTS_LIMIT  = 15

def make_comment_id(handle: str, raw_text: str) -> str:
    payload = f"{handle}|{raw_text}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_post_urls() -> dict:
    root = os.path.join(os.path.dirname(__file__), "..", "post_urls.json")
    path = os.path.normpath(root)
    if not os.path.exists(path):
        raise FileNotFoundError(f"post_urls.json not found at {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def get_dataset_id(run) -> str:
    """
    Handle both SDK versions:
    - Old SDK: run is a dict  -> run["defaultDatasetId"]
    - New SDK: run is a Run object -> run.default_dataset_id
    """
    if isinstance(run, dict):
        return run["defaultDatasetId"]
    return run.default_dataset_id

def build_row(item: dict, handle: str, meta: dict, scraped_at: str) -> dict:
    raw_text = (
        item.get("text")
        or item.get("message")
        or item.get("commentText")
        or ""
    ).strip()

    post_url = (
        item.get("postUrl")
        or item.get("url")
        or item.get("postId", "")
    )

    return {
        "comment_id":      make_comment_id(handle, raw_text),
        "scraped_at":      scraped_at,
        "post_url":        str(post_url),
        "source_handle":   handle,
        "platform":        meta["platform"],
        "utility_type":    meta["utility_type"],
        "raw_text":        raw_text,
        "cleaned_text":    "",
        "lang_detected":   "",
        "sentiment_label": "",
        "score_pos":       None,
        "score_neu":       None,
        "score_neg":       None,
        "lexicon_boosted": False,
        "is_excluded":     False,
    }

def scrape_instagram(client: ApifyClient, handle: str, urls: list, meta: dict, scraped_at: str) -> list:
    print(f"  [IG] @{handle} — {len(urls)} post(s) ...")
    run_input = {
        "directUrls":     urls,
        "resultsLimit":   COMMENTS_LIMIT,
        "includeReplies": False,
    }
    try:
        run        = client.actor(ACTOR_INSTAGRAM).call(run_input=run_input)
        dataset_id = get_dataset_id(run)
        items      = list(client.dataset(dataset_id).iterate_items())
        rows       = [
            build_row(i, handle, meta, scraped_at)
            for i in items
            if (i.get("text") or i.get("commentText") or "").strip()
        ]
        print(f"      {len(rows)} comments fetched.")
        return rows
    except Exception as exc:
        print(f"      ERROR: {exc}")
        return []

def scrape_facebook(client: ApifyClient, handle: str, urls: list, meta: dict, scraped_at: str) -> list:
    print(f"  [FB] {handle} — {len(urls)} post(s) ...")
    run_input = {
        "startUrls":    [{"url": u} for u in urls],
        "resultsLimit": COMMENTS_LIMIT,
    }
    try:
        run        = client.actor(ACTOR_FACEBOOK).call(run_input=run_input)
        dataset_id = get_dataset_id(run)
        items      = list(client.dataset(dataset_id).iterate_items())
        rows       = [
            build_row(i, handle, meta, scraped_at)
            for i in items
            if (i.get("message") or i.get("text") or "").strip()
        ]
        print(f"      {len(rows)} comments fetched.")
        return rows
    except Exception as exc:
        print(f"      ERROR: {exc}")
        return []

def main():
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        raise EnvironmentError("APIFY_API_TOKEN not found in .env file.")

    post_urls  = load_post_urls()
    client     = ApifyClient(token)
    scraped_at = utc_now()
    all_rows   = []

    print(f"\n=== Scrape run started: {scraped_at} ===\n")

    for handle, urls in post_urls.items():
        if not urls:
            print(f"  Skipping {handle} — no URLs listed.")
            continue
        meta = SOURCES.get(handle)
        if not meta:
            print(f"  WARNING: {handle} not in SOURCES registry — skipping.")
            continue
        if meta["platform"] == "instagram":
            rows = scrape_instagram(client, handle, urls, meta, scraped_at)
        else:
            rows = scrape_facebook(client, handle, urls, meta, scraped_at)
        all_rows.extend(rows)

    df     = pd.DataFrame(all_rows) if all_rows else pd.DataFrame()
    before = len(df)
    if not df.empty:
        df = df.drop_duplicates(subset=["comment_id"], keep="first")
    dupes = before - len(df)

    out_path = os.path.join(os.path.dirname(__file__), "raw_comments.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\n=== Done ===")
    print(f"  Total rows fetched : {before}")
    print(f"  Duplicates removed : {dupes}")
    print(f"  Rows written       : {len(df)}")
    print(f"  Output             : {out_path}\n")

    sources_out = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "sources.json"))
    with open(sources_out, "w", encoding="utf-8") as f:
        json.dump([{"handle": k, **v} for k, v in SOURCES.items()], f, indent=2, ensure_ascii=False)
    print(f"  sources.json updated: {sources_out}")

if __name__ == "__main__":
    main()
