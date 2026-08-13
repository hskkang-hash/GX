import os
import re
import tempfile
from typing import Optional
from datetime import datetime
import html

from bs4 import BeautifulSoup
from common.utils import decode_template_html_entities
from django.core.files.base import ContentFile
from django.template import Template, Context
from htmldocx import HtmlToDocx
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
from django.template import Template, Context as DjContext
from core.file_management.helper import FileHelper
from print_format.views import PrintFormatController
from print_format.services import PrintFormatService
from report_template.models import ReportTemplate


def generate_report_template(request, data, template_type="pdf", operation_id=None, group_id=None):
    """
    Generate a report template for an order.

    Args:
        request: Django request object
        data: Data to be used in the template
        template_type: Type of template to generate (pdf or docx)

    Returns:
        dict: Dictionary containing the file URL and success status
    """
    
    html_template = get_report_template_default_with_data(data, group_id)
    html_template = decode_template_html_entities(html_template)
    
    if template_type == "pdf" and html_template:
        pdf_file = None
        try:
            pdf_file = generate_pdf_report_template(html_template)
            # Read the content of the file
            pdf_content = pdf_file.read()

            # Create a Django ContentFile
            filename = f"report-{operation_id}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.pdf"
            file_obj = ContentFile(pdf_content, name=filename)
            file_url = upload_file_to_s3(request, file_obj)
            return {
                "file_url": file_url,
                "success": True,
            }
        except (RuntimeError, ValueError) as e:
            print(f"Error in generate_report_template: {str(e)}")
            return {
                "file_url": None,
                "success": False,
                "message": str(e),
            }
        finally:
            # Clean up: close and remove the temporary file
            if pdf_file:
                try:
                    temp_file_path = pdf_file.name
                    pdf_file.close()
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    print(f"Warning: Error during cleanup: {cleanup_error}")

    elif template_type == "docx" and html_template:
        try:
            # Convert HTML -> DOCX
            docx_file = generate_docx_report_template(html_template)

            # Create a Django ContentFile
            filename = f"report-{operation_id}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.docx"
            file_obj = ContentFile(docx_file, name=filename)
            file_url = upload_file_to_s3(request, file_obj)
            return {
                "file_url": file_url,
                "success": True,
            }
        except (RuntimeError, ValueError) as e:
            return {
                "file_url": None,
                "success": False,
                "message": str(e),
            }
    else:
        return {
            "file_url": None,
            "success": False,
            "message": f"Invalid template type: {template_type}",
        }


