# proxy_service.py
from email.utils import unquote
import re
from urllib.parse import urljoin, urlparse, quote, parse_qs
from bs4 import BeautifulSoup

PROXY_FILE = "/api/proxy/proxy?url="
PROXY_HTML = "/api/proxy/proxyhtml?url="

ALLOWED_HOSTS = (
    "aim.koca.go.kr",
    "aip.caat.or.th",
)

def is_allowed(url):
    try:
        host = urlparse(url).hostname or ""
        return any(host.endswith(d) for d in ALLOWED_HOSTS)
    except:
        return False

def extract_original_url(url):
    """Extract original URL from proxy URL if it's a nested proxy call"""
    # Check if URL contains proxy path
    if '/api/proxy/proxyhtml' in url or '/api/proxy/proxy' in url:
        # Extract the actual URL from proxy URL query parameter
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'url' in query_params:
            original_url = query_params['url'][0]
            #print(f"[extract_original_url] Found nested proxy URL: {url}")
            #print(f"[extract_original_url] Extracted original URL: {original_url}")
            # Recursively extract in case of nested proxy calls
            return extract_original_url(original_url)
    return url

def abs_url(base, link):
    # Ensure base is original URL, not proxy URL
    original_base = extract_original_url(base)
    result = urljoin(original_base, link)
    # if base != original_base:
        #print(f"[abs_url] Base URL changed: {base} -> {original_base}")
    #print(f"[abs_url] Joining: base={original_base}, link={link} -> result={result}")
    return result

def to_proxy_html(url):
    return PROXY_HTML + quote(url, safe='')

def to_proxy_file(url):
    return PROXY_FILE + quote(url, safe='')

def is_binary(url):
    return bool(re.search(r'\.(pdf|jpg|jpeg|png|gif|xml|zip|mp3|mp4|ttf|woff2?|eot)$', url, re.I))

