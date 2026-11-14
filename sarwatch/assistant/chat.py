"""Orchestration: question -> intent -> tools -> evidence -> generation -> verification -> answer."""
from dataclasses import dataclass, field

from sarwatch.assistant import tools
from sarwatch.assistant.generators import RuleGenerator, select_generator
from sarwatch.assistant.retriever import search
from sarwatch.assistant.router import OUT_OF_SCOPE, route
from sarwatch.assistant.verify import verify

INTENT_TOOLS = {
    "resumen": [tools.tool_statistics],
    "colores": [tools.tool_colors],
    "unidades": [tools.tool_units],
    "calidad": [tools.tool_quality],
    "causa": [tools.tool_cause, tools.tool_statistics],
    "prediccion": [tools.tool_forecast],
    "fuentes": [tools.tool_sources],
    "deteccion": [tools.tool_detection],
    "postfuego": [tools.tool_postfire],
    "uso": [tools.tool_usage],
    "tamano": [tools.tool_storage],
    "glosario": [],
}
OUT_OF_SCOPE_TEXT = "Puedo explicar este par de observaciones, sus colores, HH/HV, calidad, agua o cambio detectados y los límites de predicción. No tengo evidencia para responder esa pregunta fuera de esos temas. Prueba «Resume el cambio» o «¿Qué significan los colores?»."


@dataclass
class Answer:
    text: str
    sources: list
    intent: str
    confidence: float
    generator: str
    verified: bool
    problems: list = field(default_factory=list)
    snippets: list = field(default_factory=list)


def gather_evidence(question, context, intent):
    results = [fn(context) for fn in INTENT_TOOLS.get(intent, [])]
    if intent == "glosario":
        results.append(tools.tool_glossary(question))
    snippets = search(question, k=2)
    facts = {}
    sources = []
    for r in results:
        facts.update(r["facts"])
        sources.extend(s for s in r["sources"] if s not in sources)
    for s in snippets:
        if s["source"] not in sources:
            sources.append(s["source"])
    return {"intent": intent, "tools": results, "facts": facts, "sources": sources, "snippets": [s["text"][:400] for s in snippets]}


def answer(question, context, profile="Público general", generator=None):
    intent, confidence, _ = route(question)
    if intent == OUT_OF_SCOPE:
        return Answer(OUT_OF_SCOPE_TEXT, [context["source"]], intent, confidence, "reglas", True)
    evidence = gather_evidence(question, context, intent)
    if intent == "glosario" and not any(r["text"] for r in evidence["tools"]):
        return Answer("No tengo ese término en el glosario del proyecto. " + OUT_OF_SCOPE_TEXT, [context["source"]], intent, confidence, "reglas", True)
    rule = RuleGenerator()
    generator = generator or select_generator()
    text = rule.generate(evidence, question, profile)
    used = rule.name
    problems = []
    publishable = bool(evidence["facts"].get("published_model"))
    if generator.name != rule.name:
        try:
            candidate = generator.generate(evidence, question, profile)
            ok, problems = verify(candidate, evidence["facts"], evidence["sources"], publishable)
            if ok and candidate:
                text, used = candidate, generator.name
        except Exception as exc:  # the local model is optional; rules always answer
            problems = [f"generador no disponible: {type(exc).__name__}"]
    verified, rule_problems = verify(text, evidence["facts"], evidence["sources"], publishable)
    return Answer(text, evidence["sources"], intent, confidence, used, verified, problems + rule_problems, evidence["snippets"])
