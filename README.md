# Source Asia — Backend Assignment

A single Django HTTP service implementing **rate-limited request handling** (Part 1) and a **product catalog with media** (Part 2). All data is stored in-memory using thread-safe Python data structures.

> **Language note:** The assignment recommends Go or Node.js. I chose **Python + Django REST Framework** because it is my strongest backend stack and allowed me to deliver a clean, well-structured solution within the deadline. The core concepts (in-memory stores, concurrency safety via locks, REST API design) are language-agnostic.

> **AI tools:** AI coding assistants were used for code review and generating test scripts.

---

## Quick Start

### Prerequisites
- Python 3.10+

### Install & Run

```bash
# Clone the repository
git clone https://github.com/Sudhanva-BR/South-Asia-Assignment.git
cd South-Asia-Assignment

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python manage.py runserver 8000
```

The server starts at **http://127.0.0.1:8000**.

---

## Part 1 — Rate-Limited API

### Endpoints

#### `POST /request`

Accepts a user request if the user has not exceeded the rate limit.

**Request body (JSON):**
```json
{
  "user_id": "string (required, non-empty)",
  "payload": "any JSON value (required)"
}
```

**Success — `201 Created`:**
```json
{
  "status": "accepted",
  "message": "Request accepted successfully.",
  "user_id": "user1"
}
```

**Rate limited — `429 Too Many Requests`:**
```json
{
  "error": "Rate limit exceeded. Maximum 5 requests per minute.",
  "user_id": "user1"
}
```

**Validation errors — `400 Bad Request`:**
```json
{
  "error": "user_id is required and must be a non-empty string."
}
```

Validation rules:
- `user_id` must be present, a string, and non-empty (whitespace-only is rejected)
- `payload` key must be present (any JSON value is accepted: string, number, object, array, null, boolean)
- Request body must be valid JSON

---

#### `GET /stats`

Returns per-user statistics.

**Response — `200 OK`:**
```json
{
  "stats": [
    {
      "user_id": "user1",
      "accepted_current_window": 5,
      "rejected_cumulative": 3
    }
  ],
  "description": {
    "accepted_current_window": "Number of accepted requests in the current 60-second rolling window.",
    "rejected_cumulative": "Total rejected requests since server start (cumulative)."
  }
}
```

| Field | Description |
|---|---|
| `accepted_current_window` | Accepted requests in the current 60-second rolling window (per user) |
| `rejected_cumulative` | Total rejected requests since server start — cumulative, not per-window |

---

### Rate Limiting Approach

- **Rolling window** using a deque of timestamps per `user_id`
- Maximum **5 accepted requests per user per 60-second rolling window**
- On each request, timestamps older than 60 seconds are pruned; if fewer than 5 remain, the request is accepted and the current timestamp is appended
- **Concurrency safety:** A single `threading.Lock` protects all reads and writes to the shared data structures, ensuring correctness under parallel requests for the same `user_id`
- When the limit is exceeded: **429 Too Many Requests** with a JSON error message

---

### Example curl Commands (Part 1)

```bash
# Accept a request
curl -X POST http://127.0.0.1:8000/request \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "payload": "hello"}'

# Send 6 rapid requests (6th will be rejected)
for i in $(seq 1 6); do
  curl -s -X POST http://127.0.0.1:8000/request \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"user1\", \"payload\": \"req-$i\"}"
  echo
done

# Check stats
curl http://127.0.0.1:8000/stats
```

---

### Production Limitations (Part 1)

| Limitation | Detail |
|---|---|
| **Single instance only** | The in-memory store is local to one process. Horizontal scaling would require a shared store (e.g., Redis) |
| **Restart loses state** | All accepted/rejected counts are lost on server restart |
| **Single lock** | The global lock serializes all rate-limit checks. Under very high concurrency, per-user locks or a lock-free approach (e.g., Redis `INCR` + `EXPIRE`) would be more scalable |
| **No persistence** | No recovery after crashes; production would need Redis or a database-backed rate limiter |

---

## Part 2 — Product Catalog with Media

### Data Model

Products and media are stored in **separate in-memory dictionaries**:

