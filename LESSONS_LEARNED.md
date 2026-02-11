# Lessons Learned — MSC-ALGO v4 Pipeline

## Bugs Fixed

### 1. `$input.item()` does not exist in n8n Code Nodes

- **Symptom:** `$input.item is not a function [line 7]`
- **Root Cause:** n8n Code nodes with multiple inputs cannot use `$input.item()` or `$input.all(inputIndex)`. These APIs don't exist.
- **Fix:** Reference upstream nodes by name: `$('Node Name').all().map(i => i.json)`
- **Lesson:** Always use `$('Node Name').all()` for multi-input Code nodes. Wrap in `try/catch` for optional inputs.

### 2. Credential IDs must match server, not placeholders

- **Symptom:** n8n UI forces user to re-select credentials every time
- **Root Cause:** JSON contained placeholder IDs (`GOOGLE_SA_CREDENTIAL_ID`, `META_BEARER_CREDENTIAL_ID`) that don't exist on server
- **Fix:** Query `GET /api/v1/workflows/{id}` to read real credential IDs from server, then patch into local JSON
- **Lesson:** After first manual setup in n8n UI, always read back the real IDs via API and store them in the JSON.

| Node | Credential Type | Real ID |
|:---|:---|:---|
| GA4 nodes | `googleApi` | `HDkQgqGFjUakc4Ct` |
| Meta Ads | `httpBearerAuth` | `RAbkfjgnH4OLFDrm` |
| Google Sheets | `googleSheetsOAuth2Api` | `4rQw16Pw2ajSyr33` |

### 3. JSON comments crash n8n

- **Symptom:** Workflow import fails silently
- **Root Cause:** JSON spec doesn't allow `//` comments. A `// MERGER CONNECTION` comment was added to the connections section.
- **Fix:** Remove all comments from JSON files
- **Lesson:** Never add comments to `.json` files. Use `"notes"` field on n8n nodes instead.

### 4. `nodeCredentialType` vs actual credential type

- **Symptom:** GA4 auth fails even with correct Service Account
- **Root Cause:** n8n uses `googleApi` as the credential type for Service Account auth on HTTP Request nodes, not `googleServiceAccountApi`
- **Fix:** Use `googleApi` with the correct credential ID
- **Lesson:** The credential type in JSON must match what n8n server stores, not what the documentation says.

### 5. Unleash / HTTP Header encoding (Antigravity IDE)

- **Symptom:** IDE extension crashes repeatedly with `Paweł-DESKTOP-71DFK8S is not a legal HTTP header value`
- **Root Cause:** Polish character `ł` in Windows hostname is non-ASCII, invalid for HTTP headers
- **Impact:** Extension host becomes unresponsive, commands like `getChromeDevtoolsMcpUrl` fail
- **Workaround:** Ignore IDE errors. Use workspace root for file access (not deep `.gemini` paths). All n8n operations are server-side and unaffected.
