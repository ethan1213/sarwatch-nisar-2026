"""Intent routing with a small supervised text classifier trained from catalog/assistant_intents.json."""
import json
import unicodedata
from functools import lru_cache
from pathlib import Path

INTENTS_PATH = Path("catalog/assistant_intents.json")
OUT_OF_SCOPE = "fuera_de_alcance"
MIN_CONFIDENCE = 0.30


def normalize(text):
    text = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def load_examples(path=INTENTS_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    examples = [(normalize(q), intent) for intent, questions in data["intents"].items() for q in questions]
    if len({i for _, i in examples}) < 2:
        raise ValueError("Se requieren al menos dos intenciones")
    return examples, data


@lru_cache(maxsize=1)
def _model(path=str(INTENTS_PATH)):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    examples, _ = load_examples(path)
    texts = [t for t, _ in examples]
    labels = [i for _, i in examples]
    pipeline = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1, sublinear_tf=True), LogisticRegression(C=8.0, max_iter=2000))
    pipeline.fit(texts, labels)
    return pipeline


def route(question, path=str(INTENTS_PATH), min_confidence=MIN_CONFIDENCE):
    """Return (intent, confidence, alternatives). Low confidence maps to OUT_OF_SCOPE."""
    text = normalize(question)
    if not text:
        return OUT_OF_SCOPE, 0.0, []
    model = _model(path)
    probabilities = model.predict_proba([text])[0]
    classes = list(model.classes_)
    ranked = sorted(zip(probabilities, classes), reverse=True)
    confidence, intent = float(ranked[0][0]), ranked[0][1]
    if confidence < min_confidence:
        return OUT_OF_SCOPE, confidence, [(c, float(p)) for p, c in ranked[:3]]
    return intent, confidence, [(c, float(p)) for p, c in ranked[:3]]
