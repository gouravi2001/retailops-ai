/**
 * RetailOps AI: Google Workspace integration (Apps Script V8 runtime).
 * Add to Extensions -> Apps Script in a Google Sheet.
 * Script Properties required:
 *   API_BASE_URL: publicly reachable HTTPS URL, e.g. https://api.example.com
 *   API_KEY: the same secret configured for FastAPI
 *   SPREADSHEET_ID: ID of the Google Sheet used for reports
 * Optional:
 *   REPORT_EMAIL: recipient address for scheduled summaries
 *
 * Localhost/Docker URLs DO NOT work from cloud-hosted Apps Script.
 */

function config_() {
  const p = PropertiesService.getScriptProperties();
  const base = p.getProperty('API_BASE_URL');
  const key = p.getProperty('API_KEY');
  const sheet = p.getProperty('SPREADSHEET_ID');
  if (!base || !base.startsWith('https://') || !key || !sheet) {
    throw new Error('Missing API_BASE_URL (HTTPS), API_KEY, or SPREADSHEET_ID in Script Properties');
  }
  return { base: base.replace(/\/$/, ''), key: key, sheet: sheet,
           email: p.getProperty('REPORT_EMAIL') };
}

function callApi_(path, method, body) {
  const c = config_();
  const options = {
    method: method || 'get',
    muteHttpExceptions: true,
    headers: { 'X-API-Key': c.key },
    contentType: 'application/json'
  };
  if (body) options.payload = JSON.stringify(body);
  const response = UrlFetchApp.fetch(c.base + path, options);
  const code = response.getResponseCode();
  if (code < 200 || code >= 300) {
    // Do not include secret-bearing request headers in logs.
    throw new Error('RetailOps API returned HTTP ' + code);
  }
  return JSON.parse(response.getContentText());
}

function writeTable_(spreadsheet, sheetName, headers, records) {
  const tab = spreadsheet.getSheetByName(sheetName) || spreadsheet.insertSheet(sheetName);
  tab.clearContents();
  tab.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (records.length > 0) {
    const rows = records.map(row => headers.map(h => row[h] == null ? '' : row[h]));
    tab.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  tab.setFrozenRows(1);
}

/** Manual or time-driven report sync. Run once to authorize Workspace scopes. */
function syncRetailOpsReport() {
  const c = config_();
  const report = callApi_('/api/metrics', 'get');
  const issues = callApi_('/api/issues', 'get');
  const spreadsheet = SpreadsheetApp.openById(c.sheet);
  const summary = Object.entries(report.summary).map(([metric, value]) => ({metric, value}));
  writeTable_(spreadsheet, 'KPI Summary', ['metric', 'value'], summary);
  writeTable_(spreadsheet, 'Store Performance',
    ['store_id', 'store_name', 'city', 'region', 'revenue_eur',
     'inventory_accuracy_pct', 'on_time_delivery_pct', 'active_issues'], report.by_store);
  writeTable_(spreadsheet, 'Issue Queue',
    ['id', 'store_name', 'region', 'kind', 'severity', 'status', 'description'], issues);
  Logger.log('RetailOps summary and issue queue synchronized');
}

/** Sends an optional daily email to a configured internal address. */
function sendDailySummary() {
  const c = config_();
  if (!c.email) throw new Error('REPORT_EMAIL Script Property is not configured');
  const s = callApi_('/api/metrics', 'get').summary;
  const body = [
    'RetailOps fictional demo: daily summary',
    'Stores: ' + s.stores_tracked,
    'Revenue: EUR ' + s.revenue_eur,
    'Inventory accuracy: ' + s.inventory_accuracy_pct + '%',
    'On-time deliveries: ' + s.on_time_delivery_pct + '%',
    'Active issues: ' + s.active_issues,
    'Use the dashboard to investigate anomalies. Data is fictional.'
  ].join('\n');
  MailApp.sendEmail({to: c.email, subject: 'RetailOps AI - Daily operations summary', body: body});
}

/**
 * Optional installable form-submit trigger, bound to a response spreadsheet.
 * Form question labels must be: Issue ID, Next Status, Reviewer, Review Note.
 * The backend enforces allowed transitions and creates the audit record.
 */
function onRetailOpsFormSubmit(e) {
  if (!e || !e.namedValues) throw new Error('Run via installed form-submit trigger');
  const get = (name) => (e.namedValues[name] || [''])[0].trim();
  const id = get('Issue ID');
  if (!/^[a-f0-9]{32}$/.test(id)) throw new Error('Malformed Issue ID');
  const status = get('Next Status');
  if (!['IN_REVIEW', 'RESOLVED', 'DISMISSED'].includes(status)) {
    throw new Error('Invalid requested status');
  }
  callApi_('/api/issues/' + id, 'patch', {
    status: status,
    actor: get('Reviewer'),
    note: get('Review Note')
  });
}

/** Create a single daily reporting trigger (avoids accumulating duplicates). */
function configureDailyTrigger() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'syncRetailOpsReport')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('syncRetailOpsReport').timeBased().everyDays(1).atHour(8).create();
}