```
_products: dict[str, dict]     # id → lightweight product (no media arrays)
_sku_index: dict[str, str]     # sku → id (for O(1) uniqueness checks)
_media: dict[str, dict]        # id → {"image_urls": [...], "video_urls": [...]}
```

**Why separate?** The list endpoint (`GET /products`) iterates only over `_products`, which contains `image_count` and `video_count` as integers — it never touches `_media`. This means listing 20 products out of 1,000 (each with 10 images) does **not** load or serialize any of the 10,000 URLs.

The detail endpoint (`GET /products/{id}`) merges both dictionaries to return the full product.

**Thread safety:** A single `threading.Lock` protects all mutations to all three dictionaries.

---

### Endpoints

#### `POST /products`

Creates a new product.

**Request body (JSON):**
```json
{
  "name": "Widget A",
  "sku": "SKU-001",
  "image_urls": [
    "https://cdn.example.com/products/sku-001/img-1.jpg",
    "https://cdn.example.com/products/sku-001/img-2.jpg"
  ],
  "video_urls": [
    "https://cdn.example.com/products/sku-001/demo.mp4"
  ]
}
```

**Success — `201 Created`:**
```json
{
  "id": "a1b2c3d4-...",
  "name": "Widget A",
  "sku": "SKU-001",
  "image_count": 2,
  "video_count": 1,
  "thumbnail_url": "https://cdn.example.com/products/sku-001/img-1.jpg",
  "created_at": "2026-05-22T15:00:00+00:00",
  "image_urls": ["..."],
  "video_urls": ["..."]
}
```

| Error | Status |
|---|---|
| Duplicate `sku` | `409 Conflict` |
| Empty/missing `name` or `sku` | `400 Bad Request` |
| Invalid URLs | `400 Bad Request` |
| More than 20 URLs per array | `400 Bad Request` |

---

#### `GET /products`

Lists products **without full media arrays** (designed for UI list/grid views).

**Query parameters:**

| Parameter | Default | Max | Description |
|---|---|---|---|
| `limit` | 20 | 100 | Number of products per page |
| `offset` | 0 | — | Number of products to skip |

**Response — `200 OK`:**
```json
{
  "total": 150,
  "limit": 20,
  "offset": 0,
  "products": [
    {
      "id": "a1b2c3d4-...",
      "name": "Widget A",
      "sku": "SKU-001",
      "image_count": 2,
      "video_count": 1,
      "thumbnail_url": "https://cdn.example.com/products/sku-001/img-1.jpg",
      "created_at": "2026-05-22T15:00:00+00:00"
    }
  ]
}
```

> **Performance:** Each list item contains only `image_count`, `video_count`, and `thumbnail_url` — never the full URL arrays. With 1,000 products × 10 images each, `GET /products?limit=20` returns only the 20 lightweight product objects without touching the 10,000 stored URLs.

---

#### `GET /products/{id}`

Returns the **full product** including all `image_urls` and `video_urls`.

**Response — `200 OK`:**
```json
{
  "id": "a1b2c3d4-...",
  "name": "Widget A",
  "sku": "SKU-001",
  "image_count": 2,
  "video_count": 1,
  "thumbnail_url": "https://cdn.example.com/products/sku-001/img-1.jpg",
  "created_at": "2026-05-22T15:00:00+00:00",
  "image_urls": [
    "https://cdn.example.com/products/sku-001/img-1.jpg",
    "https://cdn.example.com/products/sku-001/img-2.jpg"
  ],
  "video_urls": [
    "https://cdn.example.com/products/sku-001/demo.mp4"
  ]
}
```

**Unknown id — `404 Not Found`:**
```json
{
  "error": "Product not found."
}
```

---

#### `POST /products/{id}/media`

Appends new media URLs to an existing product.

**Request body (JSON):**
```json
{
  "image_urls": ["https://cdn.example.com/new-img.jpg"],
  "video_urls": ["https://cdn.example.com/new-video.mp4"]
}
```

