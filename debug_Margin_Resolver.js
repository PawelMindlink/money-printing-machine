// ============================================================
// MARGIN RESOLVER — GATE NODE
// ============================================================

const rules = $input.all().map(item => ({
  match_type:  (item.json.match_type  || '').toUpperCase().trim(),
  match_value: (item.json.match_value || '').trim(),
  margin_rate: parseFloat(item.json.margin_rate) || 0
}));

const validTypes = ['SKU_EXACT', 'CATEGORY_EXACT', 'KEYWORD'];
const validRules = rules.filter(r => validTypes.includes(r.match_type) && r.margin_rate > 0);

const config = $node['Build Config'].json;

return [{ json: {
  ...config,
  MARGIN_RULES: validRules,
  MARGIN_RULES_COUNT: validRules.length,
  _resolver_executed: true
} }];