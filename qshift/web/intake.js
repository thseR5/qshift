const el = id => document.getElementById(id);
const roles = {designer: 'demo-designer-token', approver: 'demo-approver-token'};
const samples = [
  'Hi, need a wardrobe in the second bedroom.',
  'White laminate please. About 8 ft wide.',
  '7 feet',
];
const itemizedSamples = [
  'Need a white laminate wardrobe in the second bedroom, 8 ft wide and 7 ft tall. Also a gypsum false ceiling in the living room.',
  'Living room gypsum ceiling area is 100 sq ft.',
];
const labels = {item: 'Item', room: 'Room', finish: 'Finish', width_ft: 'Width (ft)', height_ft: 'Height (ft)', area: 'Area (sq ft)'};
const itemFields = {
  'WARDROBE-WHITE-LAMINATE': {label: 'Wardrobe', fields: ['room', 'finish', 'width_ft', 'height_ft']},
  'FALSE-CEILING-GYPSUM': {label: 'Gypsum ceiling', fields: ['room', 'area']},
};
let intake = null;
let busy = false;
let previewOpen = false;
let rehearsalRates = null;
let pendingEvent = null;
const studioMode = document.body.dataset.mode === 'studio';
let studioIdentity = null;

function isApprover() {
  if (studioMode) return ['APPROVER', 'OWNER'].includes(studioIdentity?.role);
  return el('role').value === 'approver';
}

function headers(json = false) {
  return {
    ...(!studioMode ? {Authorization: 'Bearer ' + roles[el('role').value]} : {}),
    ...(json ? {'Content-Type': 'application/json'} : {}),
  };
}

