# proxy_controller.py
import logging
import requests
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.views.decorators.clickjacking import xframe_options_exempt
from urllib.parse import unquote, urlparse

from proxy.services.proxy_service import safe_filename_from_url

logger = logging.getLogger(__name__)

# try import rewrite_html + is_allowed from proxy_service (adjust path if needed)
try:
    from .services.proxy_service import rewrite_html, is_allowed
except Exception:
    try:
        from services.proxy_service import rewrite_html, is_allowed
    except Exception:
        rewrite_html = None
        is_allowed = None
        logger.exception("Could not import proxy_service.rewrite_html / is_allowed")


@method_decorator(require_GET, name="dispatch")
class ProxyDiagView(View):
    """Diagnostic endpoint to inspect upstream headers quickly."""
    def get(self, request):
        raw = request.GET.get("url", "")
        if not raw:
            return JsonResponse({"ok": False, "error": "missing url"}, status=400)
        url = unquote(raw)
        try:
            r = requests.head(url, timeout=15, allow_redirects=True)
            return JsonResponse({"ok": True, "status": r.status_code, "headers": dict(r.headers)})
        except Exception as e:
            logger.exception("proxydiag error")
            return JsonResponse({"ok": False, "error": str(e)}, status=502)


@method_decorator(require_GET, name="dispatch")
@method_decorator(xframe_options_exempt, name="dispatch")
class ProxyHtmlView(View):
    """Proxy and rewrite HTML pages (strip scripts, rewrite links to /proxy*)."""
    def get(self, request):
        if rewrite_html is None or is_allowed is None:
            return HttpResponse("Server misconfigured: proxy_service not available", status=500)
        
        raw = request.GET.get("url", "")
        if not raw:
            return HttpResponse("Missing url", status=400)

        url = unquote(raw)
        
        # Get theme from authenticated user, fallback to query parameter, then default to 'light'
        theme = None
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            try:
                user = request.user
                # Try to get theme code from user
                # First, try direct access (if theme is already loaded via select_related)
                if hasattr(user, 'theme') and user.theme:
                    theme = getattr(user.theme, 'code', None)
                
                # If theme not loaded or code not available, try to fetch using theme_id
                if not theme and hasattr(user, 'theme_id') and user.theme_id:
                    try:
                        # Try different possible import paths for Theme model
                        Theme = None
                        try:
                            from core.configuration.models import Theme
                        except ImportError:
                            try:
                                from core.user.models import Theme
                            except ImportError:
                                pass
                        
                        if Theme:
                            theme_obj = Theme.objects.get(id=user.theme_id)
                            theme = getattr(theme_obj, 'code', None)
                    except Exception as fetch_error:
                        logger.debug("Could not fetch theme object: %s", fetch_error)
            except Exception as e:
                logger.warning("Failed to get theme from user: %s", e)
        
        # Fallback to query parameter if user theme not available
        if not theme:
            theme = request.GET.get("theme", "light")
        
        logger.info("ProxyHtml requested: %s (theme: %s)", url, theme)
        #print("\n===== [proxyhtml] REQUEST =====")
        #print("Raw URL param:", raw)
        #print("Decoded upstream URL:", url)
        
        # Extract original URL if it's a proxy URL (nested proxy call)
        from proxy.services.proxy_service import extract_original_url
        original_url = extract_original_url(url)
        #print(f"[proxyhtml] Original URL after extract: {original_url}")
        
        # Check if original URL is allowed
        if not is_allowed(original_url):
            logger.warning("ProxyHtml forbidden domain: %s", original_url)
            return HttpResponse("Forbidden domain", status=403)
        
        # Use original URL for fetching
        url = original_url

        try:
            upstream = requests.get(url, timeout=30, allow_redirects=True)
            #print("\n===== [proxyhtml] UPSTREAM RESPONSE =====")
            #print("Status code:", upstream.status_code)
            #print("Headers:", upstream.headers.get("Content-Type"))
            #print("Content type:", upstream.headers.get("Content-Type"))
            #print("Content length:", upstream.headers.get("Content-Length"))
        except Exception as e:
            logger.exception("Upstream fetch failed for %s", url)
            return HttpResponse(f"Upstream error: {e}", status=502)

        try:
            html = rewrite_html(upstream.content, url, theme=theme)

        except Exception:
            logger.exception("rewrite_html failed; returning raw content")
            html = upstream.content or b""

        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        # override headers that would block embedding
        # Remove X-Frame-Options to allow embedding in iframe
        if "X-Frame-Options" in resp:
            del resp["X-Frame-Options"]
        resp["Access-Control-Allow-Origin"] = "*"
        # remove CSP if present in resp (resp is new, but ensure not set)
        if "Content-Security-Policy" in resp:
            del resp["Content-Security-Policy"]
        return resp