def rewrite_html(html_bytes: bytes, current_url: str, theme: str = "light") -> bytes:
    #print("\n===== [rewrite_html] REQUEST =====")
    #print("Current URL (before extract):", current_url)
    # Ensure current_url is original URL, not proxy URL
    current_url = extract_original_url(current_url)
    #print("Current URL (after extract):", current_url)
    #print("Incoming HTML size:", len(html_bytes))
    try:
        try:
            soup = BeautifulSoup(html_bytes, "lxml")
        except:
            soup = BeautifulSoup(html_bytes, "html.parser")

        # remove script tags
        for s in soup.find_all("script"):
            s.decompose()

        # remove inline on* attributes
        for tag in soup.find_all(True):
            for a in list(tag.attrs.keys()):
                if a.lower().startswith("on"):
                    try:
                        del tag.attrs[a]
                    except:
                        pass

        # remove base tags
        for b in soup.find_all("base"):
            b.decompose()

        # remove header tags (if user wants to hide header)
        for header in soup.find_all("header"):
            header.decompose()

        # remove body tags with class "commands"
        for body in soup.find_all("body"):
            classes = body.get("class", [])
            # Handle both string and list class attributes
            if isinstance(classes, list):
                if "commands" in classes:
                    body.decompose()
            elif isinstance(classes, str) and "commands" in classes.split():
                body.decompose()

        # remove dl tags with class "skipnavi"
        for dl in soup.find_all("dl"):
            classes = dl.get("class", [])
            # Handle both string and list class attributes
            if isinstance(classes, list):
                if "skipnavi" in classes:
                    dl.decompose()
            elif isinstance(classes, str) and "skipnavi" in classes.split():
                dl.decompose()

        # rewrite anchors
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.lower().startswith("javascript:") or href == "":
                a["href"] = "#"
                if "target" in a.attrs:
                    del a.attrs["target"]
                continue

            u = abs_url(current_url, href)
            p = urlparse(u)
            if p.path in ("", "/"):
                u = current_url

            # Check if URL is PDF before removing target
            is_pdf = bool(re.search(r'\.pdf$', u, re.I))
            
            if is_binary(u):
                a["href"] = to_proxy_file(u)
            else:
                a["href"] = to_proxy_html(u)
            
            # Only remove target if not PDF
            if "target" in a.attrs and not is_pdf:
                del a.attrs["target"]

        # rewrite forms
        for f in soup.find_all("form", action=True):
            act = f["action"].strip()
            u = abs_url(current_url, act) if act else current_url
            f["action"] = to_proxy_file(u)
            if "target" in f.attrs:
                del f.attrs["target"]

        # rewrite stylesheets
        for lk in soup.find_all("link", href=True):
            rel = lk.get("rel") or []
            if "stylesheet" in rel:
                u = abs_url(current_url, lk["href"])
                lk["href"] = to_proxy_file(u)

        # rewrite src attributes
        for tagname, attr in (("img","src"),("iframe","src"),("frame","src"),("audio","src"),("video","src"),("source","src")):
            for t in soup.find_all(tagname):
                if attr not in t.attrs:
                    continue
                v = t[attr].strip()
                if v.lower().startswith("data:") or v.lower().startswith("javascript:"):
                    continue

                u = abs_url(current_url, v)
                p = urlparse(u)
                if p.path in ("", "/"):
                    u = current_url

                if tagname in ("iframe","frame"):
                    t[attr] = to_proxy_html(u)
                else:
                    t[attr] = to_proxy_file(u)

                if "target" in t.attrs:
                    del t.attrs["target"]

        # meta refresh
        for m in soup.find_all("meta", attrs={"http-equiv": True}):
            if m["http-equiv"].lower() == "refresh":
                c = m.get("content", "")
                match = re.search(r"url=(.*)", c, re.I)
                if match:
                    tgt = abs_url(current_url, match.group(1))
                    m["content"] = f"0; url={to_proxy_html(tgt)}"
                else:
                    m.decompose()

        # rewrite url(...) in style tags and style attributes
        def fix_style(match):
            target = match.group(1).strip('\'"')
            target = abs_url(current_url, target)
            return f"url({to_proxy_file(target)})"

        for style in soup.find_all("style"):
            if style.string:
                style.string = re.sub(r'url\(([^)]+)\)', fix_style, style.string)
        for tag in soup.find_all(style=True):
            try:
                tag['style'] = re.sub(r'url\(([^)]+)\)', fix_style, tag['style'])
            except:
                pass

        # Remove eAISCommands frame from anywhere in the document
        commands_frame = soup.find("frame", {"name": "eAISCommands"})
        if commands_frame:
            commands_frame.decompose()

        # Extract eAISNavigationBase frame from frameset and replace with iframe
        frameset = soup.find("frameset")
        if frameset:
            # Adjust frameset rows if needed (remove first row if it was for commands)
            rows_attr = frameset.get("rows", "")
            if rows_attr and "," in rows_attr:
                rows = rows_attr.split(",")
                if len(rows) == 2:
                    # If there were 2 rows and we removed commands frame, use only second row
                    frameset["rows"] = rows[1].strip()

            # Find frame with name="eAISNavigationBase"
            nav_frame = soup.find("frame", {"name": "eAISNavigationBase"})
            if nav_frame and nav_frame.get("src"):
                frame_src = nav_frame["src"]
                #print(f"[rewrite_html] Found frame src: {frame_src}")
                #print(f"[rewrite_html] Current URL for abs_url: {current_url}")
                # Convert relative URL to absolute
                frame_url = abs_url(current_url, frame_src)
                #print(f"[rewrite_html] Absolute frame URL: {frame_url}")
                # Convert to proxy URL
                proxy_frame_url = to_proxy_html(frame_url)
                #print(f"[rewrite_html] Proxy frame URL: {proxy_frame_url}")
                
                # Create new body with iframe
                new_body = soup.new_tag("body")
                new_body["style"] = "margin: 0; padding: 0; width: 100%; height: 100vh; overflow: hidden;"
                
                # Create iframe element
                new_iframe = soup.new_tag("iframe")
                new_iframe["src"] = proxy_frame_url
                new_iframe["style"] = "width: 100%; height: 100vh; border: none; display: block;"
                new_iframe["name"] = "eAISNavigationBase"
                
                new_body.append(new_iframe)
                
                # Remove old frameset and body if exists
                if soup.find("body"):
                    soup.find("body").decompose()
                frameset.decompose()
                
                # Append new body
                if soup.find("html"):
                    soup.find("html").append(new_body)
                
                # Add CSS to ensure full width/height
                if soup.find("head"):
                    style_tag = soup.new_tag("style")
                    style_tag.string = """
                        html, body {
                            margin: 0;
                            padding: 0;
                            width: 100%;
                            height: 100%;
                            overflow: hidden;
                        }
                        iframe {
                            width: 100% !important;
                            height: 100vh !important;
                            border: none !important;
                            display: block !important;
                        }
                    """
                    soup.find("head").append(style_tag)

        # Inject GuardianX custom styles into all HTML content
        if soup.find("head"):
            # Determine theme-specific colors
            is_dark = theme.lower() == "dark"

            # Theme-specific color variables
            bg_color = "#1f1f20" if is_dark else "#ffffff"
            text_color = "#ececef" if is_dark else "#2d2e30"
            heading_color = "#ececef" if is_dark else "#2d2e30"
            table_header_bg = "#2d2e30" if is_dark else "#f6f7f8"
            table_border_color = "#444646" if is_dark else "#dddfe2"
            scrollbar_track_bg = "#2d2e30" if is_dark else "#f2f2f2"
            input_bg = "#2d2e30" if is_dark else "#ffffff"
            input_border = "#444646" if is_dark else "#dddfe2"

            # Build dark mode specific overrides
            dark_mode_overrides = ""
            if is_dark:
                dark_mode_overrides = f"""
                /* Override hardcoded white backgrounds in dark mode */
                [style*='background-color: white'], [style*='background-color:#FFFFFF'],
                [style*='background-color: #FFF'], [style*='background: white'],
                [style*='background:#FFFFFF'], [style*='background: #FFF'] {{
                    background-color: {bg_color} !important;
                }}

                /* Override hardcoded black text in dark mode */
                [style*='color: black'], [style*='color:#000000'], [style*='color: #000'] {{
                    color: {text_color} !important;
                }}
                """

            custom_style_tag = soup.new_tag("style")
            custom_style_tag.string = f"""
                /* GuardianX Custom Styles - Theme: {theme} */
                @font-face {{
                    font-family: 'Inter';
                    src: local('Inter'), local('system-ui'), local('-apple-system'), local('BlinkMacSystemFont');
                    font-display: swap;
                }}

                /* Base font size - matching GuardianX */
                html {{
                    font-size: 16px !important;
                }}

                @media screen and (min-width: 2560px) {{
                    html {{
                        font-size: 18px !important;
                    }}
                }}

                @media screen and (min-width: 1920px) and (max-width: 2559px) {{
                    html {{
                        font-size: 16px !important;
                    }}
                }}

                @media screen and (min-width: 1440px) and (max-width: 1919px) {{
                    html {{
                        font-size: 15px !important;
                    }}
                }}

                @media screen and (max-width: 1439px) {{
                    html {{
                        font-size: 14px !important;
                    }}
                }}

                body, html {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                        sans-serif !important;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                    background-color: {bg_color} !important;
                    color: {text_color} !important;
                    line-height: 1.6 !important;
                }}

                html {{
                    padding: 2rem 1rem !important;

                }}
                html>body.tab {{
                    padding-top: 2.5rem !important;	/* intended value for better browsers */
                }}

                /* Override all text elements to use Inter font and better sizing */
                * {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                        sans-serif !important;
                }}

                {dark_mode_overrides}

                /* Main content areas - ensure proper dark mode background */
                #main, #content, .content, .main-content, [role="main"] {{
                    background-color: {bg_color} !important;
                    color: {text_color} !important;
                }}

                /* Navigation and tree structures */
                nav, .navigation, .nav, .tree, .toc, [role="navigation"], [role="tree"] {{
                    background-color: {bg_color} !important;
                    color: {text_color} !important;
                }}

                /* Paragraphs and general text */
                p, div:not([style*="background"]), span:not([style*="background"]), li {{
                    font-size: 1rem !important;
                    line-height: 1.6 !important;
                    color: {text_color} !important;
                }}

                /* Divs without explicit backgrounds should use theme background */
                div:not([class*="highlight"]):not([class*="active"]):not([style*="background-color"]) {{
                    background-color: {bg_color} !important;
                }}

                /* Preserve highlighted/active elements but ensure text is readable */
                .highlight, .active, .selected, [class*="highlight"], [class*="active"] {{
                    color: white !important;
                }}

                /* Blue highlighted sections (like Part 1, Part 2, etc.) */
                [style*="background-color: blue"], [style*="background: blue"],
                [style*="background-color:#0000FF"], [style*="background:#0000FF"],
                [style*="background-color: #00"], [style*="background: #00"] {{
                    color: white !important;
                    font-weight: 600 !important;
                }}

                /* List items */
                ul, ol {{
                    font-size: 1rem !important;
                    line-height: 1.8 !important;
                    background-color: {bg_color} !important;
                }}

                li {{
                    margin-bottom: 0.5rem !important;
                    font-size: 1rem !important;
                    color: {text_color} !important;
                    background-color: {bg_color} !important;
                }}

                /* Tree navigation items and collapsible sections */
                .tree-node, .tree-item, [class*="tree"], [class*="toc"] {{
                    background-color: {bg_color} !important;
                    color: {text_color} !important;
                }}

                /* Section headers and parts (common in AIP documents) */
                [class*="part"], [class*="section"], [class*="header"] {{
                    font-weight: 600 !important;
                }}

                /* Frames and containers */
                frame, iframe {{
                    background-color: {bg_color} !important;
                }}

                /* Tables of contents */
                .toc, #toc, [id*="toc"], [class*="contents"] {{
                    background-color: {bg_color} !important;
                    color: {text_color} !important;
                }}

                /* Primary color for links and highlights */
                a {{
                    color: {"#ececef" if is_dark else "black"} !important;
                    text-decoration: none !important;
                    font-size: 1rem !important;
                }}

                a:hover {{
                    color: #1D9BE2 !important;
                    text-decoration: underline !important;
                }}

                /* Headings - larger and more prominent */
                h1 {{
                    color: {heading_color} !important;
                    font-weight: 700 !important;
                    font-size: 2rem !important;
                    line-height: 1.3 !important;
                    margin: 1.5rem 0 1rem 0 !important;
                }}

                h2 {{
                    color: {heading_color} !important;
                    font-weight: 600 !important;
                    font-size: 1.5rem !important;
                    line-height: 1.4 !important;
                    margin: 1.25rem 0 0.875rem 0 !important;
                }}

                h3 {{
                    color: {heading_color} !important;
                    font-weight: 600 !important;
                    font-size: 1.25rem !important;
                    line-height: 1.4 !important;
                    margin: 1rem 0 0.75rem 0 !important;
                }}

                h4 {{
                    color: {heading_color} !important;
                    font-weight: 600 !important;
                    font-size: 1.125rem !important;
                    line-height: 1.5 !important;
                    margin: 1rem 0 0.75rem 0 !important;
                }}

                h5, h6 {{
                    color: {heading_color} !important;
                    font-weight: 600 !important;
                    font-size: 1rem !important;
                    line-height: 1.5 !important;
                    margin: 0.875rem 0 0.625rem 0 !important;
                }}

                /* Navigation and tabs styling */
                nav, .nav, .tabs, [role="navigation"] {{
                    font-size: 1rem !important;
                }}

                /* Top-level tab container (only body > div.tab for navigation) */
                body.tab > div.tab {{
                    background-color: {bg_color} !important;
                    display: flex !important;
                    gap: 0.5rem !important;
                    padding: 0.75rem 1rem !important;
                    border-bottom: 1px solid {table_border_color} !important;
                }}

                /* Tab items (only direct links in top navigation) */
                body.tab > div.tab > a {{
                    font-size: 1rem !important;
                    padding: 0.625rem 1.25rem !important;
                    font-weight: 500 !important;
                    border-radius: 6px !important;
                    transition: all 0.2s ease !important;
                    text-decoration: none !important;
                    color: {text_color} !important;
                    background-color: {"#2d2e30" if is_dark else "#f6f7f8"} !important;
                    border: 1px solid {table_border_color} !important;
                }}

                /* Tab hover */
                body.tab > div.tab > a:hover {{
                    background-color: {"#3d3e40" if is_dark else "#e8e9ea"} !important;
                    border-color: #1d9be2 !important;
                    color: #1d9be2 !important;
                    transform: translateY(-1px) !important;
                }}

                /* Active/current tab */
                body.tab > div.tab > a#current {{
                    background-color: #1d9be2 !important;
                    color: white !important;
                    font-weight: 600 !important;
                    border-color: #1d9be2 !important;
                }}

                /* Effective date header */
                .effDate, h2.effDate {{
                    font-size: 1.25rem !important;
                    font-weight: 600 !important;
                    color: {heading_color} !important;
                    text-align: center !important;
                    margin: 1rem 0 !important;
                    padding: 0.75rem !important;
                    background-color: {bg_color} !important;
                }}

                /* Amendment intro text */
                .amdtIntro, h2.amdtIntro {{
                    font-size: 1rem !important;
                    font-weight: normal !important;
                    color: {text_color} !important;
                    padding: 1rem !important;
                    background-color: {bg_color} !important;
                    line-height: 1.6 !important;
                }}

                /* Amendment groups */
                #amdtGroups {{
                    background-color: {bg_color} !important;
                    padding: 1rem !important;
                }}

                /* Amendment group titles */
                .amdtGroupTitle {{
                    font-size: 1.125rem !important;
                    font-weight: 600 !important;
                    color: {heading_color} !important;
                    background-color: {"#2d2e30" if is_dark else "#f6f7f8"} !important;
                    padding: 0.75rem 1rem !important;
                    margin: 0.5rem 0 !important;
                    border-radius: 4px !important;
                    cursor: pointer !important;
                }}

                /* Hierarchy items (Hx class) */
                .Hx, .H4 {{
                    font-size: 1rem !important;
                    color: {text_color} !important;
                    background-color: {bg_color} !important;
                    padding: 0.5rem 0.75rem !important;
                    line-height: 1.6 !important;
                }}

                .Hx:hover {{
                    background-color: {"#2d2e30" if is_dark else "#f6f7f8"} !important;
                }}

                /* Plus/minus expand/collapse indicators */
                .Plus, span.Plus {{
                    color: #1d9be2 !important;
                    font-weight: 700 !important;
                    margin-right: 0.5rem !important;
                    cursor: pointer !important;
                    display: inline-block !important;
                    min-width: 1rem !important;
                }}

                /* Numbering in navigation */
                .Number, .Numbering {{
                    font-weight: 600 !important;
                    color: {heading_color} !important;
                    margin-right: 0.5rem !important;
                }}

                /* Amendment links (arrows ►) */
                a.amdtLink {{
                    color: #1d9be2 !important;
                    text-decoration: none !important;
                    margin-left: 0.25rem !important;
                    font-weight: 700 !important;
                    font-size: 1rem !important;
                }}

                a.amdtLink:hover {{
                    color: #248bc5 !important;
                    text-decoration: none !important;
                }}

                /* Level indentation */
                .level {{
                    padding-left: 1.5rem !important;
                    background-color: {bg_color} !important;
                }}

                /* Amendment group details */
                .amdtGroupDetails {{
                    background-color: {bg_color} !important;
                }}

                /* Tables - improved styling */
                table {{
                    border-collapse: collapse !important;
                    width: 100% !important;
                    margin: 1rem 0 !important;
                    font-size: 1rem !important;
                }}

                th {{
                    background-color: {table_header_bg} !important;
                    color: {text_color} !important;
                    font-weight: 600 !important;
                    padding: 0.875rem 1rem !important;
                    border: 1px solid {table_border_color} !important;
                    font-size: 1rem !important;
                    text-align: left !important;
                }}

                td {{
                    padding: 0.875rem 1rem !important;
                    border: 1px solid {table_border_color} !important;
                    color: {text_color} !important;
                    background-color: {bg_color} !important;
                    font-size: 1rem !important;
                    line-height: 1.6 !important;
                }}

                tbody, tr {{
                    background-color: {bg_color} !important;
                }}

                tr:hover {{
                    background-color: {"#2d2e30" if is_dark else "#f6f7f8"} !important;
                }}

                tr:hover td {{
                    background-color: {"#2d2e30" if is_dark else "#f6f7f8"} !important;
                }}

                /* SupTable specific styling - grouped rows */
                table.SupTable {{
                    border-collapse: separate !important;
                    border-spacing: 0 !important;
                }}

                /* Remove vertical borders from all SupTable cells */
                table.SupTable td {{
                    border-left: none !important;
                    border-right: none !important;
                }}

                /* Main data row in SupTable */
                table.SupTable tr.SupTable-Row td {{
                    border-bottom: none !important;
                    padding: 0.625rem 0.875rem !important;
                }}

                /* Subject row (immediately follows SupTable-Row) - no top border */
                table.SupTable tr.SupTable-Row + tr td {{
                    border-top: none !important;
                    padding: 0.375rem 0.875rem 0.75rem 0.875rem !important;
                    font-style: italic !important;
                }}

                /* Subject cell specific styling */
                table.SupTable td.SupTable-Subject-td {{
                    padding-top: 0.25rem !important;
                    padding-bottom: 0.875rem !important;
                    border-top: none !important;
                }}

                /* Add bottom border only after subject row to separate groups */
                table.SupTable tr:has(+ tr.SupTable-Row) td,
                table.SupTable tbody tr:last-child td {{
                    border-bottom: 2px solid {table_border_color} !important;
                }}

                /* SupTable header styling */
                table.SupTable thead tr:first-child th {{
                    background-color: {table_header_bg} !important;
                    font-weight: 600 !important;
                    padding: 0.75rem 0.875rem !important;
                    vertical-align: top !important;
                    border-top: 1px solid {table_border_color} !important;
                    border-bottom: none !important;
                    border-left: none !important;
                    border-right: none !important;
                }}

                /* Second header row - merge with first row visually */
                table.SupTable thead tr:nth-child(2) th {{
                    background-color: {table_header_bg} !important;
                    border-top: none !important;
                    border-bottom: 1px solid {table_border_color} !important;
                    border-left: none !important;
                    border-right: none !important;
                    padding: 0.25rem 0.875rem 0.75rem 0.875rem !important;
                    font-size: 1rem !important;
                    font-weight: 600 !important;
                    font-style: normal !important;
                    color: {text_color} !important;
                    vertical-align: bottom !important;
                }}

                /* Hide the first empty cell in second row */
                table.SupTable thead tr:nth-child(2) th:first-child {{
                    background-color: {table_header_bg} !important;
                    padding: 0 !important;
                }}

                /* Specific column styling for SupTable */
                table.SupTable td.SupTable-NRYear-td {{
                    font-weight: 600 !important;
                    min-width: 120px !important;
                }}

                table.SupTable td.SupTable-Period-td {{
                    min-width: 180px !important;
                }}

                /* Hover effect for grouped rows */
                table.SupTable tr.SupTable-Row:hover td,
                table.SupTable tr.SupTable-Row:hover + tr td {{
                    background-color: {"#2d2e30" if is_dark else "#f6f7f8"} !important;
                }}

                /* Buttons - improved styling */
                button, input[type="button"], input[type="submit"], .button, .btn {{
                    background-color: #1d9be2 !important;
                    color: white !important;
                    border: none !important;
                    border-radius: 6px !important;
                    padding: 0.625rem 1.25rem !important;
                    font-weight: 500 !important;
                    font-size: 1rem !important;
                    cursor: pointer !important;
                    transition: all 0.2s ease !important;
                }}

                button:hover, input[type="button"]:hover, input[type="submit"]:hover, .button:hover, .btn:hover {{
                    background-color: #248bc5 !important;
                    transform: translateY(-1px) !important;
                    box-shadow: 0 4px 8px rgba(29, 155, 226, 0.3) !important;
                }}

                /* Input fields */
                input, select, textarea {{
                    background-color: {input_bg} !important;
                    color: {text_color} !important;
                    border: 1px solid {input_border} !important;
                    padding: 0.625rem !important;
                    font-size: 1rem !important;
                    border-radius: 4px !important;
                }}

                input:focus, select:focus, textarea:focus {{
                    outline: none !important;
                    border-color: #1d9be2 !important;
                    box-shadow: 0 0 0 3px rgba(29, 155, 226, 0.1) !important;
                }}

                /* Code blocks */
                code, pre {{
                    font-family: 'Courier New', Courier, monospace !important;
                    font-size: 0.9375rem !important;
                    background-color: {"#2d2e30" if is_dark else "#f6f7f8"} !important;
                    padding: 0.25rem 0.5rem !important;
                    border-radius: 3px !important;
                }}

                pre {{
                    padding: 1rem !important;
                    overflow-x: auto !important;
                    line-height: 1.5 !important;
                }}

                /* Blockquotes */
                blockquote {{
                    border-left: 4px solid #1d9be2 !important;
                    padding-left: 1rem !important;
                    margin: 1rem 0 !important;
                    font-style: italic !important;
                    color: {text_color} !important;
                    font-size: 1.0625rem !important;
                }}

                /* Custom scrollbar */
                ::-webkit-scrollbar {{
                    width: 8px !important;
                    height: 8px !important;
                }}

                ::-webkit-scrollbar-thumb {{
                    background-color: {"#444646" if is_dark else "#c1c1c1"} !important;
                    border-radius: 4px !important;
                }}

                ::-webkit-scrollbar-thumb:hover {{
                    background-color: {"#5a5c5c" if is_dark else "#a0a0a0"} !important;
                }}

                ::-webkit-scrollbar-track {{
                    background-color: {scrollbar_track_bg} !important;
                }}

                /* Strong emphasis */
                strong, b {{
                    font-weight: 600 !important;
                    color: {heading_color} !important;
                }}

                /* Small text */
                small {{
                    font-size: 0.875rem !important;
                }}

                /* HR dividers */
                hr {{
                    border: none !important;
                    border-top: 1px solid {table_border_color} !important;
                    margin: 1.5rem 0 !important;
                }}

                /* Hide floating menu */
                #floatingMenu {{
                    display: none !important;
                }}
            """
            soup.find("head").append(custom_style_tag)

            # Inject JavaScript for dynamic theme switching via postMessage
            script_tag = soup.new_tag("script")
            script_tag.string = f"""
                // Current theme from server
                const currentTheme = '{theme}';

                // Listen for theme changes from parent window
                window.addEventListener('message', function(event) {{
                    // Security: verify origin if needed
                    // if (event.origin !== 'http://localhost:3002') return;

                    if (event.data && event.data.type === 'THEME_CHANGE') {{
                        const newTheme = event.data.theme;
                        console.log('[GuardianX Iframe] Theme change received:', newTheme);
                        console.log('[GuardianX Iframe] Current theme:', currentTheme);

                        // Only reload if theme actually changed
                        if (newTheme !== currentTheme) {{
                            console.log('[GuardianX Iframe] Theme changed, reloading...');
                            // Store theme for potential page reloads
                            sessionStorage.setItem('guardianx_theme', newTheme);

                            // Apply theme by reloading with theme parameter
                            const url = new URL(window.location.href);
                            url.searchParams.set('theme', newTheme);
                            window.location.href = url.toString();
                        }} else {{
                            console.log('[GuardianX Iframe] Theme unchanged, skipping reload');
                        }}
                    }}
                }});

                // On load, notify parent that iframe is ready (only once)
                let notifiedParent = false;
                window.addEventListener('load', function() {{
                    if (window.parent !== window && !notifiedParent) {{
                        notifiedParent = true;
                        window.parent.postMessage({{
                            type: 'IFRAME_READY',
                            theme: currentTheme
                        }}, '*');
                        console.log('[GuardianX Iframe] Notified parent - ready with theme:', currentTheme);
                    }}

                    // Initialize toggle functionality for navigation tree
                    initToggleNavigation();
                }});

                // Toggle functionality for AIP navigation tree
                const TOGGLE = 'toggle';

                function showHide(id, action) {{
                    const detailsDiv = document.getElementById(id + 'details');
                    const plusLink = document.getElementById(id + 'plus');

                    if (!detailsDiv) return;

                    if (action === TOGGLE) {{
                        if (detailsDiv.style.display === 'none' || detailsDiv.style.display === '') {{
                            detailsDiv.style.display = 'block';
                            if (plusLink) plusLink.textContent = '-';
                        }} else {{
                            detailsDiv.style.display = 'none';
                            if (plusLink) plusLink.textContent = '+';
                        }}
                    }}
                }}

                function initToggleNavigation() {{
                    // Find all .Hx elements with .Plus children
                    const hxElements = document.querySelectorAll('.Hx');

                    hxElements.forEach(hx => {{
                        const plusLink = hx.querySelector('a.Plus');
                        if (!plusLink) return;

                        // Extract ID from the plus link
                        const plusId = plusLink.id;
                        if (!plusId || !plusId.endsWith('plus')) return;

                        const baseId = plusId.replace('plus', '');
                        const detailsDiv = document.getElementById(baseId + 'details');

                        if (!detailsDiv) return;

                        // Add click handler to the entire Hx div
                        hx.style.cursor = 'pointer';
                        hx.addEventListener('click', function(e) {{
                            e.preventDefault();
                            e.stopPropagation();
                            showHide(baseId, TOGGLE);
                        }});

                        // Prevent default on Plus link
                        plusLink.addEventListener('click', function(e) {{
                            e.preventDefault();
                            e.stopPropagation();
                        }});
                    }});
                }}
            """
            soup.find("head").append(script_tag)

        return str(soup).encode("utf-8")

    except Exception as e:
        # fallback: return original bytes so we don't break
        #print("rewrite_html ERROR:", e)
        return html_bytes


def safe_filename_from_url(url):
    try:
        path = urlparse(url).path
        name = path.split('/')[-1] or "file"
        # decode percent-encoding
        return unquote(name)
    except Exception:
        return "file"