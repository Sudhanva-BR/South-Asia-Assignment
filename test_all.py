"""
Comprehensive test script for the Source Asia backend assignment.
Tests Part 1 (Rate Limiting) and Part 2 (Product Catalog).
"""
import urllib.request
import urllib.error
import json
import sys

BASE = "http://127.0.0.1:8000"

passed = 0
failed = 0

def req(method, path, body=None):
    """Make an HTTP request and return (status_code, parsed_json_body)."""
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} -- {detail}")
        failed += 1

# ============================================================
# PART 1 — Rate-Limited API
# ============================================================
print("\n" + "=" * 60)
print("PART 1: Rate-Limited API")
print("=" * 60)

# --- 1.1  POST /request — valid request ---
print("\n--- 1.1 POST /request (valid) ---")
status, body = req("POST", "/request", {"user_id": "testA", "payload": "hello"})
test("Returns 201", status == 201, f"got {status}")
test("Body has status=accepted", body.get("status") == "accepted", str(body))
test("Body has user_id", body.get("user_id") == "testA", str(body))

# --- 1.2  Validation: missing user_id ---
print("\n--- 1.2 Validation: missing user_id ---")
status, body = req("POST", "/request", {"payload": "hello"})
test("Returns 400", status == 400, f"got {status}")
test("Has error message", "error" in body, str(body))

# --- 1.3  Validation: empty user_id ---
print("\n--- 1.3 Validation: empty user_id ---")
status, body = req("POST", "/request", {"user_id": "", "payload": "hello"})
test("Returns 400", status == 400, f"got {status}")

# --- 1.4  Validation: whitespace-only user_id ---
print("\n--- 1.4 Validation: whitespace user_id ---")
status, body = req("POST", "/request", {"user_id": "   ", "payload": "hello"})
test("Returns 400", status == 400, f"got {status}")

# --- 1.5  Validation: missing payload ---
print("\n--- 1.5 Validation: missing payload ---")
status, body = req("POST", "/request", {"user_id": "testA"})
test("Returns 400", status == 400, f"got {status}")

# --- 1.6  Validation: invalid JSON ---
print("\n--- 1.6 Validation: invalid JSON ---")
url = BASE + "/request"
r = urllib.request.Request(url, data=b"not json", method="POST")
r.add_header("Content-Type", "application/json")
try:
    resp = urllib.request.urlopen(r)
    status = resp.status
    body = json.loads(resp.read())
except urllib.error.HTTPError as e:
    status = e.code
    body = json.loads(e.read())
test("Returns 400 for bad JSON", status == 400, f"got {status}")

# --- 1.7  Validation: non-string user_id ---
print("\n--- 1.7 Validation: numeric user_id ---")
status, body = req("POST", "/request", {"user_id": 123, "payload": "hello"})
test("Returns 400", status == 400, f"got {status}")

# --- 1.8  Rate limiting: 5 accepts then reject ---
print("\n--- 1.8 Rate limiting (5 accept, 6th reject) ---")
# Use a fresh user
accept_count = 0
reject_count = 0
for i in range(7):
    status, body = req("POST", "/request", {"user_id": "ratelimit_user", "payload": f"req{i}"})
    if status == 201:
        accept_count += 1
    elif status == 429:
        reject_count += 1
test("Exactly 5 accepted", accept_count == 5, f"got {accept_count}")
test("At least 2 rejected (429)", reject_count >= 2, f"got {reject_count}")

# Verify 429 body has error message
status, body = req("POST", "/request", {"user_id": "ratelimit_user", "payload": "extra"})
test("429 body has error key", "error" in body, str(body))

# --- 1.9  GET /stats ---
print("\n--- 1.9 GET /stats ---")
status, body = req("GET", "/stats")
test("Returns 200", status == 200, f"got {status}")
test("Has stats array", "stats" in body, str(body))
# Check ratelimit_user stats
rl_stats = [s for s in body["stats"] if s["user_id"] == "ratelimit_user"]
test("ratelimit_user in stats", len(rl_stats) == 1, str(body))
if rl_stats:
    test("accepted_current_window == 5", rl_stats[0].get("accepted_current_window") == 5, str(rl_stats[0]))
    test("rejected_cumulative >= 3", rl_stats[0].get("rejected_cumulative", 0) >= 3, str(rl_stats[0]))