async function request(path, method = 'GET', body) {
  const response = await fetch(path, {
    method, headers: headers(body !== undefined),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Check the values and try again.');
  }
  return data;
}

function intakePath(suffix = '') {
  return '/api/simulated-intakes/' + encodeURIComponent(intake.project_id) + suffix;
}

function addText(parent, tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  parent.append(node);
  return node;
}

function addConcept(parent, path) {
  const figure = document.createElement('figure');
  figure.className = 'concept';
  const image = document.createElement('img');
  image.src = path;
  image.alt = 'AI concept image of a matte white laminate wardrobe with flat doors';
  image.loading = 'lazy';
  figure.append(image);
  addText(figure, 'figcaption', 'AI-generated sample. Finish and hardware are illustrative.');
  parent.append(figure);
}

function run(action) {
  return async event => {
    event?.preventDefault();
    if (busy) return;
    busy = true;
    el('status').textContent = 'Working…';
    try {
      await action();
      el('status').textContent = '';
    } catch (error) {
      el('status').textContent = error.message;
    } finally {
      busy = false;
    }
  };
}

async function downloadPdf(path) {
  const response = await fetch(path, {headers: headers()});
  if (!response.ok) throw new Error('Could not download the approved PDF.');
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = 'qshift-approved-quotation-v1.pdf';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function render() {
  el('workspace').hidden = false;
  el('chat-heading').textContent = intake.chat_id ? 'Simulated WhatsApp client chat' : 'Simulated client chat';
  el('chat-form').hidden = Boolean(intake.draft);
  const chat = el('messages');
  chat.replaceChildren();
  if (!intake.messages.length) addText(chat, 'p', 'Start with the client’s first message.');
  for (const message of intake.messages) {
    const bubble = document.createElement('div');
    bubble.id = 'message-' + message.id;
    bubble.className = 'message ' + message.role;
    addText(bubble, 'strong', message.role === 'client' ? 'Fictional client' : 'QShift');
    addText(bubble, 'span', message.text);
    if (message.pdf_path) {
      const button = addText(bubble, 'button', 'Download approved PDF');
      button.className = 'secondary';
      button.style.display = 'block';
      button.onclick = run(() => downloadPdf(message.pdf_path));
    }
    if (message.concept_preview) addConcept(bubble, message.concept_preview);
    chat.append(bubble);
  }
  chat.scrollTop = chat.scrollHeight;

  const brief = el('brief');
  el('extraction').textContent = intake.extraction
    ? 'Brief interpreted on this Mac by ' + intake.extraction + '.'
    : (intake.messages.some(message => message.role === 'client') ? 'Brief interpreted by offline rules.' : '');
  brief.replaceChildren();
  if (intake.scenario === 'itemized') {
    for (const item of intake.items) {
      const config = itemFields[item.sku];
      for (const field of config.fields) {
        addFact(brief, config.label + ' · ' + labels[field], item.facts[field]);
      }
    }
  } else {
    for (const field of ['item', 'room', 'finish', 'width_ft', 'height_ft']) {
      addFact(brief, labels[field], intake.brief[field]);
    }
  }
  renderReview();
}

function addFact(brief, label, fact) {
    const row = document.createElement('div');
    addText(row, 'dt', label);
    const value = addText(row, 'dd', fact?.value ?? 'Awaiting detail');
    if (fact) {
      const source = addText(value, 'a', 'Source message');
      source.href = '#message-' + fact.source;
    }
    brief.append(row);
}

function formatMoney(value) {
  const paise = BigInt(value);
  const cents = paise % 100n;
  return '₹' + (paise / 100n).toLocaleString('en-IN') +
    (cents ? '.' + String(cents).padStart(2, '0') : '');
}

function renderReview() {
  const review = el('review');
  review.replaceChildren();
  const draft = intake.draft;
  if (!draft) {
    addText(review, 'p', 'The first quote will appear once the required details and verified rate are available.');
    return;
  }
  addText(review, 'h3', draft.status === 'APPROVED' ? 'Approved quote · v1' : 'First quote · draft');
  const inputs = [];
  for (const line of draft.lines ?? [draft.line]) {
    const card = document.createElement('div');
    card.className = 'quote-line';
    addText(card, 'strong', line.room + ' · ' + line.description);
    addText(card, 'p', line.quantity + ' sq ft × ' + formatMoney(line.rate_paise) + ' · ' + formatMoney(line.total_paise));
    if (draft.status === 'DRAFT_READY') inputs.push(addQuantityEditor(card, draft, line));
    review.append(card);
  }
  addText(review, 'p', 'Quote total ' + draft.total);
  if (draft.concept_preview) renderConcept(review, draft);
  if (draft.status !== 'DRAFT_READY') return;

  const approve = addText(review, 'button', 'Approve reviewed quote');
  approve.className = 'secondary';
  const canApprove = isApprover();
  approve.disabled = !canApprove;
  if (!canApprove) addText(review, 'p', studioMode
    ? 'A studio owner or approver must authorize this version.'
    : 'Switch to the Approver demo role to authorize this version.');
  for (const input of inputs) {
    input.oninput = () => {
      approve.disabled = !canApprove || inputs.some(field => field.value !== field.defaultValue);
    };
  }
  approve.onclick = run(async () => {
    const {token} = await request('/api/drafts/' + draft.id + '/approval-token', 'POST', {expected_hash: draft.hash});
    await request('/api/approvals/commit', 'POST', {token});
    intake = await request(intakePath());
    render();
  });
}

function addQuantityEditor(card, draft, line) {
  const form = document.createElement('form');
  const label = addText(form, 'label', 'Adjust billable area (sq ft)');
  label.htmlFor = 'quantity-' + line.line_id;
  const quantity = document.createElement('input');
  Object.assign(quantity, {
    id: label.htmlFor, type: 'number', min: '0.0001', max: '400', step: '0.0001',
    required: true, defaultValue: line.quantity,
  });
  const row = document.createElement('div');
  row.className = 'row';
  form.append(row);
  row.append(quantity);
  addText(row, 'button', 'Recalculate');
  form.onsubmit = run(async () => {
    intake = await request(intakePath('/draft'), 'PATCH', {
      quantity: quantity.value, expected_hash: draft.hash, line_id: line.line_id,
    });
    render();
  });
  card.append(form);
  return quantity;
}

function renderConcept(review, draft) {
  const details = document.createElement('details');
  details.className = 'concept-panel';
  details.open = previewOpen;
  details.ontoggle = () => { previewOpen = details.open; };
  addText(details, 'summary', 'View AI concept preview');
  addConcept(details, draft.concept_preview);
  if (draft.concept_attached) {
    addText(details, 'p', 'Attached in the simulated client chat.');
  } else if (draft.version_id && isApprover()) {
    const attach = addText(details, 'button', 'Attach preview in simulated chat');
    attach.className = 'secondary';
    attach.onclick = run(async () => {
      intake = await request(intakePath('/concept'), 'POST', {version_id: draft.version_id});
      render();
    });
  } else {
    addText(details, 'p', 'An approver can attach the preview after approving the quote.');
  }
  review.append(details);
}

const startSample = scenario => run(async () => {
  const seeded = await fetch('/api/demo/seed', {method: 'POST'});
  if (!seeded.ok) throw new Error('Could not load fictional demo data.');
  intake = await request('/api/simulated-intakes', 'POST', {scenario});
  openIntake();
});
if (!studioMode) {
  el('start').onclick = startSample('wardrobe');
  el('start-itemized').onclick = startSample('itemized');
}

function openIntake() {
  previewOpen = false;
  pendingEvent = null;
  if (!studioMode) sessionStorage.setItem('qshift-intake-project', intake.project_id);
  el('message').value = '';
  render();
}

function updateRateButtons() {
  const ready = rehearsalRates?.verified;
  el('verify-rates').disabled = !rehearsalRates || ready || el('role').value !== 'approver';
  el('start-whatsapp').disabled = !ready;
}

if (!studioMode) {
el('load-rates').onclick = run(async () => {
  const seeded = await fetch('/api/demo/seed', {method: 'POST'});
  if (!seeded.ok) throw new Error('Could not load fictional demo data.');
  const file = await fetch('/templates/whatsapp_rehearsal_rates.csv');
  if (!file.ok) throw new Error('The fictional rate card could not be loaded.');
  const form = new FormData();
  form.append('file', await file.blob(), 'whatsapp_rehearsal_rates.csv');
  const response = await fetch('/api/imports/rate-card', {
    method: 'POST', headers: headers(), body: form,
  });
  const imported = await response.json();
  if (!response.ok || imported.accepted !== 2) throw new Error('Could not import both sample rates.');
  rehearsalRates = {id: imported.rate_card_id, entries: imported.entries, verified: false};
  el('rate-status').textContent = 'Two rates imported. Choose the Approver role to verify them.';
  updateRateButtons();
});

el('verify-rates').onclick = run(async () => {
  for (const entry of rehearsalRates.entries) {
    await request('/api/imports/rate-card/verify', 'POST', {entry_id: entry.id});
  }
  rehearsalRates.verified = true;
  el('rate-status').textContent = 'Two verified rates. Start a simulated client chat.';
  updateRateButtons();
});

el('start-whatsapp').onclick = run(async () => {
  intake = await request('/api/simulated-whatsapp/chats', 'POST', {rate_card_id: rehearsalRates.id});
  openIntake();
});
}

function webhookPayload(chatId, messageId, text) {
  return {
    object: 'whatsapp_business_account',
    entry: [{
      id: 'qshift-sim-account',
      changes: [{
        field: 'messages',
        value: {
          metadata: {phone_number_id: 'qshift-sim-number'},
          messages: [{id: messageId, from: 'sim-client-' + chatId, type: 'text', text: {body: text}}],
        },
      }],
    }],
  };
}

el('chat-form').onsubmit = run(async () => {
  const value = el('message').value.trim();
  if (!value) return;
  if (intake.chat_id) {
    if (!pendingEvent || pendingEvent.text !== value) {
      pendingEvent = {id: 'sim-msg-' + crypto.randomUUID(), text: value};
    }
    intake = await request(
      '/api/simulated-whatsapp/webhook', 'POST',
      webhookPayload(intake.chat_id, pendingEvent.id, value),
    );
    pendingEvent = null;
  } else {
    intake = await request(intakePath('/messages'), 'POST', {text: value});
  }
  el('message').value = '';
  render();
});
el('sample').onclick = () => {
  const count = intake.messages.filter(message => message.role === 'client').length;
  const script = intake.scenario === 'itemized' ? itemizedSamples : samples;
  el('message').value = script[count] ?? '';
  el('message').focus();
};
if (!studioMode) el('role').onchange = () => {
  updateRateButtons();
  if (intake) renderReview();
};

const saved = studioMode ? null : sessionStorage.getItem('qshift-intake-project');
if (saved) {
  run(async () => {
    intake = await request('/api/simulated-intakes/' + encodeURIComponent(saved));
    render();
  })();
}
