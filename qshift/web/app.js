const $=id=>document.getElementById(id);let draftId=null;let activeProject=null;let currentDraft=null;
const formatPaise=value=>{let paise=BigInt(value),rupees=paise/100n,cents=String(paise%100n).padStart(2,'0'),digits=String(rupees);if(digits.length>3)digits=digits.slice(0,-3).replace(/\B(?=(\d{2})+(?!\d))/g,',')+','+digits.slice(-3);return '₹'+digits+(cents==='00'?'':'.'+cents)};
const api=async(path,method='GET',body=null)=>{const r=await fetch(path,{method,headers:{'Content-Type':'application/json','Authorization':'Bearer '+$('user').value},body:body?JSON.stringify(body):undefined});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Request failed');return data};
function addBubble(text,who='assistant'){const div=document.createElement('div');div.className='bubble '+who;div.textContent=text;$('chat').append(div);$('chat').scrollTop=$('chat').scrollHeight;return div}
async function boot(){await fetch('/api/demo/seed',{method:'POST'});const list=await api('/api/projects');$('project').innerHTML=list.map(p=>`<option value="${p.id}">${p.name}</option>`).join('');$('project').value='project-sharma';activeProject=$('project').value;await api('/api/projects/pin','POST',{project_id:activeProject});}
function renderDraft(d){currentDraft=d;draftId=d.id;$('status').textContent=d.status==='DRAFT_READY'?'Ready for review':'Needs your input';const node=$('draft');node.className='';node.innerHTML='';for(const op of d.ops){let x=document.createElement('div');x.className='op';x.innerHTML=`<b>${op.op}</b> · ${op.room||'Project'} · ${op.target_text||''}<br><span>${op.status==='NEEDS_INFO'?'Select a verified catalogue rate to continue.':'Verified against the quotation.'}</span>`;node.append(x);if(op.status==='NEEDS_INFO'&&op.options?.length){for(const opt of op.options){let b=document.createElement('button');b.className='option';b.textContent=`${opt.name} · ${opt.unit} · ${formatPaise(opt.rate_paise)} / ${opt.unit}`;b.onclick=async()=>{try{renderDraft(await api(`/api/drafts/${d.id}/catalogue-selection`,'POST',{sku:opt.sku}));addBubble('Catalogue option selected: '+opt.name,'user')}catch(e){addBubble(e.message)}};node.append(b)}}}if(d.line_diffs){let diff=document.createElement('div');diff.className='fine';diff.innerHTML='<b>Line differences (before GST)</b><br>'+d.line_diffs.filter(x=>x.kind!=='unchanged').map(x=>`${x.kind}: ${x.room} · ${x.description} · ${x.delta}`).join('<br>');node.append(diff)}let price=document.createElement('div');price.innerHTML=`<div class="price"><span>GST change (included)</span><b>${formatPaise(BigInt(d.revised_gst_paise)-BigInt(d.original_gst_paise))}</b></div><div class="price"><span>Current approved</span><b>${d.original_total}</b></div><div class="price"><span>Proposed change</span><b>${d.net_change}</b></div><div class="price total"><span>Revised total</span><span>${d.revised_total}</span></div>`;node.append(price);if(d.status==='DRAFT_READY'){let b=document.createElement('button');b.className='approve';b.textContent='Approve exact revision';b.onclick=approve;b.disabled=$('user').value==='demo-designer-token';node.append(b);let note=document.createElement('div');note.className='fine';note.textContent=b.disabled?'Designer role can prepare drafts. Switch to an authorized approver to approve.':'Approval is server checked and bound to this draft.';node.append(note);let rejectButton=document.createElement('button');rejectButton.className='quiet';rejectButton.textContent='Reject draft';rejectButton.onclick=async()=>{try{await api(`/api/drafts/${draftId}/reject`,'POST',{});$('status').textContent='Rejected';addBubble('Draft rejected and recorded in project history.')}catch(e){addBubble(e.message)}};node.append(rejectButton)}else{let note=document.createElement('div');note.className='fine';note.textContent='Clarification is required before this draft can be approved.';node.append(note)}}
function selectChatProject(projectId) {
  if (activeProject !== projectId) {
    currentDraft = null;
    draftId = null;
    $('status').textContent = 'No draft';
    $('draft').textContent = 'Send status to see any open draft for this project.';
  }
  activeProject = projectId;
  $('project').value = projectId;
}

async function sendText(text) {
  addBubble(text, 'user');
  try {
    const result = await api('/api/simulated-chat/messages', 'POST', {
      text,
      project_id: activeProject,
      draft_id: draftId,
    });
    if (result.project_id) selectChatProject(result.project_id);
    if (result.draft) renderDraft(result.draft);
    addBubble(result.reply);
  } catch (error) {
    addBubble(error.message);
  }
}
function pdfButton(path, version, label) {
  const button = document.createElement('button');
  button.className = 'option';
  button.textContent = label;
  button.onclick = async () => {
    try {
      const response = await fetch(path, {headers: {Authorization: 'Bearer ' + $('user').value}});
      if (!response.ok) throw new Error('Could not download this quotation.');
      const url = URL.createObjectURL(await response.blob());
      const download = document.createElement('a');
      download.href = url;
      download.download = `qshift-quotation-v${version}.pdf`;
      download.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      addBubble(error.message);
    }
  };
  return button;
}

async function approve() {
  try {
    const {token} = await api(`/api/drafts/${draftId}/approval-token`, 'POST', {});
    const result = await api('/api/approvals/commit', 'POST', {token});
    addBubble(`Approved quotation version ${result.version} is ready. Total: ${result.total}. The PDF is available in version history.`);
    currentDraft = null;
    draftId = null;
    $('status').textContent = 'Approved · v' + result.version;
    $('draft').querySelectorAll('button').forEach(button => { button.disabled = true; });
    $('draft').append(pdfButton(`/api/versions/${result.version_id}/pdf`, result.version, 'Download approved PDF'));
  } catch (error) {
    addBubble(error.message);
  }
}

async function showHistory() {
  const panel = $('side-result');
  try {
    const versions = await api(`/api/projects/${$('project').value}/versions`);
    panel.replaceChildren();
    for (const version of versions) {
      const row = document.createElement('div');
      row.textContent = `v${version.version} · ${version.status} · ${version.total} `;
      row.append(pdfButton(version.pdf_path, version.version, 'PDF'));
      panel.append(row);
    }
  } catch (error) {
    panel.textContent = error.message;
  }
}

async function showFoundingPlan() {
  const panel = $('founding-terms');
  try {
    const plan = await api('/api/pricing');
    $('founding-price').textContent = `Founding plan · ${formatPaise(plan.monthly_paise)}/month`;
    const annualSavings = plan.monthly_paise * 12 - plan.annual_paise;
    const terms = [
      `${formatPaise(plan.annual_paise)}/year prepaid. Save ${formatPaise(annualSavings)}.`,
      `First ${plan.founding_firms} firms. Price locked for ${plan.price_lock_months} months.`,
      `${plan.included_firms} firm, ${plan.included_users} users and ${plan.included_monthly_revisions} approved revisions per month.`,
      `${formatPaise(plan.overage_paise)} per extra approved revision with your opt-in.`,
      `${formatPaise(plan.onboarding_paise)} onboarding, including rate-card cleanup.`,
      `Planned list price after the founding cohort and usage review is ${formatPaise(plan.future_monthly_paise)}/month.`,
      'GST extra where applicable. Pricing preview only.',
    ];
    for (const term of terms) {
      const line = document.createElement('p');
      line.textContent = term;
      panel.append(line);
    }
  } catch {
    panel.textContent = 'Pricing details are temporarily unavailable.';
  }
}

showFoundingPlan();
async function showMemory(){try{const m=await api(`/api/projects/${$('project').value}/memory`);$('side-result').textContent=`${m.project}: ${m.requested} recorded requested operation(s), ${m.included} included, ${m.pending} pending, ${m.rejected} rejected.`;addBubble(`Stored project records show ${m.requested} requested change operation(s): ${m.included} included, ${m.pending} pending, ${m.rejected} rejected.`)}catch(e){$('side-result').textContent=e.message}}
$('send').onclick=()=>{const text=$('message').value.trim();if(text){$('message').value='';sendText(text)}};$('message').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('send').click()}};$('pin').onclick = async () => {
  try {
    const project = await api('/api/projects/pin', 'POST', {project_id: $('project').value});
    selectChatProject(project.id);
    addBubble('Pinned project: ' + project.name + '.');
  } catch (error) {
    addBubble(error.message);
  }
};
$('user').onchange=()=>{if(currentDraft)renderDraft(currentDraft)};$('history').onclick=showHistory;$('memory').onclick=showMemory;$('voice').onclick=async()=>{try{const transcript=await api('/api/transcripts/telugu_quartz_change');addBubble('Mock voice fixture transcript (please confirm): “'+transcript.text+'”');const b=document.createElement('button');b.className='option';b.textContent='Confirm transcript and prepare draft';b.onclick=()=>sendText(transcript.text);$('chat').append(b)}catch(e){addBubble(e.message)}};boot().catch(e=>addBubble(e.message));

