// NORMALIZE FEED + MARGINS v2
// FIX: g: namespace fields use bracket notation (p['g:id'] not p.g_id)
// FIX: DEFAULT rule from margin_rules is used as fallback
const config = $node['Margin Resolver'].json;
const marginRules = config.MARGIN_RULES || [];
const defaultMargin = config.DEFAULT_MARGIN || 0.10;

function normalizeUrl(url) {
  if (!url) return '';
  let u = url.toLowerCase().replace(/^https?:\/\/(www\.)?/, '').split('?')[0].replace(/\/$/, '');
  return u;
}

function resolveMargin(feedId, feedCategory, feedTitle) {
  const id = (feedId || '').trim();
  const cat = (feedCategory || '').toLowerCase().trim();
  const title = (feedTitle || '').toLowerCase().trim();
  const searchStr = cat + ' ' + title;
  for (const rule of marginRules) {
    if (rule.match_type === 'SKU_EXACT' && id === rule.match_value) return rule.margin_rate;
    if (rule.match_type === 'CATEGORY_EXACT' && cat === rule.match_value.toLowerCase()) return rule.margin_rate;
    if (rule.match_type === 'KEYWORD' && searchStr.includes(rule.match_value.toLowerCase())) return rule.margin_rate;
  }
  return defaultMargin;
}

const feedData = $input.first().json;
let products = [];
if (feedData.rss?.channel?.item) products = [feedData.rss.channel.item].flat();
else if (feedData.feed?.entry) products = [feedData.feed.entry].flat();
else if (feedData.products?.product) products = [feedData.products.product].flat();

return products.map(p => {
  const id = p['g:id'] || p.g_id || p.id || '';
  const cat = p['g:product_type'] || p['g:google_product_category'] || p.product_type || p.google_product_category || '';
  const link = p['g:link'] || p.g_link || p.link || '';
  const priceRaw = p['g:price'] || p.g_price || p.price || '0';
  const title = p['g:title'] || p.g_title || p.title || '';
  const brand = p['g:brand'] || p.g_brand || p.brand || '';

  return {
    json: {
      feed_id: id,
      feed_title: title,
      feed_brand: brand,
      feed_price: parseFloat(String(priceRaw).replace(/[^0-9.]/g, '')) || 0,
      feed_category: cat,
      feed_link: link,
      norm_url_path: normalizeUrl(link).split('/').slice(1).join('/'),
      base_gross_margin: resolveMargin(id, cat, title)
    }
  };
});