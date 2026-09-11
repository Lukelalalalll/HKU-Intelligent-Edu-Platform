from __future__ import annotations

def build_chunks(pages, document_id=None, source_file=None):
    chunks = []
    for page in pages:
        number = page.get('page', page.get('slide_number', 0))
        section = page.get('section')
        title = page.get('title') or section
        for block in page.get('blocks', []):
            typ = block.get('type', 'text')
            text = (block.get('markdown') or block.get('text') or block.get('latex') or '').strip()
            if not text:
                continue
            if typ in ('title', 'heading'):
                section = text[:512]
                title = title or section
            metadata = {
                'bbox': block.get('bbox'), 'bbox_raw': block.get('bbox_raw'),
                'block_id': block.get('id'), 'source': block.get('source'),
                'latex': block.get('latex'), 'confidence': block.get('confidence', 0.0),
                'needs_visual_verification': bool(block.get('needs_visual_verification')),
                'slide_number': page.get('slide_number'), 'title': title,
                'source_file': source_file,
            }
            chunks.append({
                'document_id': document_id, 'page': number,
                'slide_number': page.get('slide_number'), 'section': section,
                'title': title, 'chunk_type': typ, 'content': text,
                'bbox': block.get('bbox'), 'confidence': block.get('confidence', 0.0),
                'metadata': metadata,
            })
    return chunks