# --- 1.10  Payload can be any JSON value ---
print("\n--- 1.10 Payload can be any JSON value ---")
status, _ = req("POST", "/request", {"user_id": "typetest1", "payload": 42})
test("payload=number accepted", status == 201, f"got {status}")
status, _ = req("POST", "/request", {"user_id": "typetest2", "payload": [1, 2, 3]})
test("payload=array accepted", status == 201, f"got {status}")
status, _ = req("POST", "/request", {"user_id": "typetest3", "payload": None})
test("payload=null accepted", status == 201, f"got {status}")
status, _ = req("POST", "/request", {"user_id": "typetest4", "payload": True})
test("payload=boolean accepted", status == 201, f"got {status}")

# ============================================================
# PART 2 — Product Catalog
# ============================================================
print("\n" + "=" * 60)
print("PART 2: Product Catalog")
print("=" * 60)

# --- 2.1  POST /products — create product ---
print("\n--- 2.1 POST /products (create) ---")
status, body = req("POST", "/products", {
    "name": "Widget A",
    "sku": "SKU-001",
    "image_urls": [
        "https://cdn.example.com/products/sku-001/img-1.jpg",
        "https://cdn.example.com/products/sku-001/img-2.jpg"
    ],
    "video_urls": [
        "https://cdn.example.com/products/sku-001/demo.mp4"
    ]
})
test("Returns 201", status == 201, f"got {status}")
test("Has id", "id" in body, str(body))
test("Has name", body.get("name") == "Widget A", str(body))
test("Has sku", body.get("sku") == "SKU-001", str(body))
test("Has image_urls", len(body.get("image_urls", [])) == 2, str(body))
test("Has video_urls", len(body.get("video_urls", [])) == 1, str(body))
test("Has created_at", "created_at" in body, str(body))
product_id = body.get("id")

# --- 2.2  Duplicate SKU ---
print("\n--- 2.2 Duplicate SKU ---")
status, body = req("POST", "/products", {"name": "Widget B", "sku": "SKU-001"})
test("Returns 409 Conflict", status == 409, f"got {status}")
test("Has error message", "error" in body, str(body))

# --- 2.3  Validation: empty name ---
print("\n--- 2.3 Validation: empty name ---")
status, body = req("POST", "/products", {"name": "", "sku": "SKU-X"})
test("Returns 400", status == 400, f"got {status}")

# --- 2.4  Validation: missing sku ---
print("\n--- 2.4 Validation: missing sku ---")
status, body = req("POST", "/products", {"name": "Test"})
test("Returns 400", status == 400, f"got {status}")

# --- 2.5  Validation: invalid URL ---
print("\n--- 2.5 Validation: invalid URL ---")
status, body = req("POST", "/products", {
    "name": "Bad URL Product",
    "sku": "SKU-BAD",
    "image_urls": ["ftp://bad.example.com/img.jpg"]
})
test("Returns 400 for non-http URL", status == 400, f"got {status}")

# --- 2.6  Validation: too many URLs ---
print("\n--- 2.6 Validation: >20 URLs ---")
urls = [f"https://cdn.example.com/img-{i}.jpg" for i in range(25)]
status, body = req("POST", "/products", {
    "name": "Too Many URLs",
    "sku": "SKU-MANY",
    "image_urls": urls
})
test("Returns 400 for >20 URLs", status == 400, f"got {status}")

# --- 2.7  Create product without media ---
print("\n--- 2.7 Create product without media ---")
status, body = req("POST", "/products", {"name": "No Media Product", "sku": "SKU-NOMEDIA"})
test("Returns 201", status == 201, f"got {status}")
test("image_urls is empty", body.get("image_urls", []) == [], str(body))
test("video_urls is empty", body.get("video_urls", []) == [], str(body))

