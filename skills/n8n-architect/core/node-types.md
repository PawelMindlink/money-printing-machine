# n8n Node Type Reference

Quick-reference for the most common node `type` strings used in n8n workflows.

## Triggers

| Node | Type String | Version |
|---|---|---|
| Manual Trigger | `n8n-nodes-base.manualTrigger` | 1 |
| Schedule Trigger | `n8n-nodes-base.scheduleTrigger` | 1.1 |
| Webhook | `n8n-nodes-base.webhook` | 2 |
| Error Trigger | `n8n-nodes-base.errorTrigger` | 1 |
| Email Trigger (IMAP) | `n8n-nodes-base.imapEmail` | 2 |

## Data Processing

| Node | Type String | Version |
|---|---|---|
| Code (JS/Python) | `n8n-nodes-base.code` | 2 |
| Set / Edit Fields | `n8n-nodes-base.set` | 3.4 |
| IF / Filter | `n8n-nodes-base.if` | 2 |
| Switch | `n8n-nodes-base.switch` | 3 |
| Merge / Join | `n8n-nodes-base.merge` | 3 |
| Split In Batches | `n8n-nodes-base.splitInBatches` | 3 |
| XML Parser | `n8n-nodes-base.xml` | 1 |
| HTML Extract | `n8n-nodes-base.html` | 1 |
| Aggregate | `n8n-nodes-base.aggregate` | 1 |

## HTTP & APIs

| Node | Type String | Version |
|---|---|---|
| HTTP Request | `n8n-nodes-base.httpRequest` | 4.2 |
| Respond to Webhook | `n8n-nodes-base.respondToWebhook` | 1.1 |

## Google Services

| Node | Type String | Version |
|---|---|---|
| Google Sheets | `n8n-nodes-base.googleSheets` | 4.5 |
| Google Drive | `n8n-nodes-base.googleDrive` | 3 |
| Google Analytics | `n8n-nodes-base.googleAnalytics` | 2.1 |
| Gmail | `n8n-nodes-base.gmail` | 2.1 |

## Communication

| Node | Type String | Version |
|---|---|---|
| Slack | `n8n-nodes-base.slack` | 2.2 |
| Discord | `n8n-nodes-base.discord` | 2 |
| Telegram | `n8n-nodes-base.telegram` | 1.2 |
| Email (Send) | `n8n-nodes-base.emailSend` | 2.2 |

## Databases

| Node | Type String | Version |
|---|---|---|
| Postgres | `n8n-nodes-base.postgres` | 2.5 |
| MySQL | `n8n-nodes-base.mySql` | 2.4 |
| Supabase | `n8n-nodes-base.supabase` | 1 |

## Meta / Facebook

| Node | Type String | Version |
|---|---|---|
| Facebook Graph API | `n8n-nodes-base.facebookGraphApi` | 1 |

> **Note:** For the full list of 525+ supported nodes, use `n8n-mcp` tool: `search_nodes`.