- At least one of `image_urls` or `video_urls` must be provided
- Returns the full updated product (`200 OK`)
- Unknown id: `404 Not Found`
- Empty body (no URLs): `400 Bad Request`

---

### Validation Rules

| Rule | Limit |
|---|---|
| `name` | Required, non-empty string |
| `sku` | Required, non-empty string, must be unique |
| URL scheme | Must start with `http://` or `https://` |
| URL max length | 2,048 characters |
| Max URLs per array per request | 20 |

---

### Example curl Commands (Part 2)

```bash
# Create a product
curl -X POST http://127.0.0.1:8000/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Widget A",
    "sku": "SKU-001",
    "image_urls": ["https://cdn.example.com/img-1.jpg", "https://cdn.example.com/img-2.jpg"],
    "video_urls": ["https://cdn.example.com/demo.mp4"]
  }'

# List products (paginated)
curl "http://127.0.0.1:8000/products?limit=10&offset=0"

# Get product detail (replace <id> with actual UUID)
curl http://127.0.0.1:8000/products/<id>

# Append media to a product
curl -X POST http://127.0.0.1:8000/products/<id>/media \
  -H "Content-Type: application/json" \
  -d '{"image_urls": ["https://cdn.example.com/img-3.jpg"]}'
```

---

### Seed Script (Optional)

To create 1,000 products with 10 images each for performance testing:

```bash
python manage.py shell -c "
import urllib.request, json
for i in range(1000):
    data = json.dumps({
        'name': f'Product {i}',
        'sku': f'SKU-{i:04d}',
        'image_urls': [f'https://cdn.example.com/p{i}/img-{j}.jpg' for j in range(10)],
        'video_urls': [f'https://cdn.example.com/p{i}/video.mp4']
    }).encode()
    req = urllib.request.Request('http://127.0.0.1:8000/products', data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    urllib.request.urlopen(req)
    if i % 100 == 0: print(f'Created {i}...')
print('Done: 1000 products created')
"
```

After seeding, verify list performance:
```bash
curl "http://127.0.0.1:8000/products?limit=20"
# Returns 20 lightweight products instantly — no media arrays loaded
```

---

### Production Notes (Part 2)

**What would change with PostgreSQL + a CDN:**

| Aspect | Current (In-Memory) | Production (PostgreSQL + CDN) |
|---|---|---|
| **Storage** | Python dicts + lists | `products` table + `product_media` table (foreign key) |
| **List query** | Slice of `_products` dict | `SELECT id, name, sku, image_count, video_count, thumbnail_url FROM products LIMIT $1 OFFSET $2` — never joins media |
| **Detail query** | Merge `_products[id]` + `_media[id]` | `SELECT * FROM products WHERE id = $1` + `SELECT url, type FROM product_media WHERE product_id = $1` |
| **Media storage** | URL strings in lists | URLs point to a real CDN (S3 + CloudFront); `product_media` table stores the CDN URLs |
| **Uniqueness** | `_sku_index` dict | `UNIQUE` constraint on `products.sku` column |
| **Concurrency** | `threading.Lock` | Database-level row locks / transactions |
| **Thumbnail** | First `image_url` stored on product | Dedicated CDN-generated thumbnail URL, possibly resized via image processing pipeline |
| **Scalability** | Single process, single machine | Stateless app servers behind a load balancer; database handles persistence |

---

## Project Structure

```
.
├── core/                  # Django project settings & root URL config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── ratelimit_api/         # Part 1 — Rate-limited API
│   ├── views.py           # POST /request, GET /stats
│   ├── store.py           # In-memory rate limiter (rolling window + lock)
│   └── urls.py
├── catalog/               # Part 2 — Product catalog
│   ├── views.py           # CRUD + media endpoints
│   ├── store.py           # In-memory product + media store (lock-protected)
│   └── urls.py
├── manage.py
├── requirements.txt
└── README.md
```

---

## Running Tests

An automated test script is included:

```bash
# Start the server in one terminal
python manage.py runserver 8000

# Run tests in another terminal
python test_all.py
```

The test script covers **69 test cases** across both parts, including all validation rules, rate limiting behavior, pagination edge cases, and list-vs-detail separation.