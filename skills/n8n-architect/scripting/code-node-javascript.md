# n8n Code Node — JavaScript Patterns

Reference for writing JavaScript inside `n8n-nodes-base.code` nodes (typeVersion 2).

## Data Access

```javascript
// All items from previous node
const items = $input.all();       // Returns: [{json: {...}}, ...]

// First item only
const first = $input.first();     // Returns: {json: {...}}

// Current item (in "Run Once for Each Item" mode)
const item = $input.item;         // Returns: {json: {...}}
```

## ⚠️ Critical Gotcha: Webhook Data

Webhook payload is nested under `$json.body`, NOT at the root:

```javascript
// ❌ WRONG
const name = $json.name;

// ✅ CORRECT
const name = $json.body.name;
```

## Return Format

Code nodes **MUST** return an array of objects with a `json` key:

```javascript
// ✅ Correct — single item
return [{ json: { result: "ok", count: 42 } }];

// ✅ Correct — multiple items
return items.map(item => ({
  json: {
    ...item.json,
    processed: true
  }
}));

// ❌ WRONG — missing json wrapper
return [{ result: "ok" }];

// ❌ WRONG — not an array
return { json: { result: "ok" } };
```

## Built-in Helpers

```javascript
// HTTP Request (no external packages needed)
const response = await $helpers.httpRequest({
  method: 'GET',
  url: 'https://api.example.com/data',
  headers: { 'Authorization': `Bearer ${$env.API_KEY}` }
});

// Current date/time
const now = DateTime.now();
const formatted = now.toFormat('yyyy-MM-dd');

// JMESPath queries
const result = $jmespath(data, 'people[?age > `30`].name');

// Environment variables
const apiKey = $env.MY_API_KEY;

// Reference data from another node
const config = $node['Load Config'].json;
```

## Top 5 Error Patterns

| # | Error | Fix |
|---|---|---|
| 1 | `Cannot read property 'x' of undefined` | Data is under `.body` for webhooks |
| 2 | `items is not iterable` | Use `$input.all()`, not `$json` directly |
| 3 | `Must return array of objects with json` | Wrap return: `[{json: {...}}]` |
| 4 | `Cannot use import statement` | n8n uses CommonJS, no `import` |
| 5 | `$helpers is not defined` | Use `this.helpers` in older versions |

## Production Patterns

### Safe Property Access

```javascript
const value = item.json?.nested?.deep?.value ?? 'default';
```

### URL Normalization

```javascript
function normalizeUrl(url) {
  if (!url) return '';
  return url.toLowerCase()
    .replace(/^https?:\/\/(www\.)?/, '')
    .split('?')[0]
    .replace(/\/$/, '');
}
```

### Percentile Calculation

```javascript
function getPercentile(values, pct) {
  const sorted = values.filter(v => typeof v === 'number' && v > 0).sort((a, b) => a - b);
  if (sorted.length === 0) return 0;
  const idx = Math.floor(sorted.length * pct);
  return sorted[Math.min(idx, sorted.length - 1)];
}
```

### Grouping / Aggregation

```javascript
const grouped = {};
for (const item of items) {
  const key = item.json.category;
  if (!grouped[key]) grouped[key] = [];
  grouped[key].push(item.json);
}
return Object.entries(grouped).map(([key, records]) => ({
  json: { category: key, count: records.length, records }
}));
```
