// NORMALIZE GA4 ITEMS
return $input.first().json.rows.map(row => {
  return { json: {
    ga4_item_id: row.dimensionValues[0].value,
    ga4_item_views: parseInt(row.metricValues[0].value),
    ga4_item_rev: parseFloat(row.metricValues[1].value),
    ga4_item_purch: parseInt(row.metricValues[2].value)
  }};
});