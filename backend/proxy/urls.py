# urls.py (app-level)
from django.urls import path
from .views import (
    ProxyHtmlView,
    ProxyFileView,
    ProxyDiagView,
    notam_proxy,
    notam_detail_proxy,
    airport_search_proxy,
)

urlpatterns = [
    path("proxydiag", ProxyDiagView.as_view(), name="proxy-diag"),
    path("proxyhtml", ProxyHtmlView.as_view(), name="proxy-html"),
    path("proxy", ProxyFileView.as_view(), name="proxy-file"),
    path("notam", notam_proxy, name="notam-proxy"),
    path("notam-detail", notam_detail_proxy, name="notam-detail-proxy"),
    path("airport-search", airport_search_proxy, name="airport-search-proxy"),
]
