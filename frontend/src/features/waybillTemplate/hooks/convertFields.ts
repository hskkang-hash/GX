import { generateStyledQRCode } from '@/utils/generateStyledQRCode';
import { isObject } from '@/utils/utils';

import { Field, FieldTemplate, Result } from '../type';

export async function convertFieldsAndData(fields: Field[]): Promise<Result> {
  const data: Record<string, any> = {};
  const fieldTemplate: FieldTemplate[] = [];

  const qrPromises: Promise<void>[] = [];

  fields.forEach(async (field) => {
    const {
      name,
      field_type,
      label,
      fields: childFields,
      data_example,
    } = field;

    if (field_type === 'table' && Array.isArray(childFields)) {
      const rowExample: Record<string, any> = {};
      childFields.forEach((child) => {
        rowExample[child.name] = isObject(child.data_example)
          ? child.data_example.name
          : child.data_example;
      });
      data[name] = [rowExample];

      let listItems = '';
      childFields.forEach((child) => {
        listItems += `{{ ${name}_child.${child.name} }} | `;
      });

      const valueTemplate = `{% for ${name}_child in ${name} %}<ol><li>${listItems.trim()}</li></ol>{% endfor %}`;

      fieldTemplate.push({ label, value: valueTemplate });
    } else if (field_type === 'qr_code') {
      fieldTemplate.push({
        label,
        value: `{{ ${name} }}`,
      });
      const primaryColor =
        getComputedStyle(document.documentElement)
          .getPropertyValue('--ga-primary')
          .trim() || '#2196f3';

      const url_qr_code =
        import.meta.env.VITE_API_URL_FE +
        `?data=${encodeURIComponent(JSON.stringify(data_example))}`;

      const qrPromise = generateStyledQRCode({
        data: url_qr_code,
        primaryColor,
        logo: '/logoguax.svg',
      }).then((url: string) => {
        data['qr_code_img'] = url;
      });

      qrPromises.push(qrPromise);
    } else {
      data[name] = isObject(data_example) ? data_example.name : data_example;
      fieldTemplate.push({
        label,
        value: `{{ ${name} }}`,
      });
    }
  });

  // Await all QR Code image generation
  await Promise.all(qrPromises);

  return {
    data,
    fieldTemplate,
  };
}

export function reverseFormatHTML(html: string): string {
  if (!html) return '';

  let result = html;

  // 1. Bỏ <style>...</style>
  result = result.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');

  // 2. Gỡ image-wrapper => giữ nguyên <img ...> tag với bất kỳ cách đóng tag nào
  result = result.replace(
    /<div[^>]*class=["']?image-wrapper["']?[^>]*>\s*(<img[^>]* \/>)\s*<\/div>/gi,
    '$1',
  );

  // 3. Bỏ wrapper tiptap-preview
  result = result.replace(
    /<div[^>]*class=["']?tiptap-preview[^"']*["']?[^>]*>([\s\S]*?)<\/div>/i,
    '$1',
  );

  return result.trim();
}

export function replaceQRParagraphWithDiv(html: string): string {
  // 1. Tách phần <style> nếu có
  const styleMatch = html.match(/<style[\s\S]*?<\/style>/gi);
  const styleContent = styleMatch ? styleMatch.join('\n') : '';

  // 2. Lấy phần nội dung còn lại để xử lý DOM
  const contentWithoutStyle = html.replace(/<style[\s\S]*?<\/style>/gi, '');

  // 3. Dùng DOMParser để chỉnh sửa nội dung
  const parser = new DOMParser();
  const doc = parser.parseFromString(contentWithoutStyle, 'text/html');

  const qrParagraphs = doc.querySelectorAll('p');

  qrParagraphs.forEach((p) => {
    const content = p.innerHTML.trim();
    if (content === '{{ qr_code }}' || content.includes('{{ qr_code }}')) {
      const replacement = document.createElement('div');

      replacement.setAttribute('style', p.getAttribute('style') || '');

      replacement.className = 'qr-code-wrapper';
      replacement.innerHTML = `<img src="{{ qr_code_img }}" alt="QR Code" style="width: 150px;" />`;

      p.replaceWith(replacement);
    }
  });

  // 4. Kết hợp lại phần <style> với nội dung HTML đã xử lý
  return `${styleContent}\n${doc.body.innerHTML}`;
}
