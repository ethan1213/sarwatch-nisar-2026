"""Local, evidence-bound assistant: intent router -> tools -> evidence -> optional local LLM -> verification.

Numbers are produced by tools, never by language models. If a generated answer contains a number or a
citation that cannot be traced to the evidence, the deterministic rule answer is returned instead.
No external API is called; an optional Ollama server on the host may be used when ASSISTANT_LLM=ollama.
"""