def get_report_template_default_with_data(data, group_id):
    """
    Get the data for a report template.

    Args:
        data: Data to be used in the template

    Returns:
        str: Rendered HTML content
    """
    try:
        default_template_obj = ReportTemplate._base_manager.filter(is_default=True, is_enabled=True, group=group_id).first()
        default_template = default_template_obj.template
        default_template = decode_template_html_entities(default_template)
        # Validate template content
            
        
    except ReportTemplate.DoesNotExist:

        # Fallback to a simple default template if no default template exists
        default_template = """<style>
  /* Font family for multilingual support including Korean */
  .tiptap-preview {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 'Gulim', 'Dotum', 'Arial Unicode MS', 'Arial', sans-serif;
  }
  
  /* Headings */
.tiptap-preview h1,
.tiptap-preview h2,
.tiptap-preview h3,
.tiptap-preview h4,
.tiptap-preview h5,
.tiptap-preview h6 {
  font-weight: bold;
  line-height: 1.5;
  overflow-wrap: break-word;
  page-break-inside: avoid;
  break-inside: avoid;
  text-wrap: balance;
  font-family: 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 'Gulim', 'Dotum', 'Arial Unicode MS', 'Arial', sans-serif;
}

.tiptap-preview h1 {
  font-size: 2.5rem;
}

.tiptap-preview h2 {
  font-size: 2rem;
}

.tiptap-preview h3 {
  font-size: 1.75rem;
}

.tiptap-preview h4 {
  font-size: 1.5rem;
}

.tiptap-preview h5 {
  font-size: 1.25rem;
}

.tiptap-preview h6 {
  font-size: 1rem;
}

.tiptap-preview p {
  margin: 0.5rem 0;
  font-size: 1.25rem;
  overflow-wrap: break-word;
  -webkit-user-modify: read-write-plaintext-only;
  font-family: 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 'Gulim', 'Dotum', 'Arial Unicode MS', 'Arial', sans-serif;
}

.tiptap-preview ul, .tiptap-preview ol {
  padding: 0 1rem;
  margin: 0.5rem 0;
}

.tiptap-preview ul li, .tiptap-preview ol li {
  padding: 0.2em 0;
}

.tiptap-preview ul li p, .tiptap-preview ol li p {
  margin: 0.25em 0;
}

.tiptap-preview table {
  border-collapse: collapse;
  margin: 0.5rem 0;
  overflow: hidden;
  table-layout: fixed;
  width: 100%;
}

.tiptap-preview table.hide-table-borders td, 
.tiptap-preview table.hide-table-borders th {
  border: none;
}

.tiptap-preview table td, .tiptap-preview table th {
  border: 1px solid #ced4da;
  padding: 3px 5px;
  vertical-align: top;
  box-sizing: border-box;
  min-width: 1em;
  position: relative;
  font-family: 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 'Gulim', 'Dotum', 'Arial Unicode MS', 'Arial', sans-serif;
}

.tiptap-preview table td p, .tiptap-preview table th p {
  margin: 0;
  overflow-wrap: break-word;
  -webkit-user-modify: read-write-plaintext-only;
}

.tiptap-preview table th {
  background-color: #f1f3f5;
  font-weight: bold;
  text-align: left;
}

.tiptap-preview table td > *, .tiptap-preview table th > * {
  margin-bottom: 0;
}

.tiptap-preview blockquote {
  border-left: 3px solid #f2f2f2;
  margin: 0.5rem 0;
  padding-left: 1rem;
}

.tiptap-preview code {
  background-color: #f8f9fa;
  border-radius: 4px;
  color: #212529;
  font-size: 0.85rem;
  font-family: 'JetBrainsMono', monospace;
  padding: 0.25em 0.3em;
}

.tiptap-preview pre {
  background: #f8f9fa;
  font-family: 'JetBrainsMono', monospace;
  border-radius: 0.5rem;
  margin: 0.5rem 0;
  padding: 0.75rem 1rem;
  overflow-x: auto;
}

.tiptap-preview pre code {
  background: none;
  color: inherit;
  font-size: 0.8rem;
  padding: 0;
}

.tiptap-preview hr {
  border: none;
  border-top: 1px solid #ced4da;
  margin: 0.5rem 0;
}

.tiptap-preview a {
  color: #4a6cfa;
  text-decoration: underline;
}

.tiptap-preview a:hover {
  text-decoration: none;
}

.tiptap-preview img {
  max-width: 100%;
  height: auto;
  cursor: pointer;
}

.tiptap-preview .image-wrapper {
  display: flex;
}

.hide-table-borders table tbody td{
   border: none;
}
</style>

<div class="tiptap-preview">
  <p style="text-align: right;"><br><br></p>
  
  <h1 style="text-align: center;"><strong>Delivery Completion Report</strong></h1>
  
  <p style="text-align: left;"><span style="font-size: 14px;"><strong>Operation ID:</strong> {{ id|default:"N/A" }}</span></p>
  
  <p style="text-align: left;"><span style="font-size: 14px;"><strong>Order Information</strong></span></p>
  <ul>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Order Code:</strong> {{ order__order_code|default:"N/A" }}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Order ID:</strong> {{ order__id|default:"N/A" }}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Created Date:</strong> {{ order__created_on|default:"N/A" }}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Modified Date:</strong> {{ order__modified_on|default:"N/A" }}</span></p></li>
  </ul>
  
  <p style="text-align: left;"><span style="font-size: 14px;"><strong>Sender</strong></span></p>
  <ul>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Name:</strong> {{ order__sender_name|default:"N/A" }}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Phone:</strong> {{ order__sender_phone|default:"N/A" }}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Address:</strong> {% if order__sender_address__full_address %}{{ order__sender_address__full_address }}{% elif order__pickup_location__name %}{{ order__pickup_location__name }}{% else %}N/A{% endif %}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>City:</strong> {% if order__sender_address__city %}{{ order__sender_address__city }}{% elif order__pickup_location__city_province %}{{ order__pickup_location__city_province }}{% else %}N/A{% endif %}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>District:</strong> {% if order__sender_address__district %}{{ order__sender_address__district }}{% elif order__pickup_location__city_county_district %}{{ order__pickup_location__city_county_district }}{% else %}N/A{% endif %}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Ward:</strong> {% if order__sender_address__ward %}{{ order__sender_address__ward }}{% elif order__pickup_location__ward_town_township %}{{ order__pickup_location__ward_town_township }}{% else %}N/A{% endif %}</span></p></li>
    <li><p style="text-align: left;"><span style="font-size: 14px;"><strong>Note:</strong> {{ order__sender_note|default:"N/A" }}</span></p></li>
  </ul>
  
  <p style="text-align: left;"><span style="font-size: 14px;"><strong>Recipient</strong></span></p>
  <ul>
    <li><p><span style="font-size: 14px;"><strong>Name:</strong> {{ order__recipient_name|default:"N/A" }}</span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Phone:</strong> {{ order__recipient_phone|default:"N/A" }}</span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Address:</strong> 
      {% if order__delivery_option__code == "delivery_to_door" %}
        {{ order__recipient_address__full_address|default:"N/A" }}
      {% elif order__delivery_option__code == "collect_at_location" %}
        {{ order__delivery_terminal__name|default:"N/A" }}
      {% else %}
        N/A
      {% endif %}
    </span></p></li>
    <li><p><span style="font-size: 14px;"><strong>City:</strong> 
      {% if order__delivery_option__code == "delivery_to_door" %}
        {{ order__recipient_address__city|default:"N/A" }}
      {% elif order__delivery_option__code == "collect_at_location" %}
        {{ order__delivery_terminal__city_province|default:"N/A" }}
      {% else %}
        N/A
      {% endif %}
    </span></p></li>
    <li><p><span style="font-size: 14px;"><strong>District:</strong> 
      {% if order__delivery_option__code == "delivery_to_door" %}
        {{ order__recipient_address__district|default:"N/A" }}
      {% elif order__delivery_option__code == "collect_at_location" %}
        {{ order__delivery_terminal__city_county_district|default:"N/A" }}
      {% else %}
        N/A
      {% endif %}
    </span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Ward:</strong> 
      {% if order__delivery_option__code == "delivery_to_door" %}
        {{ order__recipient_address__ward|default:"N/A" }}
      {% elif order__delivery_option__code == "collect_at_location" %}
        {{ order__delivery_terminal__ward_town_township|default:"N/A" }}
      {% else %}
        N/A
      {% endif %}
    </span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Note:</strong> {{ order__recipient_note|default:"N/A" }}</span></p></li>
  </ul>
  
  
  
  <p style="text-align: left;"><span style="font-size: 14px;"><strong>Financial Information</strong></span></p>
  <ul>
    <li><p><span style="font-size: 14px;"><strong>Subtotal:</strong> {{ order__subtotal|default:"N/A" }}</span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Delivery Fee:</strong> {{ order__delivery_fee|default:"N/A" }}</span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Tax Amount:</strong> {{ order__tax_amount|default:"N/A" }}</span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Discount Amount:</strong> {{ order__discount_amount|default:"N/A" }}</span></p></li>
    <li><p><span style="font-size: 14px;"><strong>Total Amount:</strong> {{ order__total_amount|default:"N/A" }}</span></p></li>
  </ul>
  
  <p><br><br></p>
</div>"""

    if not default_template:
        return None


    
    # Ensure all required fields have default values if missing
    template_data = {
        # Default values for common fields
        'id': data.get('id', 'N/A'),
        'created_on': data.get('created_on', 'N/A'),
        'modified_on': data.get('modified_on', 'N/A'),
        'current_status__name': data.get('current_status__name', 'N/A'),
        'current_status__code': data.get('current_status__code', 'N/A'),
        'current_status__description': data.get('current_status__description', 'N/A'),
        'is_partial_approved': data.get('is_partial_approved', False),
        
        # Order fields
        'order__id': data.get('order__id', 'N/A'),
        'order__order_code': data.get('order__order_code', 'N/A'),
        'order__created_on': data.get('order__created_on', 'N/A'),
        'order__modified_on': data.get('order__modified_on', 'N/A'),
        'order__status__name': data.get('order__status__name', 'N/A'),
        
        # Sender fields
        'order__sender_name': data.get('order__sender_name', 'N/A'),
        'order__sender_phone': data.get('order__sender_phone', 'N/A'),
        'order__sender_note': data.get('order__sender_note', 'N/A'),
        
        # Recipient fields
        'order__recipient_name': data.get('order__recipient_name', 'N/A'),
        'order__recipient_phone': data.get('order__recipient_phone', 'N/A'),
        'order__recipient_address': data.get('order__recipient_address', 'N/A'),
        'order__recipient_note': data.get('order__recipient_note', 'N/A'),
        
        # Pickup location
        'order__pickup_location': data.get('order__pickup_location', 'N/A'),
        
        # Route fields
        'route__id': data.get('route__id', 'N/A'),
        'route__name': data.get('route__name', 'N/A'),
        'route__code': data.get('route__code', 'N/A'),
        'route__total_stops': data.get('route__total_stops', 'N/A'),
        'route__status': data.get('route__status', 'N/A'),
        
        # Financial fields
        'order__subtotal': data.get('order__subtotal', 'N/A'),
        'order__delivery_fee': data.get('order__delivery_fee', 'N/A'),
        'order__tax_amount': data.get('order__tax_amount', 'N/A'),
        'order__discount_amount': data.get('order__discount_amount', 'N/A'),
        'order__total_amount': data.get('order__total_amount', 'N/A'),
        
        # Report template info
        'report_template_name': data.get('report_template_name', 'Default Report Template'),
        'report_template_id': data.get('report_template_id', 'N/A'),
    }
    
    # Merge with original data (original data takes precedence)
    template_data.update(data)
    template_str = PrintFormatService.normalize_template_content(default_template)
    try:
        rendered_html = PrintFormatController.render_jinja2_template(template_str, template_data)
    except Exception as e:
        print(e)
        template = Template(template_str)
        rendered_html = template.render(DjContext(template_data))
        
    
    from django.utils.safestring import mark_safe
    import re
    
    # Remove all escaped quotes that break CSS
    rendered_html = re.sub(r'\\"', '"', rendered_html)
    rendered_html = re.sub(r"\\'", "'", rendered_html)
    
    # Also fix any remaining escaped characters
    rendered_html = rendered_html.replace('\\n', ' ')
    rendered_html = rendered_html.replace('\\r', ' ')
    rendered_html = rendered_html.replace('\\t', ' ')
    
    rendered_html = mark_safe(rendered_html)
    return rendered_html


