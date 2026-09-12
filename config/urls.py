from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.decorators import login_not_required
from django.views.generic import TemplateView

from core.views import service_worker

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("expenses/", include("expenses.urls")),
    path("settle/", include("settlements.urls")),
    path("recurring/", include("recurring.urls")),
    path("api/", include("api.urls")),
    # A service worker only controls pages at or below its own URL, so this
    # must be served from the root -- /static/sw.js would scope it to /static/.
    path("sw.js", service_worker, name="sw"),
    # Must stay anonymous-reachable: the service worker precaches this at
    # install time, and a login redirect cached here would be permanent.
    path(
        "offline/",
        login_not_required(TemplateView.as_view(template_name="core/offline.html")),
        name="offline",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
