
import os
import re
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

load_dotenv()


class OutreachPayload(BaseModel):
    detected_persona: Literal[
        "Fresher",
        "1-2_YOE",
        "Career_Switcher",
    ] = Field(description="The person's career stage.")

    relevance_score: int = Field(
        ge=1,
        le=10,
        description="Relevance for practical AI and software learning.",
    )

    reasoning: str = Field(
        description="One-line explanation based on profile evidence."
    )

    connection_note: str = Field(
        max_length=299,
        description="Personalized LinkedIn connection note under 300 characters.",
    )

    follow_up_dm: str = Field(
        description="Warm follow-up message under 100 words, mentioning code2careerai.com."
    )

    generator: str = Field(
        description="The generation method used."
    )

    @field_validator("follow_up_dm")
    @classmethod
    def validate_follow_up_words(cls, value):
        if len(value.split()) >= 100:
            raise ValueError("Follow-up DM must be under 100 words.")
        return value.strip()

    @field_validator("connection_note")
    @classmethod
    def validate_connection_note(cls, value):
        if len(value) >= 300:
            raise ValueError("Connection note must be under 300 characters.")
        return value.strip()


SWITCHER_SIGNALS = (
    "career switch", "career change", "switching to",
    "transition into", "transition to ai", "moving into",
    "move into", "qa to ai", "support to ai",
    "career transition",
)

EXPERIENCE_SIGNALS = (
    "associate software engineer", "junior developer",
    "junior engineer", "junior data analyst",
    "1 year experience", "2 years experience",
    "1 year of experience", "2 years of experience",
    "1.5 yoe", "1-2 yoe", "1-2 years",
    "2 years", "1 year", "yoe",
)

FRESHER_SIGNALS = (
    "student", "final year", "fresher", "fresh graduate",
    "2026 graduate", "2025 graduate", "2027 graduate",
    "entry-level", "entry level", "undergraduate",
    "college student", "recent graduate",
)

RELEVANCE_SIGNALS = {
    "artificial intelligence": 3,
    "machine learning": 3,
    "generative ai": 3,
    "genai": 3,
    "ai": 2,
    "llm": 2,
    "llms": 2,
    "rag": 2,
    "python": 2,
    "software engineering": 2,
    "software": 2,
    "programming": 2,
    "developer": 2,
    "project": 2,
    "projects": 2,
    "portfolio": 2,
    "data structures": 2,
    "automation": 2,
    "engineering": 1,
    "building": 1,
    "learning": 1,
    "api": 1,
    "apis": 1,
    "sql": 1,
    "interested in": 1,
}

SKILL_TERMS = (
    "Python", "Java", "JavaScript", "TypeScript", "SQL",
    "C++", "machine learning", "AI", "GenAI", "LLMs",
    "RAG", "data structures", "REST APIs", "automation",
    "data analysis", "backend engineering", "software engineering",
)


