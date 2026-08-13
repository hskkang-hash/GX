# Report Template Component

This component handles the rendering of report templates using LiquidJS.

## Template Syntax Support

The component supports LiquidJS template syntax with the following features:

### Conditional Statements

```liquid
{% if condition %}
  Content when condition is true
{% elsif other_condition %}
  Content when other_condition is true
{% else %}
  Content when no conditions are true
{% endif %}
```

**Important Note**: The component automatically converts `{% elif %}` to `{% elsif %}` for LiquidJS compatibility.

### Variables

```liquid
{{ variable_name }}
{{ object.property }}
```

### Loops

```liquid
{% for item in items %}
  {{ item.name }}
{% endfor %}
```

### Dictionary Iteration

The component supports dictionary iteration with automatic conversion:

```liquid
{% for key, value in object.items() %}
  {{ key }}: {{ value }}
{% endfor %}
```

**Supported Syntax**:

- `{% for key, value in object.items() %}`
- `{% for key, value in object.items %}`
- `{% for key, value in object.iteritems() %}`

**Note**: The component automatically converts these to LiquidJS-compatible format and transforms the data structure accordingly.

### Empty Loops

The component supports empty loop handling:

```liquid
{% for item in items %}
  {{ item.name }}
{% empty %}
  No items found
{% endfor %}
```

**Note**: The component automatically converts `{% empty %}` to `{% else %}` for LiquidJS compatibility.

## Usage

```tsx
import CustomNunjucksRerender from './components/CustomNunjucksRerender';

const template = `
  {% if user.name %}
    Hello {{ user.name }}!
  {% elif user.email %}
    Hello {{ user.email }}!
  {% else %}
    Hello Guest!
  {% endif %}
  
  {% for category_name, items in checklist_by_category.items() %}
    <h3>{{ category_name }}</h3>
    <ul>
    {% for item in items %}
      <li>{{ item.name }}</li>
    {% empty %}
      <li>No items in this category</li>
    {% endfor %}
    </ul>
  {% empty %}
    <p>No categories found</p>
  {% endfor %}
`;

const data = {
  user: {
    name: 'John Doe',
    email: 'john@example.com',
  },
  checklist_by_category: {
    Safety: [{ name: 'Check equipment' }, { name: 'Verify procedures' }],
    Quality: [{ name: 'Inspect products' }, { name: 'Test samples' }],
  },
};

<CustomNunjucksRerender
  template={template}
  data={data}
  printRef={printRef}
/>;
```

## Error Handling

The component includes error handling for template rendering issues:

- Invalid template syntax will display an error message
- Console errors are logged for debugging
- The component gracefully handles parsing errors

## Template Preprocessing

The component automatically preprocesses templates to ensure compatibility:

1. Converts `{% elif %}` to `{% elsif %}` for LiquidJS compatibility
2. Converts `{% empty %}` to `{% else %}` for LiquidJS compatibility
3. Converts dictionary iteration syntax to LiquidJS-compatible format
4. Transforms data structures for proper iteration
5. Validates basic template structure
6. Handles edge cases and malformed templates

## Data Transformation

The component automatically transforms data structures for dictionary iteration:

**Input Data**:

```javascript
{
  checklist_by_category: {
    Safety: [{ name: 'Check equipment' }],
    Quality: [{ name: 'Inspect products' }],
  },
}
```

**Transformed Data**:

```javascript
{
  checklist_by_category: [
    {
      key: 'Safety',
      value: [{ name: 'Check equipment' }],
      Safety_Safety: [{ name: 'Check equipment' }],
    },
    {
      key: 'Quality',
      value: [{ name: 'Inspect products' }],
      Quality_Quality: [{ name: 'Inspect products' }],
    },
  ],
}
```

## Configuration

The LiquidJS engine is configured with relaxed settings:

- `strictFilters: false` - Allows undefined filters
- `strictVariables: false` - Allows undefined variables
- `cache: false` - Disables caching for dynamic content
