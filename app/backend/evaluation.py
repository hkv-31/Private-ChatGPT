def evaluate(answer: str, expected_terms: list[str]) -> dict:
    low = answer.lower()
    hits = sum(term.lower() in low for term in expected_terms)
    return {"term_recall": hits / len(expected_terms) if expected_terms else 1.0, "matched": hits}
