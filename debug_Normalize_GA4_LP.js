// NORMALIZE GA4 LP
return $input.first().json.rows.map(row => {
  const lp = row.dimensionValues[0].value || '';
  return { json: {
    ga4_lp_url: lp,
    ga4_norm_path: lp.toLowerCase().replace(/^\/|\/$/g, '').split('?')[0], // Match feed path
    ga4_sessions: parseInt(row.metricValues[0].value),
    ga4_revenue: parseFloat(row.metricValues[1].value),
    ga4_trans: parseInt(row.metricValues[2].value)
  }};
});