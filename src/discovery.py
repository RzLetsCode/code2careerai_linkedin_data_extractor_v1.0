import json
import os
import requests

from dotenv import load_dotenv

load_dotenv()

MOCK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "mock_profiles.json",
)

TERMS = {
    "Students / Freshers": (
         '("final year student" OR "B.Tech student" OR '
    '"computer science student" OR fresher OR '
    '"2026 graduate" OR "2027 graduate" OR '
    '"recent graduate" OR "entry level software engineer" '
    'OR "aspiring AI engineer") '
    '(Python OR AI OR GenAI OR software OR programming) '
    '-senior -manager -lead -director -principal '
    '-10 years -8 years -5 years'
    ),

    "Early Career 1–2 YOE": (
        '("associate software engineer" OR '
        '"junior software engineer" OR '
        '"junior data analyst" OR '
        '"associate engineer") '
        '("1 year" OR "2 years" OR junior)'
    ),

    "Career Switchers": (
        '("career switcher" OR "QA to AI" OR '
        '"learning GenAI" OR "support engineer")'
    ),
}


def build_boolean_query(bucket, keywords):
    base_terms = TERMS.get(
        bucket,
        TERMS["Students / Freshers"],
    )

    keywords = (keywords or "").strip()

    return (
        f"site:linkedin.com/in/ {base_terms} {keywords}"
    ).strip()


def discover_profiles(bucket, keywords, use_mock=True, limit=10):
    if use_mock:
        with open(MOCK_PATH, encoding="utf-8") as file:
            profiles = json.load(file)

        matched = [
            profile
            for profile in profiles
            if profile.get("bucket") == bucket
        ]

        return (matched or profiles)[:limit]

    key = os.getenv("SERPER_API_KEY", "").strip()

    if not key:
        raise RuntimeError(
            "SERPER_API_KEY missing. Add it to .env "
            "or enable offline demo mode."
        )

    response = requests.post(
        "https://google.serper.dev/search",
        headers={
            "X-API-KEY": key,
            "Content-Type": "application/json",
        },
        json={
            "q": build_boolean_query(bucket, keywords),
            "num": min(limit, 10),
        },
        timeout=20,
    )

    response.raise_for_status()

    results = []
    seen_urls = set()

    for item in response.json().get("organic", []):
        url = (item.get("link") or "").strip()

        # Only use public LinkedIn profile URLs.
        if "linkedin.com/in/" not in url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        title = (item.get("title") or "Public profile").strip()
        snippet = (item.get("snippet") or "").strip()

        results.append(
            {
                "name": title.split(" - ")[0],
                "headline": title,
                "snippet": snippet,
                "url": url,
                "bucket": bucket,
            }
        )

    return results[:limit]