import threading
import uuid
import re
from datetime import datetime, timezone

_lock = threading.Lock()

# id -> product dict (without full media arrays for list performance)
_products: dict[str, dict] = {}

# sku -> id (for uniqueness checks)
_sku_index: dict[str, str] = {}

# id -> {"image_urls": [...], "video_urls": [...]}
_media: dict[str, dict] = {}

MAX_URL_LENGTH = 2048
MAX_URLS_PER_REQUEST = 20
URL_PATTERN = re.compile(r'^https?://.{1,}$')


def _validate_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    if len(url) > MAX_URL_LENGTH:
        return False
    return bool(URL_PATTERN.match(url))


def validate_urls(urls: list) -> tuple[bool, str]:
    if not isinstance(urls, list):
        return False, "URLs must be an array."
    if len(urls) > MAX_URLS_PER_REQUEST:
        return False, f"Maximum {MAX_URLS_PER_REQUEST} URLs per request."
    for url in urls:
        if not _validate_url(url):
            return False, f"Invalid URL: '{url}'. Must be http/https and under {MAX_URL_LENGTH} chars."
    return True, ""


def create_product(name: str, sku: str, image_urls: list, video_urls: list) -> tuple[dict | None, str, int]:
    """Returns (product, error_msg, status_code)"""
    with _lock:
        if sku in _sku_index:
            return None, f"SKU '{sku}' already exists.", 409

        product_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        product = {
            "id": product_id,
            "name": name,
            "sku": sku,
            "image_count": len(image_urls),
            "video_count": len(video_urls),
            "thumbnail_url": image_urls[0] if image_urls else None,
            "created_at": now,
        }

        _products[product_id] = product
        _sku_index[sku] = product_id
        _media[product_id] = {
            "image_urls": list(image_urls),
            "video_urls": list(video_urls),
        }

        # Return full product for create response
        full = {**product, **_media[product_id]}
        return full, "", 201


def list_products(limit: int, offset: int) -> tuple[list, int]:
    """Returns (list of lightweight product dicts, total_count). Does NOT load media arrays."""
    with _lock:
        all_products = list(_products.values())
        total = len(all_products)
        page = all_products[offset: offset + limit]
        # Each item is the lightweight dict only — no image_urls/video_urls
        return [dict(p) for p in page], total


def get_product(product_id: str) -> dict | None:
    """Returns full product with all media, or None."""
    with _lock:
        product = _products.get(product_id)
        if not product:
            return None
        media = _media.get(product_id, {"image_urls": [], "video_urls": []})
        return {**product, **media}


def append_media(product_id: str, image_urls: list, video_urls: list) -> tuple[dict | None, str]:
    """Appends URLs to existing product. Returns (updated full product, error)."""
    with _lock:
        if product_id not in _products:
            return None, "Product not found."

        _media[product_id]["image_urls"].extend(image_urls)
        _media[product_id]["video_urls"].extend(video_urls)

        # Update counts and thumbnail
        _products[product_id]["image_count"] = len(_media[product_id]["image_urls"])
        _products[product_id]["video_count"] = len(_media[product_id]["video_urls"])
        if not _products[product_id]["thumbnail_url"] and _media[product_id]["image_urls"]:
            _products[product_id]["thumbnail_url"] = _media[product_id]["image_urls"][0]

        full = {**_products[product_id], **_media[product_id]}
        return full, ""