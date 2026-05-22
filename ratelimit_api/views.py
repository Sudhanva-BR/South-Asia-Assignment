import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .store import try_accept, get_stats


@method_decorator(csrf_exempt, name='dispatch')
class RequestView(View):
    def post(self, request):
        # Parse JSON body
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {"error": "Invalid JSON body."},
                status=400
            )

        if not isinstance(body, dict):
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

        user_id = body.get("user_id", None)
        payload = body.get("payload", None)

        # Validate user_id
        if user_id is None or not isinstance(user_id, str) or user_id.strip() == "":
            return JsonResponse(
                {"error": "user_id is required and must be a non-empty string."},
                status=400
            )

        # Validate payload presence
        if "payload" not in body:
            return JsonResponse(
                {"error": "payload is required."},
                status=400
            )

        accepted = try_accept(user_id)

        if accepted:
            return JsonResponse(
                {
                    "status": "accepted",
                    "message": "Request accepted successfully.",
                    "user_id": user_id,
                },
                status=201
            )
        else:
            return JsonResponse(
                {
                    "error": "Rate limit exceeded. Maximum 5 requests per minute.",
                    "user_id": user_id,
                },
                status=429
            )


@method_decorator(csrf_exempt, name='dispatch')
class StatsView(View):
    def get(self, request):
        stats = get_stats()
        return JsonResponse(
            {
                "stats": list(stats.values()),
                "description": {
                    "accepted_current_window": "Number of accepted requests in the current 60-second rolling window.",
                    "rejected_cumulative": "Total rejected requests since server start (cumulative).",
                }
            },
            status=200
        )