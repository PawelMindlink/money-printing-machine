// ============================================================
// MARGIN RESOLVER v2 — Supports DEFAULT rule type
// ============================================================

const rules = $input.all().map(item => ({
  match_type: (item.json.match_type || '').toUpperCase().trim(),
  match_value: (item.json.match_value || '').trim(),
  margin_rate: parseFloat(item.json.margin_rate) || 0
}));

const validTypes = ['SKU_EXACT', 'CATEGORY_EXACT', 'KEYWORD', 'DEFAULT'];
const validRules = rules.filter(r => validTypes.includes(r.match_type) && r.margin_rate > 0);

// Extract DEFAULT rule for fallback (separate from matching rules)
const defaultRule = validRules.find(r => r.match_type === 'DEFAULT');
const matchingRules = validRules.filter(r => r.match_type !== 'DEFAULT');

const config = $node['Build Config'].json;

// If DEFAULT rule exists in sheet, it overrides config DEFAULT_MARGIN
const effectiveDefault = defaultRule ? defaultRule.margin_rate : config.DEFAULT_MARGIN;

return [{
  json: {
    ...config,
    DEFAULT_MARGIN: effectiveDefault,
    MARGIN_RULES: matchingRules,
    MARGIN_RULES_COUNT: matchingRules.length,
    _has_default_rule: !!defaultRule,
    _resolver_executed: true
  }
}];