"""Output verification: every number must trace to tool facts; every link to known sources; no banned claims."""
import re

NUMBER = re.compile(r"(?<![\w/])[-−+]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?(?![\w/])")
URL = re.compile(r"https?://\S+")
BANNED = ["inundación confirmada", "inundacion confirmada", "detectamos una inundación", "se confirma la inundación", "daño confirmado", "alerta de inundación", "99,9 % de precisión", "99.9 % de precisión", "probabilidad de inundación", "predecimos", "pronosticamos que habrá"]
# Tokens that look numeric but are part of names, units or dates and are always allowed.
ALLOWED_TOKENS = {"10", "2026", "12", "20", "30", "6", "0", "1", "2"}


def _to_float(token):
    token = token.replace("−", "-").strip()
    if "," in token and "." in token:
        token = token.replace(".", "").replace(",", ".")
    elif "," in token:
        token = token.replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def _fact_values(facts):
    values = set()

    def visit(value):
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            values.add(float(value))
            values.add(round(float(value), 1))
            values.add(round(float(value), 2))
            values.add(float(int(value)))
            if 0 <= float(value) <= 1:
                values.add(round(100 * float(value), 1))
                values.add(round(100 * float(value), 2))
        elif isinstance(value, dict):
            for v in value.values():
                visit(v)
        elif isinstance(value, (list, tuple, set)):
            for v in value:
                visit(v)
        elif isinstance(value, str):
            for token in NUMBER.findall(value):
                f = _to_float(token)
                if f is not None:
                    values.add(f)

    visit(facts)
    return values


def verify(text, facts, sources, forecast_publishable=False):
    """Return (ok, problems). Dates inside sources/facts strings are allowed implicitly."""
    problems = []
    lowered = text.lower()
    for phrase in BANNED:
        if phrase in lowered and not (forecast_publishable and phrase in ("predecimos",)):
            problems.append(f"afirmación no permitida: «{phrase}»")
    allowed = _fact_values(facts)
    for token in NUMBER.findall(text):
        clean = token.replace("−", "-")
        if clean in ALLOWED_TOKENS or re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean):
            continue
        value = _to_float(clean)
        if value is None:
            continue
        if not any(abs(value - a) <= 1e-6 or (a != 0 and abs(value - a) / abs(a) < 0.002) for a in allowed):
            problems.append(f"número sin respaldo en la evidencia: {token}")
    for url in URL.findall(text):
        trimmed = url.rstrip(".,;)")
        if trimmed not in set(sources):
            problems.append(f"enlace no citado en las fuentes: {trimmed}")
    return (not problems), problems
