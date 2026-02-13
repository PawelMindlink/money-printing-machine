// ============================================================
// PARSE API RESPONSE
// Ensures Python API response is properly formatted for Sheets
// ============================================================
const items = $input.all().map(i => i.json);

// Handle case where response is nested in 'data' or similar
if (items.length === 1 && Array.isArray(items[0])) {
  return items[0].map(item => ({ json: item }));
}

// Already properly formatted
return items.map(item => ({ json: item }));