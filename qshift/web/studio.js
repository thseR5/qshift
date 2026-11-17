let cards = [];
let pendingRateImport = null;
let pendingQuotationImport = null;

function optionList(element, rows, label, selected) {
  element.replaceChildren();
  for (const row of rows) {
    const option = addText(element, 'option', label(row));
    option.value = row.id;
  }
  if (rows.some(row => row.id === selected)) element.value = selected;
}

async function refreshStudio(projectId = el('project-picker').value, cardId = el('card-picker').value) {
  const [projects, rateCards] = await Promise.all([
    request('/api/projects'), request('/api/studio/rate-cards'),
  ]);
  cards = rateCards;
  optionList(el('project-picker'), projects, project => project.name, projectId);
  optionList(el('card-picker'), cards, card => 'Rate card v' + card.version, cardId);
  showRates();
}

function showRates() {
  const rates = el('rate-entries');
  rates.replaceChildren();
  const card = cards.find(row => row.id === el('card-picker').value);
  el('create-chat').disabled = !card || !el('project-picker').value;
  el('open-chat').disabled = !el('project-picker').value;
  if (!card) return;
  for (const entry of card.entries) {
    const row = addText(rates, 'p', entry.name + ' · ' + formatMoney(entry.rate_paise)
      + '/' + entry.unit + ' · ' + (entry.verified ? 'Verified' : 'Unverified'));
    if (!entry.verified && isApprover()) {
      const button = addText(row, 'button', 'Verify ' + entry.name);
      button.className = 'secondary';
      button.onclick = run(async () => {
        await request('/api/imports/rate-card/verify', 'POST', {entry_id: entry.id});
        await refreshStudio();
      });
    }
  }
}

async function openStudio() {
  studioIdentity = await request('/api/studio/session');
  el('studio-name').textContent = studioIdentity.firm;
  el('member-name').textContent = studioIdentity.name + ' · ' + studioIdentity.role;
  await refreshStudio();
  el('signed-in').hidden = false;
  el('sign-out').hidden = false;
  el('sign-in').hidden = true;
}

el('login-form').onsubmit = run(async () => {
  const password = el('studio-password');
  try {
    await request('/api/studio/session', 'POST', {
      studio: el('studio-slug').value, username: el('studio-user').value, password: password.value,
    });
    await openStudio();
  } finally {
    password.value = '';
  }
});

el('sign-out').onclick = run(async () => {
  const response = await fetch('/api/studio/session', {method: 'DELETE'});
  if (!response.ok) throw new Error('Could not sign out.');
  location.reload();
});

el('project-form').onsubmit = run(async () => {
  const name = el('project-name').value.trim();
  const project = await request('/api/projects', 'POST', {name});
  el('project-name').value = '';
  await refreshStudio(project.id);
});

function renderMapping(panelId, fieldsId, preview, requiredFields) {
  const fields = el(fieldsId);
  fields.replaceChildren();
  const options = [''].concat(preview.headers);
  const allFields = [...requiredFields, 'name', 'category', 'aliases', 'gst_percent', 'gst_bps']
    .filter((field, index, values) => values.indexOf(field) === index);
  for (const field of allFields) {
    const row = document.createElement('label');
    row.className = 'mapping-row';
    addText(row, 'span', field + (requiredFields.includes(field) ? ' *' : ''));
    const select = document.createElement('select');
    select.dataset.field = field;
    for (const header of options) addText(select, 'option', header || '— not mapped —').value = header;
    select.value = preview.mapping[field] || '';
    row.append(select);
    fields.append(row);
  }
  el(panelId).hidden = false;
}

function selectedMapping(fieldsId) {
  const mapping = {};
  for (const select of el(fieldsId).querySelectorAll('select')) {
    if (select.value) mapping[select.dataset.field] = select.value;
  }
  return mapping;
}

async function previewFile(file, endpoint, panelId, fieldsId, requiredFields) {
  const form = new FormData();
  form.append('file', file, file.name);
  const response = await fetch(endpoint, {method: 'POST', headers: headers(), body: form});
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || 'Preview could not be created.');
  if (result.missing_required.length) {
    throw new Error('Missing required fields: ' + result.missing_required.join(', '));
  }
  renderMapping(panelId, fieldsId, result, requiredFields);
  return result;
}

el('import-form').onsubmit = run(async () => {
  const file = el('rate-document').files[0];
  if (!file) throw new Error('Choose a rate card first.');
  pendingRateImport = file;
  await previewFile(file, '/api/imports/rate-card/preview', 'rate-mapping-panel', 'rate-mapping-fields', ['sku', 'unit', 'rate_paise']);
  el('import-result').textContent = 'Mapping preview ready. Review the fields, then confirm the import.';
});

el('confirm-rate-import').onclick = run(async () => {
  if (!pendingRateImport) throw new Error('Preview a rate card first.');
  const form = new FormData();
  form.append('file', pendingRateImport, pendingRateImport.name);
  form.append('mapping', JSON.stringify(selectedMapping('rate-mapping-fields')));
  const response = await fetch('/api/imports/rate-card', {method: 'POST', headers: headers(), body: form});
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || 'Import could not be completed.');
  el('import-result').textContent = [result.accepted + ' rates imported as unverified.', ...result.errors, ...result.warnings].join(' ');
  el('rate-mapping-panel').hidden = true;
  pendingRateImport = null;
  await refreshStudio(undefined, result.rate_card_id);
});

el('quotation-import-form').onsubmit = run(async () => {
  const file = el('quotation-document').files[0];
  if (!file) throw new Error('Choose a quotation first.');
  pendingQuotationImport = file;
  await previewFile(file, '/api/imports/quotation/preview', 'quotation-mapping-panel', 'quotation-mapping-fields', ['room', 'sku', 'quantity']);
  el('quotation-import-result').textContent = 'Mapping preview ready. Review the fields, then confirm the import.';
});

el('confirm-quotation-import').onclick = run(async () => {
  if (!pendingQuotationImport || !el('project-picker').value) throw new Error('Choose a project and preview a quotation first.');
  const form = new FormData();
  form.append('file', pendingQuotationImport, pendingQuotationImport.name);
  form.append('mapping', JSON.stringify(selectedMapping('quotation-mapping-fields')));
  const response = await fetch('/api/imports/quotation?project_id=' + encodeURIComponent(el('project-picker').value), {method: 'POST', headers: headers(), body: form});
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || 'Quotation import could not be completed.');
  el('quotation-import-result').textContent = result.valid_rows + ' quotation rows imported into the selected project.';
  el('quotation-mapping-panel').hidden = true;
  pendingQuotationImport = null;
  await refreshStudio();
});

el('card-picker').onchange = el('project-picker').onchange = showRates;
el('create-chat').onclick = run(async () => {
  intake = await request('/api/simulated-whatsapp/chats', 'POST', {
    project_id: el('project-picker').value, rate_card_id: el('card-picker').value,
  });
  openIntake();
});

el('open-chat').onclick = run(async () => {
  intake = await request('/api/simulated-intakes/' + encodeURIComponent(el('project-picker').value));
  openIntake();
});

openStudio().catch(() => {
  el('sign-in').hidden = false;
});
