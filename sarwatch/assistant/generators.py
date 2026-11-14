"""Answer generators. RuleGenerator is deterministic; OllamaGenerator is optional, local and verified afterwards.

Hook point for other providers: implement `generate(evidence, question, profile) -> str`. By decision of
the project owner no hosted LLM API is wired here.
"""
import json
import os
from urllib.request import Request, urlopen

PROFILE_STYLE = {
    "Público general": "Explica en frases cortas y sin jerga; di qué se observa, qué podría significar y qué falta saber.",
    "Ciencia": "Sé preciso con unidades, máscaras y métricas; distingue observación, hipótesis y dato ausente.",
    "Desarrollo y datos": "Indica archivos, formatos y pasos reproducibles cuando corresponda.",
    "Comunicaciones": "Redacta de forma responsable: qué se puede afirmar y qué no; evita «inundación detectada».",
    "Gestión territorial": "Orienta qué revisar en terreno y con quién contrastar; no es alerta operativa.",
}


class RuleGenerator:
    name = "reglas"

    def generate(self, evidence, question, profile):
        parts = [e["text"] for e in evidence["tools"] if e.get("text")]
        text = " ".join(parts).strip()
        if evidence["intent"] in ("causa", "prediccion"):
            text += " Observación: cambio de la señal radar entre las fechas indicadas. Hipótesis: causas físicas posibles sin confirmar. Dato ausente: evidencia independiente contemporánea."
        return text


class OllamaGenerator:
    name = "ollama"

    def __init__(self, host=None, model=None, timeout=25):
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or os.environ.get("ASSISTANT_MODEL", "qwen3:4b-instruct")
        self.timeout = timeout

    def available(self):
        try:
            with urlopen(self.host + "/api/tags", timeout=3) as response:
                tags = json.load(response)
            return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in tags.get("models", []))
        except Exception:
            return False

    def generate(self, evidence, question, profile):
        system = ("Eres el asistente de SARWatch, un visor de observaciones del radar NISAR. Responde en español, en menos de 120 palabras. "
                  "Usa EXCLUSIVAMENTE los hechos y textos de la evidencia JSON; no inventes cifras, fechas ni fuentes. "
                  "Si la evidencia no contiene la respuesta, di que no tienes evidencia. Nunca afirmes una inundación o daño confirmado ni des probabilidades de riesgo. "
                  "Separa observación, hipótesis y dato ausente cuando corresponda. " + PROFILE_STYLE.get(profile, ""))
        payload = {"model": self.model, "stream": False, "options": {"temperature": 0.2, "num_predict": 300}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": "Evidencia:\n" + json.dumps(evidence, ensure_ascii=False) + "\n\nPregunta: " + question}]}
        request = Request(self.host + "/api/chat", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:
            body = json.load(response)
        return body["message"]["content"].strip()


def select_generator():
    mode = os.environ.get("ASSISTANT_LLM", "none").lower()
    if mode == "ollama":
        candidate = OllamaGenerator()
        if candidate.available():
            return candidate
    return RuleGenerator()
