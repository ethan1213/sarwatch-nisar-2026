import unittest
import numpy as np
from sarwatch.assistant.router import route, OUT_OF_SCOPE, load_examples
from sarwatch.assistant.verify import verify
from sarwatch.assistant.chat import answer
from sarwatch.interpretation import summarize


def context():
    return {"region": "Pantanal", "before": "2026-07-17", "after": "2026-09-27", "polarization": "HH", "statistics": summarize(np.array([-10., np.nan, -12.]), np.array([-9.5, -8., -11.])), "source": "https://cmr.earthdata.nasa.gov/search/concepts/G4327697742-ASF.umm_json"}


class Router(unittest.TestCase):
    def test_unseen_phrasings_route_to_expected_intents(self):
        cases = {"¿me puedes resumir qué cambió?": "resumen", "qué quiere decir el color naranja": "colores", "para qué sirve HV": "unidades", "¿esto tiene 99 % de precisión?": "calidad", "¿hubo inundaciones en esta zona?": "causa", "¿va a inundarse mañana?": "prediccion", "¿cuál es la fuente de los datos?": "fuentes", "¿cuántos km² de agua detectó el modelo?": "deteccion", "¿cómo bajo los datos en csv?": "uso", "¿cuántos gigas ocuparía todo Chile?": "tamano"}
        hits = sum(route(q)[0] == intent for q, intent in cases.items())
        self.assertGreaterEqual(hits, 9, {q: route(q)[0] for q in cases})

    def test_unrelated_question_is_out_of_scope(self):
        self.assertEqual(route("¿Quién ganó el partido de fútbol ayer?")[0], OUT_OF_SCOPE)
        self.assertEqual(route("")[0], OUT_OF_SCOPE)
        examples, _ = load_examples()
        self.assertGreater(len(examples), 150)


class Verification(unittest.TestCase):
    def test_numbers_must_trace_to_facts(self):
        facts = {"median_db": -0.52, "coverage": 0.9987}
        ok, problems = verify("La mediana fue -0,52 dB con 99,9 % de cobertura.", facts, [])
        self.assertTrue(ok, problems)
        ok, problems = verify("La mediana fue -3,1 dB.", facts, [])
        self.assertFalse(ok)
        ok, problems = verify("Se confirma la inundación en la zona.", facts, [])
        self.assertFalse(ok)
        ok, problems = verify("Ver https://ejemplo.org/x", facts, ["https://otra.org"])
        self.assertFalse(ok)


class FakeInventingGenerator:
    name = "falso"

    def generate(self, evidence, question, profile):
        return "Hubo una inundación confirmada con 87,3 % de probabilidad."


class Chat(unittest.TestCase):
    def test_prediction_and_unknown_keep_honest_phrases(self):
        result = answer("¿Puedes predecir una inundación mañana?", context())
        self.assertEqual(result.intent, "prediccion")
        self.assertIn("Todavía no podemos predecir", result.text)
        self.assertTrue(result.verified, result.problems)
        unknown = answer("¿Quién ganó el partido?", context())
        self.assertIn("No tengo evidencia", unknown.text)

    def test_invented_numbers_fall_back_to_rules(self):
        result = answer("¿Es una inundación?", context(), generator=FakeInventingGenerator())
        self.assertEqual(result.generator, "reglas")
        self.assertNotIn("87,3", result.text)
        self.assertTrue(any("sin respaldo" in p or "no permitida" in p for p in result.problems))

    def test_summary_numbers_come_from_statistics(self):
        result = answer("Resume el cambio", context())
        self.assertEqual(result.intent, "resumen")
        self.assertIn("+0.75 dB", result.text)
        self.assertTrue(result.verified, result.problems)
        self.assertIn(context()["source"], result.sources)

    def test_glossary_term(self):
        result = answer("¿Qué es Otsu?", context())
        self.assertEqual(result.intent, "glosario")
        self.assertIn("umbral", result.text.lower())


if __name__ == "__main__":
    unittest.main()
