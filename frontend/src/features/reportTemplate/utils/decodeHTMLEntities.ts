// Chuyển entity -> HTML thật
export function decodeCodeBlocks(html: string) {
  return html.replace(
    /(<pre[^>]*data-language="html"[^>]*>[\s\S]*?<code[^>]*><code[^>]*>)([\s\S]*?)(<\/code><\/code>[\s\S]*?<\/pre>)/gi,
    (match, start, content, end) => {
      const textarea = document.createElement('textarea');
      textarea.innerHTML = content;
      return start + textarea.value + end;
    },
  );
}

// Chuyển HTML thật -> entity (&lt; &gt;)
export function encodeCodeBlocks(html: string) {
  return html.replace(
    /(<pre[^>]*data-language="html"[^>]*>[\s\S]*?<code[^>]*><code[^>]*>)([\s\S]*?)(<\/code><\/code>[\s\S]*?<\/pre>)/gi,
    (match, start, content, end) => {
      return (
        start +
        content
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;') +
        end
      );
    },
  );
}
