"""Optional local CLIP/FAISS reranking. Keyword ranking remains the zero-install fallback."""
from __future__ import annotations

from typing import Any


def rerank(assets: list[dict[str, Any]], text: str, model_name: str = "") -> list[dict[str, Any]]:
    if not model_name or len(assets) < 2:
        return assets
    try:
        import faiss  # type: ignore
        import torch  # type: ignore
        from PIL import Image  # type: ignore
        from transformers import CLIPModel, CLIPProcessor  # type: ignore
    except Exception:
        return assets
    try:
        model = CLIPModel.from_pretrained(model_name, local_files_only=True)
        processor = CLIPProcessor.from_pretrained(model_name, local_files_only=True)
        images = [Image.open(item["asset_path"]).convert("RGB") for item in assets if item.get("asset_path")]
        usable = [item for item in assets if item.get("asset_path")]
        if not images:
            return assets
        with torch.no_grad():
            inputs = processor(text=[text], images=images, return_tensors="pt", padding=True)
            text_vec = model.get_text_features(input_ids=inputs["input_ids"], attention_mask=inputs.get("attention_mask")); image_vec = model.get_image_features(pixel_values=inputs["pixel_values"])
            text_vec = torch.nn.functional.normalize(text_vec, dim=-1).cpu().numpy(); image_vec = torch.nn.functional.normalize(image_vec, dim=-1).cpu().numpy()
        index = faiss.IndexFlatIP(image_vec.shape[1]); index.add(image_vec); scores, ids = index.search(text_vec, len(usable))
        by_id = {id(item): item for item in usable}; ranked = []
        for score, idx in zip(scores[0], ids[0]):
            item = dict(by_id[id(usable[idx])]); item["clip_score"] = float(score); item["score"] = round(float(item.get("score") or 0) * .35 + float(score) * .65, 4); ranked.append(item)
        ranked.extend(item for item in assets if not item.get("asset_path")); return ranked
    except Exception:
        return assets
