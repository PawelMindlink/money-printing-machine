// NORMALIZE META ADS
const data = $input.first().json.data || [];
return data.map(ad => {
  const getVal = (list, type) => {
    if (!list) return 0;
    const m = list.find(x => x.action_type === type);
    return m ? parseFloat(m.value) : 0;
  };
  const purch = getVal(ad.actions, 'offsite_conversion.fb_pixel_purchase') || getVal(ad.actions, 'purchase');
  const val = getVal(ad.action_values, 'offsite_conversion.fb_pixel_purchase') || getVal(ad.action_values, 'purchase');
  const spend = parseFloat(ad.spend || '0');
  
  return { json: {
    meta_ad_id: ad.ad_id,
    meta_ad_name: ad.ad_name,
    meta_spend: spend,
    meta_purch: purch,
    meta_rev: val,
    meta_roas: spend > 0 ? val / spend : 0
  }};
});