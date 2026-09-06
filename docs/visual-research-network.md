# Visual research network and deployment

The visual step queries Wikimedia Commons from the backend, downloads the selected candidate pool, and serves cached files through the authenticated `/api/ppt/projects/{project_id}/assets/*` route. The browser never needs to call a public image host.

GitHub cloning and first-time model downloads may require a mainland development proxy/VPN. A Hong Kong school deployment should use an allowlisted HTTPS egress proxy or scheduled cache synchronization; teachers and browsers do not need a VPN. Set `CLIP_MODEL_NAME` only after the corresponding model is present in the local Hugging Face cache. Without optional visual dependencies or a model cache, deterministic keyword scoring remains active.
