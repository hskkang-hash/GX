/**
 * Preprocesses template content to ensure compatibility with different template engines
 * @param template - The raw template string
 * @returns The preprocessed template string
 */
export const preprocessTemplate = (template: string): string => {
  if (!template) return template;

  let processedTemplate = template;

  // Convert "elif" to "elsif" for LiquidJS compatibility
  // This regex matches {% elif with optional whitespace
  processedTemplate = processedTemplate.replace(/\{%\s*elif\s+/g, '{% elsif ');

  // Handle dictionary iteration syntax
  // Convert Jinja2/Nunjucks style: {% for key, value in object.items() %}
  // To LiquidJS style: {% for item in object %}

  // Handle dictionary iteration with .items() (with parentheses)
  processedTemplate = processedTemplate.replace(
    /\{%\s*for\s+(\w+),\s*(\w+)\s+in\s+(\w+)\.items\(\)\s*%\}/g,
    '{% for $1_$2 in $3 %}',
  );

  // Handle dictionary iteration with .items (without parentheses)
  processedTemplate = processedTemplate.replace(
    /\{%\s*for\s+(\w+),\s*(\w+)\s+in\s+(\w+)\.items\s*%\}/g,
    '{% for $1_$2 in $3 %}',
  );

  // Handle dictionary iteration with .iteritems() (Python style)
  processedTemplate = processedTemplate.replace(
    /\{%\s*for\s+(\w+),\s*(\w+)\s+in\s+(\w+)\.iteritems\(\)\s*%\}/g,
    '{% for $1_$2 in $3 %}',
  );

  // Handle empty tag - convert {% empty %} to {% else %} for LiquidJS compatibility
  processedTemplate = processedTemplate.replace(
    /\{%\s*empty\s*%\}/g,
    '{% else %}',
  );

  // Handle Python-style .get() method calls
  // Convert obj.get(key) to obj|get(key) for Nunjucks
  processedTemplate = processedTemplate.replace(
    /(\w+)\.get\(([^)]+)\)/g,
    '$1|get($2)',
  );

  // Handle Python-style .get() method calls with default values
  // Convert obj.get(key, default) to obj|get(key, default) for Nunjucks
  processedTemplate = processedTemplate.replace(
    /(\w+)\.get\(([^,)]+),\s*([^)]+)\)/g,
    '$1|get($2, $3)',
  );

  // Handle array length comparisons - ensure proper parentheses for Nunjucks parsing
  // This regex matches patterns like: i < auto_items|length, i + 1 < auto_items|length, etc.
  processedTemplate = processedTemplate.replace(
    /(\w+(?:\s*\+\s*\d+)?)\s*<\s*(\w+)\|length/g,
    '($1) < ($2|length)',
  );

  // Handle array length comparisons with > operator
  processedTemplate = processedTemplate.replace(
    /(\w+(?:\s*\+\s*\d+)?)\s*>\s*(\w+)\|length/g,
    '($1) > ($2|length)',
  );

  // Handle array length comparisons with <= operator
  processedTemplate = processedTemplate.replace(
    /(\w+(?:\s*\+\s*\d+)?)\s*<=\s*(\w+)\|length/g,
    '($1) <= ($2|length)',
  );

  // Handle array length comparisons with >= operator
  processedTemplate = processedTemplate.replace(
    /(\w+(?:\s*\+\s*\d+)?)\s*>=\s*(\w+)\|length/g,
    '($1) >= ($2|length)',
  );

  return processedTemplate;
};

/**
 * Validates if a template contains valid syntax
 * @param template - The template string to validate
 * @returns true if valid, false otherwise
 */
export const validateTemplate = (template: string): boolean => {
  if (!template) return true;

  // Basic validation - check for unmatched tags
  const ifCount = (template.match(/\{%\s*if\s+/g) || []).length;
  const endifCount = (template.match(/\{%\s*endif\s*%\}/g) || []).length;
  const elsifCount = (template.match(/\{%\s*elsif\s+/g) || []).length;
  const elseCount = (template.match(/\{%\s*else\s*%\}/g) || []).length;

  // Check for loops
  const forCount = (template.match(/\{%\s*for\s+/g) || []).length;
  const endforCount = (template.match(/\{%\s*endfor\s*%\}/g) || []).length;

  // Basic rule: if tags should match endif tags
  if (ifCount !== endifCount) {
    return false;
  }

  // Basic rule: for tags should match endfor tags
  if (forCount !== endforCount) {
    return false;
  }

  // elsif and else should be between if and endif
  const totalConditionalTags = elsifCount + elseCount;
  if (totalConditionalTags > ifCount) {
    return false;
  }

  return true;
};

/**
 * Converts data structure to be compatible with LiquidJS dictionary iteration
 * @param data - The original data object
 * @returns The converted data object
 */
export const convertDataForLiquidJS = (
  data: Record<string, unknown>,
): Record<string, unknown> => {
  const converted = { ...data };

  // Process each property to handle dictionary-like structures
  Object.keys(converted).forEach((key) => {
    const value = converted[key];

    if (value && typeof value === 'object' && !Array.isArray(value)) {
      // Convert object to array of key-value pairs for LiquidJS iteration
      const items = Object.entries(value as Record<string, unknown>).map(
        ([itemKey, itemValue]) => ({
          key: itemKey,
          value: itemValue,
          // Create combined key for the pattern key_value
          [`${key}_${itemKey}`]: itemValue,
        }),
      );

      converted[key] = items;
    }
  });

  return converted;
};