# --- 2.8  GET /products (list) ---
print("\n--- 2.8 GET /products (list) ---")
status, body = req("GET", "/products")
test("Returns 200", status == 200, f"got {status}")
test("Has total count", "total" in body, str(body))
test("Has products array", "products" in body, str(body))
test("Has pagination: limit", "limit" in body, str(body))
test("Has pagination: offset", "offset" in body, str(body))
# Check that list items do NOT have full image_urls/video_urls
if body.get("products"):
    first = body["products"][0]
    test("List item has id", "id" in first, str(first))
    test("List item has name", "name" in first, str(first))
    test("List item has sku", "sku" in first, str(first))
    test("List item has image_count", "image_count" in first, str(first))
    test("List item has video_count", "video_count" in first, str(first))
    test("List item does NOT have image_urls", "image_urls" not in first, f"LEAK: image_urls found: {first}")
    test("List item does NOT have video_urls", "video_urls" not in first, f"LEAK: video_urls found: {first}")

# --- 2.9  GET /products with pagination ---
print("\n--- 2.9 GET /products?limit=1&offset=0 ---")
status, body = req("GET", "/products?limit=1&offset=0")
test("Returns 200", status == 200, f"got {status}")
test("Returns exactly 1 product", len(body.get("products", [])) == 1, f"got {len(body.get('products', []))}")
test("Total is >= 2", body.get("total", 0) >= 2, f"total={body.get('total')}")

# --- 2.10  GET /products/{id} (detail) ---
print("\n--- 2.10 GET /products/{id} (detail) ---")
status, body = req("GET", f"/products/{product_id}")
test("Returns 200", status == 200, f"got {status}")
test("Has full image_urls", "image_urls" in body, str(body))
test("Has full video_urls", "video_urls" in body, str(body))
test("image_urls has 2 items", len(body.get("image_urls", [])) == 2, str(body))
test("video_urls has 1 item", len(body.get("video_urls", [])) == 1, str(body))

# --- 2.11  GET /products/{id} — not found ---
print("\n--- 2.11 GET /products/nonexistent ---")
status, body = req("GET", "/products/nonexistent-id")
test("Returns 404", status == 404, f"got {status}")

# --- 2.12  POST /products/{id}/media ---
print("\n--- 2.12 POST /products/{id}/media ---")
status, body = req("POST", f"/products/{product_id}/media", {
    "image_urls": ["https://cdn.example.com/products/sku-001/img-3.jpg"],
    "video_urls": ["https://cdn.example.com/products/sku-001/demo2.mp4"]
})
test("Returns 200", status == 200, f"got {status}")
test("image_urls now has 3", len(body.get("image_urls", [])) == 3, str(body))
test("video_urls now has 2", len(body.get("video_urls", [])) == 2, str(body))

# --- 2.13  POST /products/{id}/media — empty body ---
print("\n--- 2.13 POST /products/{id}/media (empty) ---")
status, body = req("POST", f"/products/{product_id}/media", {})
test("Returns 400 for empty media", status == 400, f"got {status}")

# --- 2.14  POST /products/{id}/media — not found ---
print("\n--- 2.14 POST /products/bad-id/media ---")
status, body = req("POST", "/products/bad-id/media", {
    "image_urls": ["https://cdn.example.com/img.jpg"]
})
test("Returns 404", status == 404, f"got {status}")

# --- 2.15  Validate URL length ---
print("\n--- 2.15 URL max length validation ---")
long_url = "https://cdn.example.com/" + "a" * 2050
status, body = req("POST", "/products", {
    "name": "Long URL Product",
    "sku": "SKU-LONGURL",
    "image_urls": [long_url]
})
test("Returns 400 for URL > 2048 chars", status == 400, f"got {status}")

# --- 2.16  Pagination edge: bad limit ---
print("\n--- 2.16 Pagination: invalid limit ---")
status, body = req("GET", "/products?limit=0")
test("Returns 400 for limit=0", status == 400, f"got {status}")
status, body = req("GET", "/products?limit=200")
test("Returns 400 for limit>100", status == 400, f"got {status}")

# --- 2.17  Pagination: negative offset ---
print("\n--- 2.17 Pagination: negative offset ---")
status, body = req("GET", "/products?offset=-1")
test("Returns 400 for negative offset", status == 400, f"got {status}")

# --- 2.18  POST /products/{id}/media — invalid URL ---
print("\n--- 2.18 Media append: invalid URL ---")
status, body = req("POST", f"/products/{product_id}/media", {
    "image_urls": ["not-a-url"]
})
test("Returns 400", status == 400, f"got {status}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
print("=" * 60)
if failed:
    sys.exit(1)
