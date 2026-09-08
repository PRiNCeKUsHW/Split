from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.generic import TemplateView

from django.contrib.auth.decorators import login_not_required


class DashboardView(TemplateView):
    """Placeholder home screen.

    Phase 4 replaces the body with real balances; for now it exists so the
    nav, the styling and the login redirect have somewhere to land.
    """

    template_name = "core/dashboard.html"


@login_not_required
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request: HttpRequest) -> HttpResponse:
    """Serve sw.js from the site root so its scope covers every page.

    Rendered as a template rather than shipped as a static file so the cache
    name carries the app version -- bumping the version retires stale caches
    on every phone without anyone clearing site data.
    """
    from django.template.loader import render_to_string

    body = render_to_string(
        "sw.js",
        {"version": getattr(settings, "APP_VERSION", "1"), "static_url": settings.STATIC_URL},
        request=request,
    )
    return HttpResponse(body, content_type="application/javascript")
