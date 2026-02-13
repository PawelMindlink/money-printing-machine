// ============================================================
// PYTHON BRIDGE — Consolidate all data for external Python API
// ============================================================

const safeGet = (nodeName) => {
  try { return $(nodeName).all().map(i => i.json); }
  catch (e) { return []; }
};

const feed = safeGet('Normalize Feed + Margins');
const meta = safeGet('Normalize Meta Ads');
const items = safeGet('Normalize GA4 Items');
const lp = safeGet('Normalize GA4 LP');

let config = {};
try { config = $('Margin Resolver').first().json; } catch(e) {}

// Return consolidated payload as single item
return [{ json: {
  feed: feed,
  meta_ads: meta,
  ga4_items: items,
  ga4_lp: lp,
  config: {
    brand: config.BRAND || '',
    vat_rate: config.VAT_RATE || 0.23,
    default_margin: config.DEFAULT_MARGIN || 0.10,
    margin_rules: config.MARGIN_RULES || []
  }
} }];