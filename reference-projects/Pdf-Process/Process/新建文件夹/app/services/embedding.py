_model=None
def embed(texts):
    global _model
    if not texts: return []
    try:
        from sentence_transformers import SentenceTransformer
        if _model is None: _model=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        return _model.encode(texts, normalize_embeddings=True).tolist()
    except Exception: return [None for _ in texts]