@method_decorator(require_GET, name="dispatch")
@method_decorator(xframe_options_exempt, name="dispatch")
class ProxyFileView(View):
    """
    Stream a binary resource from upstream and override headers that may block embedding.
    Usage: /api/proxy/proxy?url=<encoded upstream url>
    """
    def get(self, request):
        raw = request.GET.get("url", "")
        if not raw:
            return HttpResponse("Missing url parameter", status=400)
        # decode once
        upstream_url = unquote(raw)

        #print("\n===== [proxyfile] REQUEST =====")
        #print("Raw URL param:", raw)
        #print("Decoded upstream URL:", upstream_url)

        # Forward Range header if client requested (for PDF seeking)
        headers = {}
        if "HTTP_RANGE" in request.META:
            headers["Range"] = request.META["HTTP_RANGE"]
        # optional: forward other useful headers (User-Agent) if needed
        # headers["User-Agent"] = request.META.get("HTTP_USER_AGENT", "proxy")

        try:
            # allow redirects, stream content
            r = requests.get(upstream_url, headers=headers, stream=True, timeout=30, allow_redirects=True)
        except Exception as e:
            #print("ERROR fetching file upstream:", e)
            return HttpResponse("Upstream fetch error", status=502)

        #print("\n===== [proxyfile] UPSTREAM RESPONSE =====")
        #print("Status code:", r.status_code)
        #print("Headers:", r.headers.get("Content-Type"))
        #print("Content type:", r.headers.get("Content-Type"))
        #print("Content length:", r.headers.get("Content-Length"))
        # If upstream returned non-200 (e.g., 404), return that status and body as text/html so browser can show
        if r.status_code != 200 and r.status_code != 206:
            # stream error body (likely HTML)
            body = r.content or f"Upstream returned {r.status_code}".encode("utf-8")
            return HttpResponse(body, status=r.status_code, content_type=r.headers.get("Content-Type", "text/html"))

        # Build streaming response
        resp = StreamingHttpResponse(r.iter_content(chunk_size=8192), status=r.status_code)

        # Forward key headers from upstream if present
        upstream_ct = r.headers.get("Content-Type")
        if upstream_ct:
            resp["Content-Type"] = upstream_ct
        else:
            resp["Content-Type"] = "application/octet-stream"
        if "text/html" in upstream_ct.lower():
            content = b''.join(r.iter_content(chunk_size=8192))
            html = content.decode('utf-8', errors='ignore')
            # Use BeautifulSoup to properly handle HTML and preserve target="_blank" for PDF links
            from bs4 import BeautifulSoup
            import re
            try:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "")
                    # Check if href points to PDF
                    is_pdf = bool(re.search(r'\.pdf$', href, re.I))
                    # Only remove target if not PDF
                    if "target" in a.attrs and not is_pdf:
                        del a.attrs["target"]
                html = str(soup)
            except Exception:
                # Fallback to regex if BeautifulSoup fails
                import re
                # Simple regex: remove target="_blank" but this won't be as accurate
                # Better to let BeautifulSoup handle it above
                html = re.sub(r'\starget\s*=\s*["\']_blank["\']', '', html, flags=re.IGNORECASE)
            resp = HttpResponse(html.encode('utf-8'), status=r.status_code)
            resp["Content-Type"] = upstream_ct
        else:
            # Stream file (PDF, images...) như cũ
            resp = StreamingHttpResponse(r.iter_content(chunk_size=8192), status=r.status_code)
            resp["Content-Type"] = upstream_ct or "application/octet-stream"
        # Forward range related headers if they exist
        if "Content-Range" in r.headers:
            resp["Content-Range"] = r.headers["Content-Range"]
        if "Accept-Ranges" in r.headers:
            resp["Accept-Ranges"] = r.headers["Accept-Ranges"]

        # Ensure inline display where appropriate (PDF / images)
        cd = r.headers.get("Content-Disposition", "")
        # If upstream suggests attachment or no disposition, we prefer inline for embedding
        if not cd or "attachment" in cd.lower():
            filename = safe_filename_from_url(upstream_url)
            # prevent header injection by ensuring no newlines
            filename = filename.replace("\n", "").replace("\r", "")
            resp["Content-Disposition"] = f'inline; filename="{filename}"'
        else:
            # keep upstream value if explicit and not 'attachment' OR you can override as above
            resp["Content-Disposition"] = cd

        # OVERRIDE / REMOVE headers that may prevent embedding or trigger strict checks
        # Remove these if present; set safer / permissive ones
        for h in ["Content-Security-Policy", "Content-Security-Policy-Report-Only",
                "Cross-Origin-Opener-Policy", "Cross-Origin-Embedder-Policy",
                "X-Frame-Options"]:
            if h in resp:
                try:
                    del resp[h]
                except Exception:
                    pass

        # Add headers to allow embedding from anywhere (or restrict to your origin)
        # resp["X-Frame-Options"] = "ALLOWALL"
        # Be careful with wildcard CORS in production
        resp["Access-Control-Allow-Origin"] = "*"
        resp["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        resp["Pragma"] = "no-cache"
        resp["Expires"] = "0"
        # Keep MIME snoffing protection
        resp["X-Content-Type-Options"] = "nosniff"

        #print("\n===== [proxyfile] RESPONSE =====")
        #print("Status code:", resp.status_code)
        #print("Headers:", resp.get("Content-Type"))
        #print("Content type:", resp.get("Content-Type"))
        #print("Content length:", r.headers.get("Content-Length"))
        #print("Proxy FILE OK → returning streamed response\n")

        return resp


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@csrf_exempt
@require_http_methods(["POST"])
def notam_proxy(request):
    """
    Proxy endpoint for NOTAM search requests to AIM API.
    Forwards POST requests to https://aim.koca.go.kr/xNotam/searchValidNotam.do
    """
    AIM_API_BASE_URL = "https://aim.koca.go.kr/xNotam/searchValidNotam.do"

    try:
        # Parse request body
        if request.content_type == 'application/json':
            params = json.loads(request.body)
        else:
            params = request.POST.dict()

        # Extract ibpage as query parameter
        ibpage = params.pop('ibpage', 1)

        # Build form data for upstream API (excluding ibpage)
        form_data = {}
        for key, value in params.items():
            if value is not None and value != '':
                form_data[key] = str(value)

        # Build URL with ibpage as query parameter
        url = f"{AIM_API_BASE_URL}?ibpage={ibpage}"

        logger.info(f"NOTAM proxy request to {url} with form data: {form_data}")

        # Forward request to AIM API
        response = requests.post(
            url,
            data=form_data,
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://aim.koca.go.kr',
                'Referer': 'https://aim.koca.go.kr/xNotam/index.do'
            }
        )

        # Return the response from AIM API
        return JsonResponse(
            response.json(),
            status=response.status_code,
            safe=False
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in NOTAM request: {e}")
        return JsonResponse(
            {"error": "Invalid JSON format"},
            status=400
        )
    except requests.RequestException as e:
        logger.error(f"NOTAM upstream request failed: {e}")
        return JsonResponse(
            {"error": f"Upstream API error: {str(e)}"},
            status=502
        )
    except Exception as e:
        logger.exception(f"NOTAM proxy error: {e}")
        return JsonResponse(
            {"error": "Internal server error"},
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def notam_detail_proxy(request):
    """
    Proxy endpoint for NOTAM detail requests to AIM API.
    Forwards POST requests to https://aim.koca.go.kr/xNotam/searchFullTextKr.do
    """
    AIM_API_BASE_URL = "https://aim.koca.go.kr/xNotam/searchFullTextKr.do"

    try:
        # Parse request body
        if request.content_type == 'application/json':
            params = json.loads(request.body)
        else:
            params = request.POST.dict()

        # Extract seq parameter
        seq = params.get('seq', '')

        if not seq:
            return JsonResponse(
                {"error": "seq parameter is required"},
                status=400
            )

        # Build form data for upstream API
        form_data = {'seq': str(seq)}

        logger.info(f"NOTAM detail proxy request to {AIM_API_BASE_URL} with form data: {form_data}")

        # Forward request to AIM API
        response = requests.post(
            AIM_API_BASE_URL,
            data=form_data,
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://aim.koca.go.kr',
                'Referer': 'https://aim.koca.go.kr/xNotam/index.do'
            }
        )

        # Return the response from AIM API
        return JsonResponse(
            response.json(),
            status=response.status_code,
            safe=False
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in NOTAM detail request: {e}")
        return JsonResponse(
            {"error": "Invalid JSON format"},
            status=400
        )
    except requests.RequestException as e:
        logger.error(f"NOTAM detail upstream request failed: {e}")
        return JsonResponse(
            {"error": f"Upstream API error: {str(e)}"},
            status=502
        )
    except Exception as e:
        logger.exception(f"NOTAM detail proxy error: {e}")
        return JsonResponse(
            {"error": "Internal server error"},
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def airport_search_proxy(request):
    """
    Proxy endpoint for airport search requests to AIM API.
    Forwards POST requests to https://aim.koca.go.kr/svsdo/searchAirport.do
    """
    AIM_API_BASE_URL = "https://aim.koca.go.kr/svsdo/searchAirport.do"

    try:
        # Parse request body
        if request.content_type == 'application/json':
            params = json.loads(request.body)
        else:
            params = request.POST.dict()

        # Build form data for upstream API
        form_data = {
            'sch_location': params.get('sch_location', ''),
            'sch_fir': params.get('sch_fir', '')
        }

        logger.info(f"Airport search proxy request to {AIM_API_BASE_URL} with form data: {form_data}")

        # Forward request to AIM API
        response = requests.post(
            AIM_API_BASE_URL,
            data=form_data,
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://aim.koca.go.kr',
                'Referer': 'https://aim.koca.go.kr/'
            }
        )

        # Return the response from AIM API
        return JsonResponse(
            response.json(),
            status=response.status_code,
            safe=False
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in airport search request: {e}")
        return JsonResponse(
            {"error": "Invalid JSON format"},
            status=400
        )
    except requests.RequestException as e:
        logger.error(f"Airport search upstream request failed: {e}")
        return JsonResponse(
            {"error": f"Upstream API error: {str(e)}"},
            status=502
        )
    except Exception as e:
        logger.exception(f"Airport search proxy error: {e}")
        return JsonResponse(
            {"error": "Internal server error"},
            status=500
        )
