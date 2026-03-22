"""AI-powered media tagging via OpenAI."""

import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings


def tag_media(title: str, description: str = "") -> dict[str, Any]:
    """Use OpenAI to generate tags, mood, and style for a media asset.

    Returns {"tags": [...], "mood": "...", "style": "..."}.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return {"tags": [], "mood": "unknown", "style": "unknown"}

    client = OpenAI(api_key=settings.openai_api_key)

    prompt = (
        "You are a media tagging assistant for a music label that specialises in "
        "nu jazz, lo-fi, and experimental electronic music.\n\n"
        f"Title: {title}\n"
    )
    if description:
        prompt += f"Description: {description}\n"

    prompt += (
        "\nReturn a JSON object with exactly these keys:\n"
        '  "tags": a list of 5-10 descriptive keyword tags\n'
        '  "mood": a single-word mood (e.g. dreamy, energetic, melancholic)\n'
        '  "style": a short style descriptor (e.g. retro sci-fi, urban night)\n'
        "Return ONLY the JSON object, no markdown fences."
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=300,
    )

    text = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model includes them anyway
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"tags": [], "mood": "unknown", "style": "unknown"}

    return result
