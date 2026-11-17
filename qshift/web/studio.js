let cards = [];

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

el('import-form').onsubmit = run(async () => {
  const file = el('rate-document').files[0];
  const form = new FormData();
  form.append('file', file, file.name);
  const response = await fetch('/api/imports/rate-card', {method: 'POST', body: form});
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || 'Import could not be completed.');
  el('import-result').textContent = [
    result.accepted + ' rates imported as unverified.',
    ...result.errors, ...result.warnings,
  ].join(' ');
  await refreshStudio(undefined, result.rate_card_id);
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
