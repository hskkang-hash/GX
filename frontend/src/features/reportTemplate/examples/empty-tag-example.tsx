import React from 'react';

import CustomNunjucksRerender from '../components/CustomNunjucksRerender';

/**
 * Example component demonstrating the "empty" tag functionality
 */
const EmptyTagExample: React.FC = () => {
  // Example 1: Empty array - should show "No items found"
  const emptyItemsTemplate = `
    <h3>Items List:</h3>
    {% for item in items %}
      <div>{{ item.name }}</div>
    {% empty %}
      <div style="color: red;">No items found</div>
    {% endfor %}
  `;

  const emptyItemsData = {
    items: [],
  };

  // Example 2: Populated array - should show the items
  const populatedItemsTemplate = `
    <h3>Items List:</h3>
    {% for item in items %}
      <div>{{ item.name }}</div>
    {% empty %}
      <div style="color: red;">No items found</div>
    {% endfor %}
  `;

  const populatedItemsData = {
    items: [{ name: 'Item 1' }, { name: 'Item 2' }, { name: 'Item 3' }],
  };

  // Example 3: Dictionary iteration with empty handling
  const dictionaryTemplate = `
    <h3>Categories:</h3>
    {% for category_name, items in categories.items() %}
      <h4>{{ category_name }}</h4>
      <ul>
      {% for item in items %}
        <li>{{ item.name }}</li>
      {% empty %}
        <li style="color: orange;">No items in this category</li>
      {% endfor %}
      </ul>
    {% empty %}
      <p style="color: red;">No categories found</p>
    {% endfor %}
  `;

  const dictionaryData = {
    categories: {
      Safety: [{ name: 'Check equipment' }, { name: 'Verify procedures' }],
      Quality: [], // Empty category
      Maintenance: [{ name: 'Inspect systems' }],
    },
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Empty Tag Examples</h1>

      <div style={{ marginBottom: '30px' }}>
        <h2>Example 1: Empty Array</h2>
        <CustomNunjucksRerender
          template={emptyItemsTemplate}
          data={emptyItemsData}
        />
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>Example 2: Populated Array</h2>
        <CustomNunjucksRerender
          template={populatedItemsTemplate}
          data={populatedItemsData}
        />
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>Example 3: Dictionary with Empty Categories</h2>
        <CustomNunjucksRerender
          template={dictionaryTemplate}
          data={dictionaryData}
        />
      </div>
    </div>
  );
};

export default EmptyTagExample;
