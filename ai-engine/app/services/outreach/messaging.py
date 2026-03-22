"""Outreach message generation via OpenAI."""

from openai import OpenAI

from app.core.config import get_settings


def generate_outreach_message(target_name: str, target_type: str, context: str = "") -> str:
    """Generate a short, human, non-salesy outreach message (max ~100 words)."""
    settings = get_settings()
    if not settings.openai_api_key:
        return (
            f"Hi {target_name}, we're {settings.label_name} — an independent collective "
            "making nu jazz, lo-fi, and experimental electronic music. We'd love to connect "
            "and share some tracks that might be a fit. No pressure at all — just genuine "
            "appreciation for what you do. Cheers!"
        )

    client = OpenAI(api_key=settings.openai_api_key)

    prompt = (
        "You are writing a short outreach message on behalf of an independent music label.\n"
        f"Label: {settings.label_name}\n"
        f"Genre: {settings.label_genre}\n"
        f"Target: {target_name} ({target_type})\n"
    )
    if context:
        prompt += f"Context: {context}\n"
    prompt += (
        "\nRules:\n"
        "- Human, respectful, non-salesy tone\n"
        "- Maximum 100 words\n"
        "- Mention something specific about their work if context is given\n"
        "- End with a soft call-to-action\n"
        "- Do NOT include a subject line, just the body\n"
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()