def upload_file_to_s3(request, file):
    """
    Upload a file to S3 and return the full URL.

    Args:
        request: Django request object
        file: File object to upload

    Returns:
        str: Full URL of the uploaded file
    """

    saved_file = FileHelper.user_upload_s3(
        request.user, file, feature_path="OrderReports"
    )

    if not saved_file:
        raise ValueError("Failed to upload file")

    return saved_file.full_url


def clean_template_for_pdf(html_content, optimize_performance=True):
    """
    Clean up HTML template to ensure all content is visible in PDF with Korean font support
    and proper layout preservation. Optimized for performance to avoid system overload.
    
    Args:
        html_content (str): Raw HTML content to clean
        optimize_performance (bool): Enable performance optimizations (default: True)
    
    Returns:
        str: Cleaned HTML content
    """
    from bs4 import BeautifulSoup
    import re
    import time
    
    start_time = time.time()
    
    # Performance optimization: Limit HTML size to prevent system overload
    if optimize_performance and len(html_content) > 1000000:  # 1MB limit
        print(f"Warning: HTML content is very large ({len(html_content)} chars). Truncating for performance.")
        html_content = html_content[:1000000]
    
    # Performance optimization: Use faster regex patterns
    if optimize_performance:
        # Batch regex operations for better performance
        patterns_to_remove = [
            (r'<br\s+class="[^"]*"[^>]*>', ''),  # ProseMirror breaks
            (r'<span[^>]*style="[^"]*font-size:\s*10pt[^"]*"[^>]*>\s*</span>', ''),  # Empty font spans
            (r'<p[^>]*>\s*<br[^>]*>\s*</p>', ''),  # Empty paragraphs with breaks
            (r'<p[^>]*>\s*</p>', ''),  # Empty paragraphs
            (r'<div[^>]*>\s*</div>', ''),  # Empty divs
            (r'<span[^>]*>\s*</span>', ''),  # Empty spans
            (r'\n\s*\n\s*\n', '\n\n'),  # Multiple newlines
            (r'\s{3,}', ' '),  # Multiple spaces
            (r'>\s+<', '><'),  # Whitespace between tags
            (r'\s+>', '>'),  # Whitespace before closing tag
            (r'>\s+', '>'),  # Whitespace after opening tag
        ]
        
        for pattern, replacement in patterns_to_remove:
            html_content = re.sub(pattern, replacement, html_content)
    else:
        # Standard cleaning for smaller HTML content
        html_content = re.sub(r'<br\s+class="[^"]*"[^>]*>', '', html_content)
        html_content = re.sub(r'<span[^>]*style="[^"]*font-size:\s*10pt[^"]*"[^>]*>\s*</span>', '', html_content)
        html_content = re.sub(r'<p[^>]*>\s*<br[^>]*>\s*</p>', '', html_content)
        html_content = re.sub(r'<p[^>]*>\s*</p>', '', html_content)
        html_content = re.sub(r'<div[^>]*>\s*</div>', '', html_content)
        html_content = re.sub(r'<span[^>]*>\s*</span>', '', html_content)
        html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)
        html_content = re.sub(r'\s{3,}', ' ', html_content)
        html_content = re.sub(r'>\s+<', '><', html_content)
        html_content = re.sub(r'\s+>', '>', html_content)
        html_content = re.sub(r'>\s+', '>', html_content)
    
    # Ensure proper encoding
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8')
    
    # Add meta charset if not present
    if '<meta charset=' not in html_content and '<meta http-equiv="Content-Type"' not in html_content:
        html_content = html_content.replace('<head>', '<head><meta charset="utf-8">')
        if '<head>' not in html_content:
            html_content = html_content.replace('<html>', '<html><head><meta charset="utf-8"></head>')
    
    # Simple and effective HTML cleaning - Remove escape characters and artifacts
    # Remove backslashes and escape characters that break styling
    html_content = html_content.replace('\\', '')
    
    # Remove ProseMirror artifacts that cause layout issues
    html_content = re.sub(r'<br\s+class="[^"]*"[^>]*>', '', html_content)
    html_content = re.sub(r'<span[^>]*style="[^"]*font-size:\s*10pt[^"]*"[^>]*>\s*</span>', '', html_content)
    
    # Remove empty elements that cause spacing issues
    html_content = re.sub(r'<p[^>]*>\s*</p>', '', html_content)  # Empty paragraphs
    html_content = re.sub(r'<div[^>]*>\s*</div>', '', html_content)  # Empty divs
    html_content = re.sub(r'<span[^>]*>\s*</span>', '', html_content)  # Empty spans
    
    # Clean up excessive whitespace
    html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)  # Multiple newlines
    html_content = re.sub(r'\s{3,}', ' ', html_content)  # Multiple spaces
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Simple cleanup - Keep styles but remove problematic elements
    # Remove only the most problematic elements that break PDF rendering
    for element in soup.find_all(['br']):
        if element.get('class') and any('ProseMirror' in cls for cls in element.get('class', [])):
            element.decompose()
    
    # Remove empty spans with font-size: 10pt
    for span in soup.find_all('span'):
        if span.get('style') and 'font-size: 10pt' in span.get('style', ''):
            if not span.get_text(strip=True):
                span.decompose()
    
    # Remove completely empty paragraphs
    for p in soup.find_all('p'):
        if not p.get_text(strip=True) or p.get_text(strip=True) == '&nbsp;':
            p.decompose()
    
    # Simple table cleanup - Keep structure but remove empty content
    for table in soup.find_all('table'):
        # Remove completely empty rows
        for tr in table.find_all('tr'):
            if not tr.get_text(strip=True):
                tr.decompose()
        
        # Clean up table cells - remove empty content but keep structure
        for td in table.find_all(['td', 'th']):
            # Remove empty paragraphs and spans
            for p in td.find_all(['p', 'span']):
                if p.get_text(strip=True) == '':
                    p.decompose()
    
    # Simple list cleanup
    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            if not li.get_text(strip=True):
                li.decompose()
    
    # Simple heading cleanup
    for i in range(1, 7):
        for h in soup.find_all(f'h{i}'):
            # Remove only completely empty headings
            if not h.get_text(strip=True):
                h.decompose()
    
    # Performance monitoring
    if optimize_performance:
        end_time = time.time()
        processing_time = end_time - start_time
        if processing_time > 5.0:
            print(f"Warning: HTML cleaning took {processing_time:.2f} seconds.")
    
    # Simple font support for Korean text - Keep existing styles
    font_face_css = """
    /* Korean Font Support - Simple and Lightweight */
    
    /* Basic Korean font fallbacks */
    * {
        font-family: 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 'Arial Unicode MS', 'Arial', sans-serif !important;
    }
    
    /* Ensure Korean text renders properly */
    [lang="ko"], [lang="ko-KR"] {
        font-family: 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', sans-serif !important;
    }
    
    /* Basic table styling for PDF */
    table {
        border-collapse: collapse !important;
        width: 100% !important;
    }
    
    table td, table th {
        border: 1px solid #000 !important;
        padding: 4px !important;
    }
    
    /* Remove problematic elements */
    .ProseMirror-trailingBreak {
        display: none !important;
    }
    """
    
    # Create a new style tag for font faces
    font_face_tag = soup.new_tag('style')
    font_face_tag.string = font_face_css
    
    # Safely insert font tag into head or html
    if soup.head:
        soup.head.insert(0, font_face_tag)
    elif soup.html:
        soup.html.insert(0, font_face_tag)
    else:
        # If neither head nor html exists, create a head tag
        head_tag = soup.new_tag('head')
        head_tag.insert(0, font_face_tag)
        if soup.body:
            soup.body.insert_before(head_tag)
        else:
            # If no body either, insert at the beginning
            soup.insert(0, head_tag)
    
    # Remove any CSS that might hide content
    style_tags = soup.find_all('style')
    for style_tag in style_tags:
        if style_tag != font_face_tag:  # Skip the font-face tag we just added
            css_content = style_tag.string
            if css_content:
                # Remove any display: none, visibility: hidden, or opacity: 0
                css_content = css_content.replace('display: none', 'display: block')
                css_content = css_content.replace('visibility: hidden', 'visibility: visible')
                css_content = css_content.replace('opacity: 0', 'opacity: 1')
                style_tag.string = css_content
    
    # Ensure all elements are visible
    for element in soup.find_all():
        if element.get('style'):
            style = element['style']
            style = style.replace('display: none', 'display: block')
            style = style.replace('visibility: hidden', 'visibility: visible')
            style = style.replace('opacity: 0', 'opacity: 1')
            element['style'] = style
    
    # Minimal styling - Keep existing styles, just add Korean font support
    for element in soup.find_all(['div', 'p', 'span', 'table', 'tr', 'td', 'th', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        # Only add font-family if not already present
        if not element.get('style') or 'font-family' not in element.get('style', ''):
            if not element.get('style'):
                element['style'] = 'font-family: "Noto Sans KR", "Malgun Gothic", "AppleGothic", "Arial Unicode MS", "Arial", sans-serif;'
            else:
                element['style'] += '; font-family: "Noto Sans KR", "Malgun Gothic", "AppleGothic", "Arial Unicode MS", "Arial", sans-serif;'
    
    # Simple table styling - only if no existing styles
    for table in soup.find_all('table'):
        if not table.get('style'):
            table['style'] = 'border-collapse: collapse; width: 100%;'
        
        for cell in table.find_all(['td', 'th']):
            if not cell.get('style'):
                cell['style'] = 'border: 1px solid #000; padding: 4px;'
    
    return str(soup)

def create_korean_font_config(fonts_dir="fonts"):
    """
    Create a comprehensive font configuration for Korean text support in WeasyPrint.
    Uses downloaded fonts from the specified fonts directory.
    
    Args:
        fonts_dir (str): Path to fonts directory (default: "fonts")
    
    Returns:
        FontConfiguration: Configured font configuration object
    """
    try:
        # Create font configuration
        font_config = FontConfiguration()
        
        # Check if fonts directory exists
        import os
        from pathlib import Path
        
        fonts_path = Path(fonts_dir)
        if not fonts_path.exists():
            print(f"Warning: Fonts directory {fonts_dir} not found. Using system fonts.")
            return create_system_font_config()
        
        # Load font mapping if available
        font_mapping_file = fonts_path / 'font_mapping.json'
        if font_mapping_file.exists():
            try:
                import json
                with open(font_mapping_file, 'r', encoding='utf-8') as f:
                    font_data = json.load(f)
                
                # Register downloaded fonts
                for font_name, font_path in font_data.get('downloaded_fonts', {}).items():
                    try:
                        # font_path is already a string path
                        if os.path.exists(font_path):
                            # Use absolute path and provide url_fetcher parameter
                            abs_font_path = os.path.abspath(font_path)
                            font_config.add_font_face(abs_font_path, url_fetcher=None)
                            print(f"✓ Registered font: {font_name}")
                        else:
                            print(f"⚠️  Font file not found: {font_path}")
                    except Exception as e:
                        print(f"✗ Failed to register font {font_name}: {e}")
                        continue
                
                print(f"Successfully registered {len(font_data.get('downloaded_fonts', {}))} fonts from {fonts_dir}")
                return font_config
                
            except Exception as e:
                print(f"Warning: Could not load font mapping: {e}")
        
        # Fallback: manually register fonts from directory
        print("Registering fonts manually from fonts directory...")
        registered_count = 0
        
        for font_file in fonts_path.glob('*'):
            if font_file.is_file() and font_file.suffix.lower() in ['.ttf', '.otf', '.ttc']:
                try:
                    # Use absolute path and provide url_fetcher parameter
                    abs_font_path = str(font_file.absolute())
                    font_config.add_font_face(abs_font_path, url_fetcher=None)
                    print(f"✓ Registered font file: {font_file.name}")
                    registered_count += 1
                except Exception as e:
                    print(f"✗ Failed to register font file {font_file.name}: {e}")
                    continue
        
        if registered_count > 0:
            print(f"Successfully registered {registered_count} fonts manually")
            return font_config
        else:
            print("No fonts could be registered from fonts directory. Falling back to system fonts.")
            return create_system_font_config()
            
    except Exception as e:
        print(f"Warning: Could not create font configuration from {fonts_dir}: {e}")
        return create_system_font_config()

def create_system_font_config():
    """
    Create font configuration using system fonts as fallback.
    
    Returns:
        FontConfiguration: Configured font configuration object
    """
    try:
        font_config = FontConfiguration()
        
        # System Korean fonts
        system_fonts = [
            'Noto Sans KR', 'Malgun Gothic', '맑은 고딕', 'Gulim', '굴림',
            'Dotum', '돋움', 'Batang', '바탕', 'AppleGothic', 'Apple SD Gothic Neo',
            'Nanum Gothic', '나눔고딕', 'Nanum Myeongjo', '나눔명조',
            'Arial Unicode MS', 'Arial'
        ]
        
        # Try to register system fonts
        for font_name in system_fonts:
            try:
                import subprocess
                
                # Check if font exists using fc-list (fontconfig)
                try:
                    result = subprocess.run(['fc-list', font_name], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        font_config.add_font_face(font_name, url_fetcher=None)
                        print(f"✓ Registered system font: {font_name}")
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                    pass
                    
            except Exception as e:
                print(f"Warning: Error processing system font {font_name}: {e}")
                continue
        
        return font_config
        
    except Exception as e:
        print(f"Warning: Could not create system font configuration: {e}")
        return FontConfiguration()

def download_and_install_korean_fonts():
    """
    Download and install Korean fonts for better PDF generation.
    This function can be called during system setup or first run.
    """
    import urllib.request
    import tempfile
    import shutil
    import os
    
    # Font URLs for Korean fonts
    font_urls = {
        'Noto Sans KR': 'https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR-Regular.otf',
        'Nanum Gothic': 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf',
        'Nanum Myeongjo': 'https://github.com/google/fonts/raw/main/ofl/nanummyeongjo/NanumMyeongjo-Regular.ttf'
    }
    
    # Font installation directories
    font_dirs = [
        '/usr/share/fonts/truetype/korean',
        '/usr/local/share/fonts/korean',
        os.path.expanduser('~/.fonts/korean')
    ]
    
    for font_name, font_url in font_urls.items():
        try:
            # Create font directory if it doesn't exist
            for font_dir in font_dirs:
                os.makedirs(font_dir, exist_ok=True)
                
                # Download font file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as temp_file:
                    urllib.request.urlretrieve(font_url, temp_file.name)
                    
                    # Copy to font directory
                    font_filename = os.path.basename(font_url)
                    font_path = os.path.join(font_dir, font_filename)
                    shutil.copy2(temp_file.name, font_path)
                    
                    # Clean up temp file
                    os.unlink(temp_file.name)
                    
                    print(f"Successfully installed {font_name} to {font_path}")
                    break
                    
        except Exception as e:
            print(f"Warning: Could not install {font_name}: {e}")
            continue
    
    # Refresh font cache
    try:
        import subprocess
        subprocess.run(['fc-cache', '-f', '-v'], check=True)
        print("Font cache refreshed successfully")
    except Exception as e:
        print(f"Warning: Could not refresh font cache: {e}")

def test_korean_font_support():
    """
    Test if Korean fonts are properly supported in the system.
    This can be used to diagnose font issues.
    """
    try:
        import subprocess
        import json
        
        # Check available fonts using fc-list
        result = subprocess.run(['fc-list', '--format=json'], 
                              capture_output=True, text=True, check=True)
        
        fonts = json.loads(result.stdout)
        korean_fonts = []
        
        # Look for Korean fonts
        for font in fonts:
            font_name = font.get('family', '')
            if any(korean_char in font_name for korean_char in ['가', '나', '다', '라', '마', '바', '사', '아', '자', '차', '카', '타', '파', '하']):
                korean_fonts.append(font_name)
        
        print(f"Found {len(korean_fonts)} Korean fonts:")
        for font in korean_fonts:
            print(f"  - {font}")
        
        if not korean_fonts:
            print("No Korean fonts found. Consider installing fonts using download_and_install_korean_fonts()")
        
        return korean_fonts
        
    except Exception as e:
        print(f"Error checking font support: {e}")
        return []

_CACHED_KOREAN_FONT_CONFIG = None


def get_cached_korean_font_config(fonts_dir: str = "fonts"):
    """
    Cache FontConfiguration at process-level to avoid rebuilding for every PDF.
    Thread-safe enough for our use (read-mostly).
    """
    global _CACHED_KOREAN_FONT_CONFIG
    if _CACHED_KOREAN_FONT_CONFIG is None:
        _CACHED_KOREAN_FONT_CONFIG = create_korean_font_config(fonts_dir)
    return _CACHED_KOREAN_FONT_CONFIG


def generate_pdf_report_template(template, *, font_config=None, jpeg_quality: int = 95):
    """
    Generate a PDF file from a HTML template with full Korean font support.

    Args:
        template: Rendered HTML content

    Returns:
        file: Temporary PDF file object
    """
    temp_file = None
    pdf_file = None
    
    try:
        # Clean template for PDF generation with performance optimization
        print("Cleaning HTML template for PDF generation...")
        # cleaned_template = clean_template_for_pdf(template, optimize_performance=True)
        cleaned_template = template
        print(f"HTML cleaned successfully. Original size: {len(template)}, Cleaned size: {len(cleaned_template)}")
        
        # Reuse cached font configuration unless explicitly provided
        if font_config is None:
            font_config = get_cached_korean_font_config("fonts")
        
        # Create HTML object with font configuration and proper encoding
        html = HTML(
            string=cleaned_template,
            base_url=None,  # Disable base_url to avoid external font loading issues
            encoding='utf-8'  # Ensure UTF-8 encoding
        )
        
        # Additional HTML preprocessing for better PDF rendering
        # Remove any remaining problematic elements
        # cleaned_template = re.sub(r'<br\s+class="[^"]*"[^>]*>', '<br>', cleaned_template)
        # cleaned_template = re.sub(r'<span[^>]*style="[^"]*font-size:\s*10pt[^"]*"[^>]*>\s*</span>', '', cleaned_template)
        # cleaned_template = re.sub(r'<p[^>]*>\s*<br[^>]*>\s*</p>', '', cleaned_template)
        
        # Recreate HTML object with cleaned template
        html = HTML(
            string=cleaned_template,
            base_url=None,
            encoding='utf-8'
        )

        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

        try:
            # Generate PDF with comprehensive font configuration and Korean text optimization
            html.write_pdf(
                target=temp_file.name, 
                font_config=font_config,
                optimize_images=True,
                jpeg_quality=jpeg_quality,
                # Additional options for better Korean text rendering
                presentational_hints=True,  # Better text layout
                zoom=1.0,  # Maintain original size
                # Font fallback options
                font_fallback=True,
                # Text rendering options
                text_rendering='optimizeLegibility'
            )

            # Close and reopen the file in binary read mode
            temp_file.close()
            pdf_file = open(temp_file.name, "rb")

            # Return the file object
            return pdf_file

        except Exception as e:
            # Clean up the temporary file in case of error
            if temp_file:
                temp_file.close()
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
            raise e

    except Exception as e:
        # Clean up any remaining temporary files
        if temp_file and os.path.exists(temp_file.name):
            try:
                temp_file.close()
                os.unlink(temp_file.name)
            except:
                pass
        raise RuntimeError(f"Error generating PDF: {str(e)}") from e


def generate_pdf_report_template_chromium(
    template: str,
    *,
    timeout_ms: int = 30000,
    wait_after_load_ms: int = 750,
) -> Optional[bytes]:
    """
    Render PDF with headless Chromium (Playwright) to match FE layout 1:1.
    Returns PDF bytes or None if Chromium/Playwright is unavailable.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()
            page.set_content(template, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(wait_after_load_ms)
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
            )
            browser.close()
            return pdf_bytes
    except Exception:
        return None


def generate_docx_report_template(template):
    """
    Generate a DOCX file from a HTML template.

    Args:
        template: Rendered HTML content

    Returns:
        file: Temporary DOCX file object
    """

    try:
        # Step 1: Convert CSS styles to inline styles
        processed_html = convert_css_to_inline_styles(template)

        # Create a new document with Korean font support
        new_parser = HtmlToDocx()
        
        # Configure parser for better Korean text handling
        new_parser.table_style = 'Table Grid'
        new_parser.paragraph_style = 'Normal'
        
        # Parse HTML and create DOCX
        docx = new_parser.parse_html_string(processed_html)

        # Save to temporary file
        temp_docx_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        temp_docx_path = temp_docx_file.name
        temp_docx_file.close()

        # Save the document
        docx.save(temp_docx_path)

        # Read the DOCX file content
        with open(temp_docx_path, "rb") as docx_file:
            docx_content = docx_file.read()

        return docx_content

    except Exception as e:
        raise RuntimeError(f"Error generating DOCX: {str(e)}") from e

    finally:
        # Clean up temporary files
        if "temp_docx_path" in locals() and os.path.exists(temp_docx_path):
            os.unlink(temp_docx_path)


def convert_css_to_inline_styles(html_content):
    """
    Convert CSS styles to inline styles.

    Args:
        html_content: HTML content

    Returns:
        str: HTML content with inline styles
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # ⚠️ Remove unused <br class="ProseMirror-trailingBreak">
    for br in soup.find_all("br", class_="ProseMirror-trailingBreak"):
        br.decompose()

    # Add Korean font support CSS
    korean_font_css = """
    /* Korean Font Support for DOCX */
    .tiptap-preview,
    .tiptap-preview h1,
    .tiptap-preview h2,
    .tiptap-preview h3,
    .tiptap-preview h4,
    .tiptap-preview h5,
    .tiptap-preview h6,
    .tiptap-preview p,
    .tiptap-preview span,
    .tiptap-preview div,
    .tiptap-preview li,
    .tiptap-preview td,
    .tiptap-preview th {
        font-family: 'Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 'Apple SD Gothic Neo', 
                     'Nanum Gothic', 'Nanum Myeongjo', 'Gulim', 'Dotum', 'Batang', 
                     'Arial Unicode MS', 'Arial', sans-serif;
    }
    """
    
    # Create a new style tag for Korean fonts
    korean_font_tag = soup.new_tag('style')
    korean_font_tag.string = korean_font_css
    soup.head.insert(0, korean_font_tag) if soup.head else soup.html.insert(0, korean_font_tag)

    # Extract and apply CSS styles
    style_tags = soup.find_all("style")
    css_rules = {}

    for style_tag in style_tags:
        if style_tag != korean_font_tag:  # Skip the Korean font tag we just added
            css_content = style_tag.string
            if css_content:
                css_rules.update(parse_css_rules(css_content))

    for selector, styles in css_rules.items():
        if selector.startswith("."):
            class_name = selector[1:].split()[0]
            elements = soup.find_all(class_=class_name)
        elif not selector.startswith(("#", ".")):
            tag_name = selector.split()[0]
            elements = soup.find_all(tag_name)
        else:
            continue

        for element in elements:
            apply_inline_styles(element, styles)

    # ✅ Add border="1" to all <table> for DOCX
    for table in soup.find_all("table"):
        table["border"] = "1"

    # Apply Korean font-family to all text elements
    for element in soup.find_all(['p', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th']):
        current_style = element.get('style', '')
        if 'font-family' not in current_style:
            if current_style and not current_style.endswith(';'):
                current_style += ';'
            element['style'] = current_style + 'font-family: "Noto Sans KR", "Malgun Gothic", "AppleGothic", "Arial Unicode MS", "Arial", sans-serif;'

    # Remove style tags (already inlined) except Korean font tag
    for style_tag in style_tags:
        if style_tag != korean_font_tag:
            style_tag.decompose()

    return str(soup)


def parse_css_rules(css_content):
    """
    Parse CSS content and extract rules.

    Args:
        css_content: CSS content

    Returns:
        dict: CSS rules
    """

    rules = {}

    # Remove comments
    css_content = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)

    # Find CSS rules
    pattern = r"([^{]+)\s*\{\s*([^}]+)\s*\}"
    matches = re.findall(pattern, css_content)

    for selector, declarations in matches:
        selector = selector.strip()

        # Parse declarations
        style_dict = {}
        declarations = declarations.split(";")

        for declaration in declarations:
            if ":" in declaration:
                prop, value = declaration.split(":", 1)
                prop = prop.strip()
                value = value.strip()

                # Convert CSS properties to inline style format
                if prop:
                    style_dict[prop] = value

        if style_dict:
            rules[selector] = style_dict

    return rules


def apply_inline_styles(element, styles):
    """
    Apply CSS styles as inline styles to an element.

    Args:
        element: BeautifulSoup element
        styles: CSS styles
    """
    current_style = element.get("style", "")

    # Convert styles dict to CSS string
    new_styles = []
    for prop, value in styles.items():
        # Map CSS properties for better DOCX compatibility
        docx_prop = map_css_property_to_docx(prop, value)
        if docx_prop:
            new_styles.append(f"{docx_prop[0]}: {docx_prop[1]}")

    if new_styles:
        if current_style and not current_style.endswith(";"):
            current_style += ";"

        combined_style = current_style + "; ".join(new_styles)
        element["style"] = combined_style


def map_css_property_to_docx(prop, value):
    """
    Map CSS properties to DOCX-compatible inline styles.

    Args:
        prop: CSS property
        value: CSS value
    """

    # Common mappings that work well with htmldocx
    mappings = {
        "font-size": ("font-size", value),
        "font-weight": ("font-weight", value),
        "font-family": ("font-family", value),  # Added font-family support
        "color": ("color", value),
        "background-color": ("background-color", value),
        "text-align": ("text-align", value),
        "margin": ("margin", value),
        "padding": ("padding", value),
        "border": ("border", value),
        "line-height": ("line-height", value),
        "text-decoration": ("text-decoration", value),
        "font-style": ("font-style", value),
        "vertical-align": ("vertical-align", value),
    }

    # Special handling for font-family to ensure Korean fonts are prioritized
    if prop == "font-family":
        # Ensure Korean fonts are at the beginning of the font stack
        korean_fonts = ['Noto Sans KR', 'Malgun Gothic', 'AppleGothic', 'Apple SD Gothic Neo', 
                       'Nanum Gothic', 'Nanum Myeongjo', 'Gulim', 'Dotum', 'Batang']
        
        # If the value contains Korean fonts, prioritize them
        if any(font in value for font in korean_fonts):
            # Reorder to put Korean fonts first
            font_list = [f.strip().strip("'\"") for f in value.split(',')]
            korean_fonts_in_value = [f for f in font_list if any(kf in f for kf in korean_fonts)]
            other_fonts = [f for f in font_list if not any(kf in f for kf in korean_fonts)]
            
            # Reorder: Korean fonts first, then others
            reordered_fonts = korean_fonts_in_value + other_fonts
            reordered_value = ', '.join(reordered_fonts)
            
            return ("font-family", reordered_value)
    
    return mappings.get(prop)


