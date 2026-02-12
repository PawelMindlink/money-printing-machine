# n8n Expression Syntax Cheat Sheet

Quick reference for `{{ }}` expressions used in node parameter fields.

## Core Variables

| Variable | Description | Example |
|---|---|---|
| `$json` | Current item's JSON data | `{{ $json.name }}` |
| `$json.body` | Webhook payload (⚠️ critical) | `{{ $json.body.email }}` |
| `$node['Name']` | Reference another node's output | `{{ $node['Load Config'].json.brand }}` |
| `$env` | Environment variables | `{{ $env.API_KEY }}` |
| `$now` | Current DateTime (Luxon) | `{{ $now.toISO() }}` |
| `$today` | Today at midnight | `{{ $today.toISODate() }}` |
| `$runIndex` | Current execution run index | `{{ $runIndex }}` |
| `$itemIndex` | Current item index in batch | `{{ $itemIndex }}` |
| `$input` | Current node's input data | `{{ $input.first().json.id }}` |
| `$workflow` | Workflow metadata | `{{ $workflow.name }}` |
| `$execution` | Execution metadata | `{{ $execution.id }}` |

## Common Patterns

### String Interpolation

```
{{ 'Hello ' + $json.name + '!' }}
```

### Conditional (Ternary)

```
{{ $json.status === 'active' ? 'Yes' : 'No' }}
```

### Default / Fallback

```
{{ $json.brand || 'Unknown' }}
```

### Date Formatting

```
{{ $now.toFormat('yyyy-MM-dd') }}
{{ $now.minus({days: 7}).toISO() }}
{{ DateTime.fromISO($json.date).toFormat('dd/MM/yyyy') }}
```

### Array Access

```
{{ $json.items[0].name }}
{{ $json.tags.join(', ') }}
```

### Math

```
{{ ($json.price * 1.23).toFixed(2) }}
{{ Math.round($json.value * 100) / 100 }}
```

## ⚠️ Gotchas

1. **Webhook data** is always under `$json.body`, not `$json` directly
2. **Expressions can't use `await`** — use Code nodes for async operations
3. **No multi-line expressions** — use Code nodes for complex logic
4. **`$node` references use display name**, not the node `id`
5. **Type coercion**: `$json.count` may be a string → use `Number($json.count)`

## When NOT to Use Expressions

Use a **Code node** instead when you need:

- Loops or iteration
- Error handling (try/catch)
- HTTP requests
- Complex string manipulation
- Data transformation across multiple items
- Any logic longer than one line
