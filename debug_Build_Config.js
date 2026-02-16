// ============================================================
// BUILD CONFIG v2 — Single Source of Truth (brand_config)
// VAT and Default Margin come from brand_config, not form.
// ============================================================

const formData = $node['Parse Form'].json;

const HARDCODED = {
  'iiyama': { ga4: '280127077', meta: 'act_1438113836305522' },
  'bushido': { ga4: '297192186', meta: 'act_1930400651212132' },
  'koszulkowy': { ga4: '270928705', meta: 'act_1897121353740892' },
  'mindlink': { ga4: '477769901', meta: 'act_1578563932814949' }
};

const sheetBrands = $input.all().map(i => i.json);
const sheetMatch = sheetBrands.find(row =>
  (row.brand_name || '').toLowerCase().trim() === formData._brand_key
);

// VAT and DEFAULT_MARGIN from brand_config (Single Source of Truth)
const vatRate = sheetMatch ? (parseFloat(sheetMatch.vat_rate) || 0.23) : 0.23;
const defaultMargin = sheetMatch ? (parseFloat(sheetMatch.default_margin) || 0.10) : 0.10;

if (!sheetMatch) {
  throw new Error(`Brand "${formData._brand_name}" not found in brand_config sheet. Add a row with brand_name="${formData._brand_name}" first.`);
}

const hardcoded = HARDCODED[formData._brand_key];
const ga4Id = formData._form_ga4_id
  || (sheetMatch ? (sheetMatch.ga4_property_id || '') : '')
  || (hardcoded ? hardcoded.ga4 : '');
const metaId = formData._form_meta_id
  || (sheetMatch ? (sheetMatch.meta_account_id || '') : '')
  || (hardcoded ? hardcoded.meta : '');

if (!ga4Id) throw new Error(`GA4 Property ID missing for "${formData._brand_name}"`);
if (!metaId) throw new Error(`Meta Account ID missing for "${formData._brand_name}"`);

const isNewBrand = !hardcoded && !sheetMatch;

return [{
  json: {
    BRAND: formData._brand_name,
    VAT_RATE: vatRate,
    DEFAULT_MARGIN: defaultMargin,
    FEED_URL: formData._feed_url,
    SHEET_ID: formData._sheet_id,
    GA4_PROPERTY_ID: ga4Id,
    META_ACCOUNT_ID: metaId,
    DATE_FROM: formData._date_from,
    DATE_TO: formData._date_to,
    MSC_ALGO: { MIN_META_TRANS: 10, MIN_ORGANIC_SESSIONS: 300 },
    _is_new_brand: isNewBrand
  }
}];