def _clean(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _profile_text(profile):
    return " ".join(
        _clean(profile.get(field))
        for field in ("headline", "snippet", "bucket")
    ).lower()


def _persona(profile):
    text = _profile_text(profile)
    bucket = _clean(profile.get("bucket")).lower()

    if any(signal in text for signal in SWITCHER_SIGNALS):
        return "Career_Switcher"

    if "career switch" in bucket or "career switcher" in bucket:
        return "Career_Switcher"

    if any(signal in text for signal in EXPERIENCE_SIGNALS):
        return "1-2_YOE"

    if "early career" in bucket:
        return "1-2_YOE"

    if any(signal in text for signal in FRESHER_SIGNALS):
        return "Fresher"

    if "student" in bucket or "fresher" in bucket:
        return "Fresher"

    return "Fresher"


def _extract_skills(profile):
    text = " ".join(
        _clean(profile.get(field))
        for field in ("headline", "snippet")
    ).lower()

    found = []
    for skill in SKILL_TERMS:
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"
        if re.search(pattern, text):
            found.append(skill)

    return found[:4]


def _relevance(profile):
    text = _profile_text(profile)
    headline = _clean(profile.get("headline"))
    snippet = _clean(profile.get("snippet"))

    if not headline and not snippet:
        return 1, "Insufficient profile text to assess relevance."

    score = 1
    matched = []

    for signal, weight in RELEVANCE_SIGNALS.items():
        pattern = r"(?<!\w)" + re.escape(signal) + r"(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            score += weight
            matched.append(signal)

    if len(_extract_skills(profile)) >= 2:
        score += 1

    score = max(1, min(score, 10))

    if matched:
        reason = (
            f"Heuristic score {score}/10 based on profile text "
            f"mentioning {', '.join(matched[:4])}. "
            "This is an estimate, not a verified assessment."
        )
    else:
        reason = (
            f"Heuristic score {score}/10 due to limited explicit "
            "AI, software, project, or learning evidence."
        )

    return score, reason


def _first_name(profile):
    name = _clean(profile.get("name"))
    return name.split()[0] if name else "there"


def _background(profile):
    headline = _clean(profile.get("headline"))
    if headline:
        return headline[:90].rstrip(" .,-")

    skills = _extract_skills(profile)
    return ", ".join(skills[:3]) if skills else "professional interests"


def _fallback(profile):
    persona = _persona(profile)
    score, reasoning = _relevance(profile)
    name = _first_name(profile)
    background = _background(profile)
    skills = _extract_skills(profile)

    skill_text = ""
    if skills:
        skill_text = f" Your profile mentions {', '.join(skills[:3])}."

    if persona == "Fresher":
        note = (
            f"Hi {name}, noticed your {background} background. "
            "We share practical learning resources at code2careerai.com. "
            "Happy to connect."
        )
        dm = (
            f"Hi {name}, I noticed your {background} background."
            f"{skill_text} Explore practical learning resources and "
            "project ideas at code2careerai.com if useful."
        )

    elif persona == "1-2_YOE":
        note = (
            f"Hi {name}, your {background} background caught my attention. "
            "We share practical engineering and AI resources at "
            "code2careerai.com. Happy to connect."
        )
        dm = (
            f"Hi {name}, I noticed your {background} background."
            f"{skill_text} If you're exploring practical projects or "
            "applied AI, code2careerai.com may be useful."
        )

    else:
        note = (
            f"Hi {name}, noticed your {background} interests. "
            "We share project-based learning resources at "
            "code2careerai.com. Happy to connect."
        )
        dm = (
            f"Hi {name}, I noticed your {background} interests."
            f"{skill_text} If you're exploring new skills, you can "
            "check code2careerai.com for practical learning resources."
        )

    return OutreachPayload(
        detected_persona=persona,
        relevance_score=score,
        reasoning=reasoning,
        connection_note=note[:299],
        follow_up_dm=" ".join(dm.split()[:99]),
        generator="local heuristic fallback",
    ).model_dump()


def _llm_score(profile):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    client = OpenAI(api_key=api_key, timeout=25.0, max_retries=1)

    profile_data = {
        "name": _clean(profile.get("name")),
        "headline": _clean(profile.get("headline")),
        "snippet": _clean(profile.get("snippet")),
        "url": _clean(profile.get("url")),
        "target_bucket": _clean(profile.get("bucket")),
    }

    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful learner-discovery assistant. "
                    "Classify the profile into exactly one persona: "
                    "Fresher, 1-2_YOE, or Career_Switcher. "
                    "Use only evidence in the supplied profile. "
                    "Do not invent experience, skills, achievements, "
                    "or personal facts. The target bucket is a search "
                    "hint, not proof. If evidence is ambiguous, use "
                    "the most cautious classification. "
                    "Score relevance from 1 to 10 for practical AI "
                    "and software learning, and explain the score "
                    "in one concise line. Write a natural, specific "
                    "connection note under 300 characters. Write "
                    "a warm follow-up DM under 100 words that invites "
                    "the person to explore code2careerai.com. "
                    "Avoid exaggerated claims and spam-like language. "
                    "Do not claim a message has been sent."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Assess this publicly indexed profile and create "
                    "a personalized outreach draft:\n"
                    + str(profile_data)
                ),
            },
        ],
        response_format=OutreachPayload,
    )

    message = completion.choices[0].message

    if message.refusal:
        raise RuntimeError("The model refused this profile request.")

    if message.parsed is None:
        raise RuntimeError("The model returned no structured payload.")

    result = message.parsed.model_dump()
    result["generator"] = f"OpenAI Structured Outputs ({model})"

    # Validate again after assigning the generator.
    return OutreachPayload(**result).model_dump()


def score_profile(profile, use_llm=True):
    """
    Generate a structured outreach payload.
    Uses OpenAI when configured; falls back to local heuristics.
    """
    if not isinstance(profile, dict):
        profile = {}

    if use_llm and os.getenv("OPENAI_API_KEY", "").strip():
        try:
            return _llm_score(profile)

        except Exception as e:
            print("OPENAI ERROR:", repr(e), flush=True)

    return _fallback(profile)
