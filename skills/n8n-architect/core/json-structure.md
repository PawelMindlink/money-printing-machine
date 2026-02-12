# n8n Workflow JSON Structure

Reference for the anatomy of an `.n8n` / `.json` workflow file.

## Top-Level Fields

```json
{
  "id": "string",           // Workflow UUID (server-assigned)
  "name": "string",         // Display name
  "active": false,          // Is workflow active on server
  "nodes": [],              // Array of node objects
  "connections": {},        // Object mapping node connections
  "settings": {},           // Execution settings
  "staticData": null,       // Persistent data between executions
  "meta": null,             // Metadata
  "pinData": null,          // Pinned test data
  "versionId": "uuid",      // Version tracking
  "tags": []                // Organizational tags
}
```

## Node Object

```json
{
  "id": "kebab-case-id",               // UNIQUE, never change existing
  "name": "Human Readable Name",       // Display name (used in connections!)
  "type": "n8n-nodes-base.code",       // Node type string
  "typeVersion": 2,                     // Version of node type
  "position": [1040, 300],             // [x, y] canvas position
  "parameters": {},                     // Node-specific config
  "notes": "Optional description"       // Sticky note on canvas
}
```

## Connections Object

Connections are keyed by the **source node's `name`** (not `id`):

```json
{
  "Source Node Name": {
    "main": [              // Output index array
      [                    // First output (index 0)
        {
          "node": "Target Node Name",  // Target by NAME
          "type": "main",
          "index": 0                   // Target input index
        }
      ]
    ]
  }
}
```

### Multi-Output (e.g., IF node)

```json
{
  "IF Node": {
    "main": [
      [{ "node": "True Branch", "type": "main", "index": 0 }],   // Output 0 = true
      [{ "node": "False Branch", "type": "main", "index": 0 }]   // Output 1 = false
    ]
  }
}
```

### Fan-Out (one node → multiple targets)

```json
{
  "Load Config": {
    "main": [
      [
        { "node": "Fetch Feed", "type": "main", "index": 0 },
        { "node": "Fetch GA4", "type": "main", "index": 0 },
        { "node": "Fetch Ads", "type": "main", "index": 0 }
      ]
    ]
  }
}
```

## Critical Rules

1. **`id`** is immutable after creation — changing it breaks execution history
2. **`name`** is used in `connections` — renaming a node requires updating all connection references
3. **`position`** is `[x, y]` — standard spacing is 200px between nodes
4. **`typeVersion`** matters — using wrong version causes runtime errors
