from django.core.management.base import BaseCommand
from report_template.models import ReportTemplate


class Command(BaseCommand):
    help = 'Create a default report template'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if default template exists',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace existing default template',
        )

    def handle(self, *args, **options):
        # Check existing templates
        existing_defaults = ReportTemplate.objects.filter(is_default=True)
        existing_enabled = ReportTemplate.objects.filter(is_enabled=True)
        
        self.stdout.write(f"Found {existing_defaults.count()} default template(s)")
        self.stdout.write(f"Found {existing_enabled.count()} enabled template(s)")
        
        # Show existing templates
        if existing_defaults.exists():
            self.stdout.write("\nExisting default templates:")
            for template in existing_defaults:
                self.stdout.write(f"  - ID: {template.id}, Name: {template.name}, Enabled: {template.is_enabled}")
        
        # Check if we should proceed
        if existing_defaults.exists() and not options['force'] and not options['replace']:
            self.stdout.write(
                self.style.WARNING('\nDefault template already exists. Use --force to create anyway or --replace to replace existing.')
            )
            return
        
        # If replace option is used, remove existing defaults
        if options['replace'] and existing_defaults.exists():
            count = existing_defaults.count()
            existing_defaults.update(is_default=False)
            self.stdout.write(
                self.style.WARNING(f'Removed default flag from {count} existing template(s)')
            )

        # Create default template
        default_template = '''<style>
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

  &.hide-table-borders > tbody > tr > td {
  border: none;
  }
  }

  .tiptap-preview table td, .tiptap-preview table th {
  border: 1px solid #ced4da;
  padding: 3px 5px;
  vertical-align: top;
  box-sizing: border-box;
  min-width: 1em;
  position: relative;


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
  border-radius: 4px;
  color: #212529;
  font-size: 0.85rem;
  font-family: 'JetBrainsMono', monospace;
  padding: 0.25em 0.3em;
  }

  .tiptap-preview pre {
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

  .tiptap-preview .code-block-wrapper {
  padding: 0 !important;
  background-color: transparent !important;
  }


  .hide-table-borders > tbody > tr > td {
  border: none;
  }

  .report-container {
  width: 100%;
  margin: 0 auto;
  /*border: 2px solid #000;*/
  }

  .header-tel {
  text-align: right;
  font-size: 8px;
  }

  .header-text {
  flex: 1;
  }

  .title-section {
  margin: 1px;
  display: flex;
  align-items: center;
  padding: 10px 15px;
  }

  .main-title {
  font-size: 18px;
  font-weight: bold;
  flex: 1;
  }

  .approval-table {
  border: 2px solid #000;
  border-collapse: collapse;
  }

  .approval-table td {
  border: 1px solid #000;
  padding: 4px 10px;
  text-align: center;
  font-size: 8px;
  width: 40px;
  height: 20px;
  }

  .approval-table .signature-row td {
  height: 30px;
  }

  .basic-info {
  width: 100%, padding: 10px 15px;
  /*border-bottom: 1px solid #000;*/
  }

  .info-line {
  margin-bottom: 4px;
  font-size: 8px;
  }

  .black-header {
  color: black;
  padding: 4px 12px;
  font-weight: bold;
  font-size: 9px;
  }

  .horizal-divider {
  background: #fff;
  height: 1px;
  border: 2px solid #000;
  border-left-width: 0;
  border-right-width: 0;
  }

  .flight-status {
  width: 100%, display: flex;
  min-height: 120px;
  }

  .left-content {
  flex: 1;
  padding: 10px 15px;
  }

  .right-content {
  display: flex;
  flex-direction: row;
  gap: 10px;
  margin-bottom: 5px;
  justify-content: center;
  }

  .status-line {
  display: flex;
  margin-bottom: 3px;
  font-size: 8px;
  }

  .status-bullet {
  width: 12px;
  }

  .status-label {
  width: 40px;
  font-weight: bold;
  }

  .diagonal-box {
  position: absolute;
  right: 15px;
  top: 15px;
  width: 150px;
  height: 80px;
  border: 1px solid #000;
  background-image: repeating-linear-gradient(45deg, transparent, transparent 4px, #000 4px, #000 5px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  }

  .diagonal-text {
  background: white;
  padding: 2px 6px;
  font-size: 7px;
  text-align: center;
  margin: 2px;
  }

  .gray-header {
  background: #808080;
  color: white;
  padding: 4px 12px;
  font-weight: bold;
  font-size: 9px;
  margin: 4px 0px 0px 0px;
  }

  .checklist-table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  table-layout: auto;
  }

  .checklist-table td {
  border: 1px solid #000;
  padding: 3px 8px;
  font-size: 8px;
  vertical-align: top;
  word-wrap: break-word;
  overflow-wrap: break-word;
  }

  .auto-check-header {
  background: #808080;
  color: white;
  font-weight: bold;
  text-align: center;
  min-width: 150px;
  font-size: 14px !important;
  }

  .status-header {
  background: #808080;
  color: white;
  font-weight: bold;
  text-align: center;
  min-width: 80px;
  font-size: 14px !important;
  }

  .check-item {
  min-width: 150px;
  max-width: 200px;
  }

  .status-cell {
  min-width: 80px;
  max-width: 100px;
  }

  .action-cell {
  min-width: 80px;
  max-width: 100px;
  font-size: 7px;
  }

  .section-header {
  background: #c0c0c0;
  font-weight: bold;
  text-align: center;
  font-size: 14px !important;
  min-width: 150px;
  }

  .sub-header {
  background: #c0c0c0;
  font-weight: bold;
  text-align: center;
  }

  .inspection-section {
  display: flex;
  }

  .inspection-left {
  width: 50%;
  border-right: 1px solid #000;
  }

  .inspection-right {
  width: 50%;
  }

  .inspection-category {
  background: #c0c0c0;
  padding: 3px 8px;
  font-weight: bold;
  font-size: 8px;
  border-bottom: 1px solid #000;
  }

  .inspection-item {
  padding: 3px 8px;
  font-size: 7px;
  border-bottom: 1px solid #ddd;
  min-height: 16px;
  }

  .item-bullet {
  margin-right: 4px;
  }

  .inner-table {
  width: 100%;
  border-collapse: collapse;
  /* viền dính nhau */
  }

  .inner-table td {
  border: 1px solid #000;
  padding: 3px 8px;
  font-size: 8px;
  }

  .title-checklist {
  display: flex;
  padding: 0px 0px 3px 0px;
  }

  .title-left,
  .title-right {
  flex: 1;
  font-weight: bold;
  font-size: 9px;
  }

  .image-box {
  width: 25%;
  display: flex;
  align-items: center;
  justify-content: center;
  }

  .image-box img {
  max-width: 100%;
  max-height: auto;
  object-fit: contain;
  }
  </style><div class="tiptap-preview"><div class="tableWrapper"><table style="min-width: 50px;" class="hide-table-borders"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><td colspan="1" rowspan="1"><p><span style="font-size: 14px">(주)가이온</span></p></td><td colspan="1" rowspan="1"><p style="text-align: right"><span style="font-size: 14px">Tel : 02) 2051-9595</span></p></td></tr></tbody></table></div><hr contenteditable="false"><div class="tableWrapper"><table style="min-width: 366px;" class="hide-table-borders"><colgroup><col style="width: 341px;"><col style="min-width: 25px;"></colgroup><tbody><tr><td colspan="1" rowspan="1" colwidth="341"><p style="text-align: center"><br><br class="ProseMirror-trailingBreak"></p><p style="text-align: center"><br><span style="font-size: 24px">비행 완료 보고서</span></p></td><td colspan="1" rowspan="1"><div class="tableWrapper"><table style="min-width: 100px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th colspan="1" rowspan="4"><p style="text-align: center"><br><br><span style="font-size: 14px">결</span></p><p style="text-align: center"><span style="font-size: 14px">재</span></p></th><th colspan="1" rowspan="1"><p style="text-align: center"><span style="font-size: 14px">담당</span></p></th><th colspan="1" rowspan="1"><p style="text-align: center"><span style="font-size: 14px">팀장</span></p></th><th colspan="1" rowspan="1"><p style="text-align: center"><span style="font-size: 14px">책임자</span></p></th></tr><tr><td colspan="1" rowspan="3"><p style="text-align: center"><br><br><br><br><br class="ProseMirror-trailingBreak"></p></td><td colspan="1" rowspan="3"><p style="text-align: center"><br><br class="ProseMirror-trailingBreak"></p></td><td colspan="1" rowspan="3"><p style="text-align: center"><br><br class="ProseMirror-trailingBreak"></p></td></tr><tr></tr><tr></tr></tbody></table></div></td></tr></tbody></table></div><p><br><br class="ProseMirror-trailingBreak"></p><p><span style="font-size: 14px">● 비행일시 : {{ items__timestamp|default("N/A") }} {% if items__delivered_at %} ~ {{ items__delivered_at }}{% endif %}</span></p><p><span style="font-size: 14px">● 기체등록 : {{ drone__name|default("N/A") }} {{ drone__id|default("")}}</span></p><p><span style="font-size: 14px">● 운항회사 : {{ order__pickup_location__group__name|default("N/A") }}</span></p><p><span style="font-size: 14px">● 기장정보 : 비행시작(MissionStart Message) 기상</span></p><p><span style="font-size: 16px"><strong>▐▒ 비행정보</strong></span></p><p><span style="font-size: 14px">o 비행경로: {{ route__name|default("N/A") }}</span></p><p><span style="font-size: 14px">o 임 무 명: {{ current_status__description|default("배송 임무") }}</span></p><p><span style="font-size: 14px">o 기 체 명: {{ drone__name|default("N/A") }}</span></p><p><span style="font-size: 14px">o 장 소: {{ order__pickup_location__full_address|default(order__pickup_location__name)|default("N/A") }}</span></p><div class="tableWrapper"><table style="min-width: 412px;" class="hide-table-borders"><colgroup><col style="width: 387px;"><col style="min-width: 25px;"></colgroup><tbody><tr><td colspan="1" rowspan="1" colwidth="387"><p><code>{% if order__pickup_location__avatar__file_url %}</code></p><div style="display: flex;" contenteditable="false" draggable="true"><div style=""><div class="image-wrapper"><img src="{{ order__pickup_location__avatar__file_url }}" alt="Pickup Location" style="" draggable="true"></div></div></div><p><code>{% else %}</code></p><div style="display: flex;" contenteditable="false" draggable="true"><div style=""><div class="image-wrapper"><img src="" alt="Pickup Location" style="" draggable="true"></div></div></div><p><code>{% endif %}</code></p></td><td colspan="1" rowspan="1"><p><code>{% if order__delivery_terminal__avatar__file_url %}</code></p><div style="display: flex;" contenteditable="false" draggable="true"><div style=""><div class="image-wrapper"><img src="{{ order__delivery_terminal__avatar__file_url }}" alt="Delivery Terminal" style="" draggable="true"></div></div></div><p><code>{% else %}</code></p><div style="display: flex;" contenteditable="false" draggable="true"><div style=""><div class="image-wrapper"><img src="" alt="Pickup Location" style="" draggable="true"></div></div></div><p><code>{% endif %}</code></p></td></tr></tbody></table></div><div class="tableWrapper"><table style="width: 560px;" class="hide-table-borders"><colgroup><col style="width: 215px;"><col style="width: 345px;"></colgroup><tbody><tr><td colspan="1" rowspan="1" colwidth="215"><p><span style="font-size: 16px"><strong>▐▒점검기록</strong></span></p></td><td colspan="1" rowspan="1" colwidth="345"><p style="text-align: center"><span style="font-size: 16px">- 아 래 -</span></p></td></tr></tbody></table></div><hr contenteditable="false"><div class="tableWrapper"><table style="min-width: 75px;"><colgroup><col style="min-width: 25px;"><col style="min-width: 25px;"><col style="min-width: 25px;"></colgroup><tbody><tr><th class="selectedCell" colspan="3" rowspan="1"><p><span style="font-size: 16px"><strong>점검항목</strong></span></p></th></tr></tbody></table></div><pre data-language="html" data-type="code-block" class="code-block-wrapper"><code data-language="html"><code>&lt;table class="checklist-table"&gt;
    &lt;tr&gt;
        &lt;td class="auto-check-header"&gt;자동 점검 항목&lt;/td&gt;
        &lt;td class="status-header"&gt;상태&lt;/td&gt;
        &lt;td class="auto-check-header"&gt;자동 점검 항목&lt;/td&gt;
        &lt;td class="status-header"&gt;상태&lt;/td&gt;
    &lt;/tr&gt;
    {% if auto_check_list %}
    {% set auto_items = auto_check_list if auto_check_list is iterable else [] %}
    {% if auto_items %}
    {% for i in range(0, auto_items|length, 2) %}
    &lt;tr&gt;
        {% if i &lt; auto_items|length %}
         &lt;td class="check-item"&gt;{{ auto_items[i].item_name }}&lt;/td&gt;
         &lt;td class="status-cell"&gt;{{ auto_items[i].value|default("비정상(Warning)") }}&lt;/td&gt;
         {% else %}
         &lt;td class="check-item"&gt;&lt;/td&gt;
         &lt;td class="status-cell"&gt;&lt;/td&gt;
         {% endif %}
         {% if i + 1 &lt; auto_items|length %}
         &lt;td class="check-item"&gt;{{ auto_items[i + 1].item_name }}&lt;/td&gt;
         &lt;td class="status-cell"&gt;{{ auto_items[i + 1].value|default("비정상(Warning)") }}&lt;/td&gt;
         {% else %}
         &lt;td class="check-item"&gt;&lt;/td&gt;
         &lt;td class="status-cell"&gt;&lt;/td&gt;
         {% endif %}
    &lt;/tr&gt;
    {% endfor %}
    {% endif %}
    {% endif %}
&lt;/table&gt;</code></code></pre><pre data-language="html" data-type="code-block" class="code-block-wrapper"><code data-language="html"><code>{% if checklist_by_category %}
&lt;div style="margin-top: 15px;"&gt;&lt;/div&gt;
&lt;table class="checklist-table"&gt;
    &lt;tr&gt;
        &lt;td class="section-header"&gt;점검 항목&lt;/td&gt;
        &lt;td class="section-header"&gt;조치사항&lt;/td&gt;
    &lt;/tr&gt;
    {% set category_keys = ["Pre-flight Check", "Weather Check", "Controller Check"] %}
    {% for cat_key in category_keys %}
    {% if checklist_by_category.get(cat_key) %}
    {% set items = checklist_by_category[cat_key] %}
    &lt;tr&gt;
        &lt;td colspan="2" style="background: #e0e0e0; font-weight: bold; text-align: left; padding: 5px; font-size: 9px;"&gt;
            {{ cat_key }}
        &lt;/td&gt;
    &lt;/tr&gt;
    {% for item in items %}
    &lt;tr&gt;
        &lt;td&gt;{{ "☑" if item.is_checked else "☐" }} {{ item.item_name }}&lt;/td&gt;
        &lt;td class="action-cell"&gt;{{ item.action_taken|default("") }}&lt;/td&gt;
    &lt;/tr&gt;
    {% endfor %}
    {% endif %}
    {% endfor %}
&lt;/table&gt;
{% endif %}</code></code></pre><pre data-language="html" data-type="code-block" class="code-block-wrapper"><code data-language="html"><code>{% if not auto_check_list and not checklist_by_category %}
&lt;table class="checklist-table"&gt;
    &lt;tr&gt;
        &lt;td colspan="4" style="text-align: center; padding: 20px"&gt;
            점검 데이터가 없습니다
        &lt;/td&gt;
    &lt;/tr&gt;
&lt;/table&gt;
{% endif %}</code></code></pre><p><span style="font-size: 14px">o 비고 : {% if order__recipient_note %}{{ order__recipient_note }}{% endif %}{% if order__sender_note %}{{ order__sender_note }}{% endif %}</span></p></div>'''

        template = ReportTemplate.objects.create(
            name='Default Delivery Report Template',
            template=default_template,
            is_default=True,
            is_enabled=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created default template with ID: {template.id}')
        )
