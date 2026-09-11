def enrich_formula(text: str|None, confidence: float|None=None):
    return {'latex': text or '', 'confidence': confidence if confidence is not None else 0.0, 'source':'mineru'}
