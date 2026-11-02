import json
from urllib.parse import quote_plus, urlparse


def handoff_html(note, url, name="", headline=""):
    url = (url or "").strip()
    name = (name or "").strip()
    headline = (headline or "").strip()

    parsed = urlparse(url)

    is_placeholder = (
        "linkedin.com" in (parsed.hostname or "").lower()
        and "example-" in (parsed.path or "").lower()
    )

    if is_placeholder or not url:
        # Mock profile ke liye generic LinkedIn search
        query = name.strip() or headline.strip() or "software engineer"
        target_url = (
            "https://www.linkedin.com/search/results/people/?keywords="
            + quote_plus(query)
        )
    else:
        # Live search se mila real LinkedIn profile
        target_url = url

    data = json.dumps({
        "note": note or "",
        "url": target_url,
    })

    return f"""
<div>
<button id="handoff"
style="padding:10px 14px;border:0;border-radius:8px;
background:#2563eb;color:white;cursor:pointer">
Copy note + open LinkedIn
</button>

<span id="status"
style="margin-left:8px;font-size:12px"></span>
</div>

<script>
const d = {data};

document.getElementById('handoff').addEventListener(
    'click',
    async () => {{
        try {{
            await navigator.clipboard.writeText(d.note);
        }} catch (e) {{
            document.getElementById('status').textContent =
                'Clipboard blocked. Copy the note manually.';
        }}

        window.open(d.url, '_blank');

        document.getElementById('status').textContent =
            'Opened LinkedIn. Verify the profile and send manually.';
    }}
);
</script>
"""