import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .store import (
    create_product, list_products, get_product, append_media,
    validate_urls, MAX_URLS_PER_REQUEST
)

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@method_decorator(csrf_exempt, name='dispatch')
class ProductListCreateView(View):

    def get(self, request):
        # Parse pagination params
        try:
            limit = int(request.GET.get("limit", DEFAULT_LIMIT))
            offset = int(request.GET.get("offset", 0))
        except ValueError:
            return JsonResponse({"error": "limit and offset must be integers."}, status=400)

        if limit < 1 or limit > MAX_LIMIT:
            return JsonResponse({"error": f"limit must be between 1 and {MAX_LIMIT}."}, status=400)
        if offset < 0:
            return JsonResponse({"error": "offset must be >= 0."}, status=400)

        products, total = list_products(limit, offset)
        return JsonResponse({
            "total": total,
            "limit": limit,
            "offset": offset,
            "products": products,
        }, status=200)

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        if not isinstance(body, dict):
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

        name = body.get("name", "")
        sku = body.get("sku", "")
        image_urls = body.get("image_urls", [])
        video_urls = body.get("video_urls", [])

        # Validate name and sku
        if not name or not isinstance(name, str) or name.strip() == "":
            return JsonResponse({"error": "name is required and must be a non-empty string."}, status=400)
        if not sku or not isinstance(sku, str) or sku.strip() == "":
            return JsonResponse({"error": "sku is required and must be a non-empty string."}, status=400)

        # Validate image_urls
        if image_urls:
            ok, err = validate_urls(image_urls)
            if not ok:
                return JsonResponse({"error": f"image_urls: {err}"}, status=400)

        # Validate video_urls
        if video_urls:
            ok, err = validate_urls(video_urls)
            if not ok:
                return JsonResponse({"error": f"video_urls: {err}"}, status=400)

        product, error, status = create_product(name.strip(), sku.strip(), image_urls, video_urls)

        if error:
            return JsonResponse({"error": error}, status=status)

        return JsonResponse(product, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class ProductDetailView(View):

    def get(self, request, product_id):
        product = get_product(product_id)
        if not product:
            return JsonResponse({"error": "Product not found."}, status=404)
        return JsonResponse(product, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class ProductMediaView(View):

    def post(self, request, product_id):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        if not isinstance(body, dict):
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

        image_urls = body.get("image_urls", [])
        video_urls = body.get("video_urls", [])

        # Must have at least one URL
        if not image_urls and not video_urls:
            return JsonResponse(
                {"error": "At least one of image_urls or video_urls is required."},
                status=400
            )

        if image_urls:
            ok, err = validate_urls(image_urls)
            if not ok:
                return JsonResponse({"error": f"image_urls: {err}"}, status=400)

        if video_urls:
            ok, err = validate_urls(video_urls)
            if not ok:
                return JsonResponse({"error": f"video_urls: {err}"}, status=400)

        product, error = append_media(product_id, image_urls or [], video_urls or [])
        if error:
            return JsonResponse({"error": error}, status=404)

        return JsonResponse(product, status=200)