// SAVE NEW BRAND CONFIG
const config = $node['Margin Resolver'].json;
if (!config._is_new_brand) return [];
return [{ json: {
  brand_name: config.BRAND,
  ga4_property_id: config.GA4_PROPERTY_ID,
  meta_account_id: config.META_ACCOUNT_ID,
  vat_rate: config.VAT_RATE,
  default_margin: config.DEFAULT_MARGIN,
  feed_url: config.FEED_URL,
  created_at: new Date().toISOString()
} }];