async function uploadForm(url,fileId){const file=$(fileId).files[0];if(!file)throw new Error('Choose a CSV or XLSX file first.');const form=new FormData();form.append('file',file);const response=await fetch(url,{method:'POST',headers:{'Authorization':'Bearer '+$('user').value},body:form});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Import failed');return data}
$('create-project').onclick=async()=>{try{const name=$('project-name').value.trim();if(!name)throw new Error('Enter a project name.');const created=await api('/api/projects','POST',{name,client_label:'Fictional demo client'});const projects=await api('/api/projects');$('project').innerHTML=projects.map(p=>`<option value="${p.id}">${p.name}</option>`).join('');$('project').value=created.id;$('project-name').value='';addBubble(`Created fictional project ${created.name}. Pin it before submitting changes.`)}catch(e){addBubble(e.message)}};
$('upload-rate').onclick=async()=>{try{const result=await uploadForm('/api/imports/rate-card','rate-file');const box=$('rate-results');box.innerHTML='';for(const entry of result.entries){const row=document.createElement('div');row.className='rate-row';const name=document.createElement('span');name.textContent=`${entry.sku} · ${entry.name}`;const button=document.createElement('button');button.className='quiet';button.textContent='Verify';button.onclick=async()=>{try{await api('/api/imports/rate-card/verify','POST',{entry_id:entry.id});button.textContent='Verified';button.disabled=true}catch(e){addBubble(e.message)}};row.append(name,button);box.append(row)}addBubble(`Imported ${result.accepted} rate(s) as unverified. An OWNER or APPROVER must verify each one before use.`);if(result.errors.length)addBubble(result.errors.join('\n'));if(result.warnings.length)addBubble(result.warnings.join('\n'))}catch(e){addBubble(e.message)}};
$('upload-quote').onclick=async()=>{try{if(!activeProject)throw new Error('Pin a project before importing a quotation.');const result=await uploadForm(`/api/imports/quotation?project_id=${encodeURIComponent(activeProject)}`,'quote-file');addBubble(`Imported quotation version ${result.version} to the pinned project. Total: ${result.total}.`)}catch(e){addBubble(e.message)}};
