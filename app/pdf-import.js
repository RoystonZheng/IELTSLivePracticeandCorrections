(() => {
'use strict';

const KEY = 'ielts-pdf-papers-v1';
const main = document.getElementById('main');
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const normalize = value => String(value ?? '').trim().replace(/\s+/g, ' ').toLowerCase();
let papers = [];
try { papers = JSON.parse(localStorage.getItem(KEY) || '[]'); if (!Array.isArray(papers)) papers = []; } catch { papers = []; }
let draft = null;
let activeId = null;
let wrongOnly = false;
let saveTimer;
let pendingAudio = null;
let audioUrl = null;

function audioDatabase() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) return reject(new Error('当前浏览器不支持音频存储'));
    const request = indexedDB.open('ielts-pdf-audio-v1', 1);
    request.onupgradeneeded = () => request.result.createObjectStore('audio');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function audioRecord(id, file) {
  const db = await audioDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction('audio', file === undefined ? 'readonly' : 'readwrite');
      const request = file === undefined ? tx.objectStore('audio').get(id)
        : file === null ? tx.objectStore('audio').delete(id) : tx.objectStore('audio').put(file, id);
      let result;
      request.onsuccess = () => { result = request.result; };
      request.onerror = () => reject(request.error);
      tx.oncomplete = () => resolve(result);
      tx.onerror = () => reject(tx.error);
    });
  } finally { db.close(); }
}
async function attachAudio(paper) {
  const player = document.getElementById('pdf-listening-audio');
  if (!player) return;
  try {
    const blob = await audioRecord(paper.id);
    if (activeId !== paper.id || !player.isConnected) return;
    if (!blob) { player.replaceWith(document.createTextNode('音频未找到，请重新导入这份听力试卷。')); return; }
    audioUrl = URL.createObjectURL(blob);
    player.src = audioUrl;
  } catch { player.replaceWith(document.createTextNode('音频读取失败，请检查浏览器存储。')); }
}

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(papers)); return true; }
  catch { alert('浏览器存储空间不足。请删除旧的 PDF 练习后重试。'); return false; }
}
function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(save, 350); }
function activePaper() { return papers.find(paper => paper.id === activeId); }
function rememberSubmission(paper) {
  if (!paper?.submittedAt) return;
  paper.attempts ||= [];
  if (!paper.attempts.some(item => item.submittedAt === paper.submittedAt)) {
    paper.attempts.push({submittedAt:paper.submittedAt, answers:structuredClone(paper.answers || {}), annotations:structuredClone(paper.annotations || {})});
  }
}
function historyEntries() {
  return papers.flatMap(paper => {
    const attempts = [...(paper.attempts || [])];
    if (paper.submittedAt && !attempts.some(item => item.submittedAt === paper.submittedAt)) attempts.push({submittedAt:paper.submittedAt,answers:paper.answers || {},annotations:paper.annotations || {}});
    return attempts.map(attempt => {
      const keyed=canScore(paper)?paper.questions.filter(q=>normalize(q.answer)):[];
      const score=keyed.filter(q=>normalize(attempt.answers?.[q.id||q.number])===normalize(q.answer)).length;
      return {id:`pdf-${paper.id}-${attempt.submittedAt}`,type:'pdf',skill:paper.skill,mode:(paper.groups||[]).length>1?'full':'single',title:paper.title,at:attempt.submittedAt,paperId:paper.id,attempt,questions:paper.questions,referenceText:paper.referenceText,score:keyed.length?score:null,total:keyed.length||null};
    });
  });
}
function redoHistory(paperId) {
  const paper = papers.find(item => item.id === paperId);
  if (!paper) return false;
  rememberSubmission(paper);
  paper.answers = {};
  paper.annotations = {};
  paper.submittedAt = null;
  activeId = paperId;
  wrongOnly = false;
  save();
  return true;
}
function skillName(skill) { return {reading:'阅读',listening:'听力',writing:'写作',speaking:'口语'}[skill] || skill; }
function canScore(paper) { return paper.skill === 'reading' || paper.skill === 'listening'; }
function questionStatus(paper, question) {
  if (!canScore(paper) || !normalize(question.answer)) return 'unkeyed';
  return normalize(paper.answers?.[question.id || question.number]) === normalize(question.answer) ? 'right' : 'wrong';
}
function render() {
  if (audioUrl) { URL.revokeObjectURL(audioUrl); audioUrl = null; }
  window.IELTS_ANNOTATIONS_INSTANCE?.dismiss?.();
  if (draft) return renderPreview();
  if (activePaper()) return renderPractice(activePaper());
  renderLibrary();
}
function renderLibrary() {
  main.innerHTML = `<div class="page-head"><div><p class="kicker">Local PDF import</p><h1>导入 PDF 试卷</h1><p class="lede">从你自己的 PDF 提取题目，核对后在浏览器里练习。PDF 只发送到这台电脑运行的本地服务；文件本身不会写入仓库。</p></div><span class="badge blue">个人练习</span></div>
  <section class="panel pdf-upload"><h2>选择试卷</h2><p>支持含文字层的 PDF，最多 20 MB、80 页。扫描版请先做 OCR；表格、图片和复杂排版需要手动核对。</p>
  <div class="toolbar"><label class="pdf-file-label">PDF 文件<input id="pdf-file" type="file" accept="application/pdf,.pdf" multiple aria-label="选择 PDF 试卷"></label><label class="pdf-file-label">导入题型<select id="pdf-skill" aria-label="导入题型"><option value="reading">阅读</option><option value="listening">听力</option><option value="writing">写作</option><option value="speaking">口语</option></select></label><label id="pdf-audio-label" class="pdf-file-label" hidden>听力音频<input id="pdf-audio" type="file" accept="audio/*,.mp3,.m4a,.wav,.ogg,.webm" aria-label="选择对应的听力音频"></label><button class="btn" data-pdf-action="upload">解析 PDF</button></div>
  <p class="small muted">阅读、写作和口语可一次选多份 PDF，也会识别单份 PDF 中的多篇文章、任务或 Part。听力每次只导入一份 PDF，并须选择对应音频。</p>
  <p id="pdf-message" class="small muted">请用 <code>python3 bank_update.py --serve</code> 启动本地服务后导入。解析不调用 Codex CLI。</p></section>
  <div class="section-title"><h2>已保存的个人试卷</h2><span class="small muted">最多保存 5 份，保存在当前浏览器</span></div>
  <div class="link-list">${papers.length ? papers.map(paper => `<div class="link-row"><span><strong>${esc(paper.title)}</strong><small>${skillName(paper.skill)} · ${(paper.groups || []).length || 1} 组 · ${paper.questions.length} 题 · ${paper.pageCount} 页 · ${paper.submittedAt ? '已提交' : '可继续练习'}</small></span><span class="pdf-row-actions"><button class="btn secondary" data-pdf-action="open" data-pdf-id="${esc(paper.id)}">打开</button><button class="btn secondary" data-pdf-action="delete" data-pdf-id="${esc(paper.id)}">删除</button></span></div>`).join('') : '<div class="empty">还没有导入试卷。</div>'}</div>`;
}
async function upload() {
  const files = [...(document.getElementById('pdf-file')?.files || [])];
  const skill = document.getElementById('pdf-skill')?.value;
  const audio = document.getElementById('pdf-audio')?.files?.[0];
  const message = document.getElementById('pdf-message');
  const button = main.querySelector('[data-pdf-action="upload"]');
  if (!files.length) { message.textContent = '请先选择 PDF 文件。'; return; }
  if (skill === 'listening' && files.length !== 1) { message.textContent = '听力每次只能导入一份 PDF。'; return; }
  if (skill === 'listening' && !audio) { message.textContent = '听力导入必须选择对应音频。'; return; }
  if (skill === 'listening' && audio && ((!audio.type.startsWith('audio/') && !/\.(mp3|m4a|wav|ogg|webm)$/i.test(audio.name)) || audio.size > 100 * 1024 * 1024)) { message.textContent = '请选择不超过 100 MB 的音频文件。'; return; }
  if (files.some(file => file.size > 20 * 1024 * 1024)) { message.textContent = '每份 PDF 不能超过 20 MB。'; return; }
  button.disabled = true;
  message.textContent = '正在从 PDF 提取文字和题目…';
  try {
    const results = [];
    for (const file of files) {
      const response = await fetch('/api/import-pdf', {method:'POST', headers:{'Content-Type':'application/pdf','X-IELTS-Skill':skill,'X-IELTS-Filename':encodeURIComponent(file.name)}, body:file});
      const result = await response.json();
      if (!response.ok) throw new Error(`${file.name}：${result.error || '解析失败'}`);
      results.push(result);
    }
    const groups = [], questions = [], references = [], warnings = [];
    for (const result of results) {
      const offset = groups.length;
      for (const group of result.groups || [{id:1,title:result.title,questions:result.questions.length}]) {
        groups.push({...group, id:offset + group.id, title:results.length > 1 ? `${result.title} · ${group.title}` : group.title});
      }
      for (const question of result.questions) {
        const group = offset + (question.group || 1);
        questions.push({...question, group, id:`${group}-${question.number}`});
      }
      references.push(results.length > 1 ? `[${result.title}]\n${result.referenceText}` : result.referenceText);
      warnings.push(...result.warnings);
    }
    draft = {title:results.length === 1 ? results[0].title : `批量导入（${results.length} 份）`, skill,
      pageCount:results.reduce((sum, result) => sum + result.pageCount, 0), referenceText:references.join('\n\n'),
      questions, groups, warnings:[...new Set(warnings)], audioName:skill === 'listening' ? audio?.name : null,
      id:`pdf-${Date.now()}-${Math.random().toString(36).slice(2,8)}`, answers:{}, submittedAt:null};
    pendingAudio = skill === 'listening' ? audio : null;
    render();
  } catch (error) {
    message.textContent = `导入失败：${error.message}。请确认已用 bank_update.py --serve 启动本地服务。`;
    button.disabled = false;
  }
}
function renderPreview() {
  main.innerHTML = `<div class="page-head"><div><p class="kicker">Review extraction</p><h1>核对提取结果</h1><p class="lede">题号、题干、选项和答案由程序初步识别。请对照原 PDF 修改；没有标准答案的听读题只保存作答，不会自动评分。</p></div></div>
  <div class="notice">${draft.warnings.map(esc).join(' ')}</div>
  <section class="panel pdf-meta"><label>试卷名称<input id="pdf-title" value="${esc(draft.title)}" maxlength="100"></label><span class="small muted">${skillName(draft.skill)} · ${draft.pageCount} 页 · ${draft.groups.length} 组 · 识别 ${draft.questions.length} 题${draft.audioName ? ` · 音频 ${esc(draft.audioName)}` : ''}</span></section>
  <details class="panel pdf-reference-edit"><summary>核对提取的原文（可修改）</summary><p class="small muted">此文字仅存在当前浏览器，练习时可用作阅读材料。图表和图片不会保留。</p><textarea id="pdf-reference">${esc(draft.referenceText)}</textarea></details>
  <div class="section-title"><h2>题目</h2><button class="btn secondary" data-pdf-action="add-question">添加题目</button></div>
  ${draft.groups.map(group => `<section class="pdf-group"><label class="pdf-group-title">组名<input data-pdf-group-title="${group.id}" value="${esc(group.title)}" maxlength="100"></label>${draft.questions.map((question, index) => question.group === group.id ? `<section class="panel pdf-edit-question"><div class="pdf-edit-head"><strong>第 <input type="number" min="1" max="120" data-pdf-field="number" data-pdf-index="${index}" value="${question.number}"> 题 · PDF 第 ${question.page} 页</strong><button class="btn secondary" data-pdf-action="remove-question" data-pdf-index="${index}">移除</button></div><label>题干<textarea data-pdf-field="prompt" data-pdf-index="${index}">${esc(question.prompt)}</textarea></label><div class="pdf-edit-grid"><label>选项（每行一个；填空题留空）<textarea data-pdf-field="options" data-pdf-index="${index}">${esc(question.options.join('\n'))}</textarea></label><label>标准答案（可选）<input data-pdf-field="answer" data-pdf-index="${index}" value="${esc(question.answer)}" placeholder="例如 A、TRUE 或原文单词"></label></div></section>` : '').join('')}</section>`).join('')}
  <div class="toolbar pdf-bottom-actions"><button class="btn" data-pdf-action="save-draft">保存并开始练习</button><button class="btn secondary" data-pdf-action="cancel-draft">取消导入</button></div>`;
}
async function saveDraft() {
  draft.title = document.getElementById('pdf-title')?.value.trim() || '导入的 PDF 试卷';
  draft.referenceText = document.getElementById('pdf-reference')?.value || '';
  const keys = draft.questions.map(q => `${q.group}-${Number(q.number)}`);
  if (!keys.length || draft.questions.some(q => !Number.isInteger(Number(q.number)) || q.number < 1 || q.number > 120 || !q.prompt.trim()) || new Set(keys).size !== keys.length) {
    alert('请至少保留一道题，并检查同一组内题号是否为 1—120 的不重复整数、题干是否为空。');
    return;
  }
  if (draft.skill === 'listening' && !pendingAudio) { alert('听力试卷必须附带音频。'); return; }
  if (papers.length >= 5) { alert('最多保存 5 份试卷。请先删除一份旧试卷。'); return; }
  draft.questions.forEach(q => { q.id = `${q.group}-${q.number}`; });
  draft.questions.sort((a,b) => a.group - b.group || a.number - b.number);
  if (draft.skill === 'listening') {
    try { await audioRecord(draft.id, pendingAudio); }
    catch { alert('音频保存失败，请检查浏览器可用空间。'); return; }
  }
  papers.unshift(draft);
  if (!save()) { papers.shift(); if (draft.skill === 'listening') audioRecord(draft.id, null).catch(() => {}); return; }
  activeId = draft.id;
  draft = null;
  pendingAudio = null;
  render();
}
function renderPractice(paper) {
  const submitted = Boolean(paper.submittedAt);
  const annotate = canScore(paper) && !submitted;
  const annotations = window.IELTS_ANNOTATIONS_INSTANCE;
  const keyed = paper.questions.filter(q => normalize(q.answer));
  const scored = canScore(paper) ? keyed.length : 0;
  const correct = paper.questions.filter(q => questionStatus(paper,q) === 'right').length;
  const shown = wrongOnly && submitted ? paper.questions.filter(q => questionStatus(paper,q) === 'wrong') : paper.questions;
  main.innerHTML = `<div class="page-head"><div><p class="kicker">Imported PDF practice</p><h1>${esc(paper.title)}</h1><p class="lede">${skillName(paper.skill)} · ${paper.pageCount} 页 · ${paper.questions.length} 题。${submitted ? '作答已提交，可逐题查看。' : '作答自动保存在当前浏览器。'}</p></div></div>
  <div class="toolbar"><button class="btn secondary" data-pdf-action="back">← 我的试卷</button>${submitted ? `<button class="btn secondary" data-pdf-action="toggle-wrong">${wrongOnly?'显示全部':'只看错题'}</button><button class="btn secondary" data-pdf-action="restart">重新作答</button>` : `<button class="btn" data-pdf-action="submit">提交作答</button>`}</div>
  ${paper.skill === 'listening' ? `<section class="panel pdf-audio-player"><strong>听力音频 · ${esc(paper.audioName || '已导入音频')}</strong><audio id="pdf-listening-audio" controls preload="metadata"></audio></section>` : ''}
  ${submitted ? `<div class="notice blue">${scored ? `有标准答案的客观题：${correct} / ${scored} 答对。` : '没有可自动评分的标准答案。'} ${paper.questions.length - scored} 题未参与自动评分。写作、口语不使用文字精确匹配评分。</div>` : `<div class="notice">图片和复杂排版请对照原 PDF 检查。${annotate ? '选中或双击原文、题干和选项可做三色高光或笔记；单击标注后选择取消。' : ''}${scored ? `当前有 ${scored} 题填写了标准答案。` : ''}</div>`}
  <div class="pdf-practice-layout"><details class="panel pdf-reference" open><summary>PDF 提取原文</summary><pre>${annotate ? paper.referenceText.split('\n').map((line,index) => annotations.textHtml('pdf',`ref:${index}`,line)).join('\n') : esc(paper.referenceText)}</pre></details><div class="pdf-questions">${shown.length ? shown.map((q,index) => `${index === 0 || shown[index-1].group !== q.group ? `<h2 class="pdf-practice-group">${esc((paper.groups || []).find(g => g.id === q.group)?.title || paper.title)}</h2>` : ''}${questionHtml(paper,q,submitted)}`).join('') : '<div class="empty">没有错题。</div>'}</div></div>${annotate ? annotations.drawerHtml('pdf') : ''}`;
  if (paper.skill === 'listening') attachAudio(paper);
}
function questionHtml(paper, q, submitted) {
  const key = q.id || String(q.number);
  const value = paper.answers?.[key] || '';
  const status = questionStatus(paper,q);
  const options = q.options || [];
  const annotate = canScore(paper) && !submitted;
  const annotations = window.IELTS_ANNOTATIONS_INSTANCE;
  let control;
  if (submitted) {
    control = `<p>你的作答：<strong>${esc(value || '未作答')}</strong></p>${canScore(paper) && q.answer ? `<p>标准答案：<strong>${esc(q.answer)}</strong> · <span class="answer-pill ${status}">${status === 'right' ? '正确' : '需订正'}</span></p>` : '<p class="small muted">无自动评分</p>'}`;
  } else if (options.length) {
    control = `<div class="q-control">${options.map((option,index) => { const choice = option.match(/^\s*([A-D])[.)]/i)?.[1].toUpperCase() || String.fromCharCode(65+index); return `<label><input type="radio" name="pdf-q-${esc(key)}" data-pdf-answer="${esc(key)}" value="${choice}" ${value===choice?'checked':''}>${annotate ? annotations.textHtml('pdf',`q:${key}:opt:${choice}`,option) : esc(option)}</label>`; }).join('')}</div>`;
  } else if (paper.skill === 'writing' || paper.skill === 'speaking') {
    control = `<textarea class="draft" data-pdf-answer="${esc(key)}" placeholder="在这里输入你的作答">${esc(value)}</textarea>`;
  } else {
    control = `<input class="pdf-answer-input" data-pdf-answer="${esc(key)}" value="${esc(value)}" autocomplete="off" placeholder="输入答案">`;
  }
  return `<article class="review-card ${submitted && status==='wrong'?'wrong':''}"><h3>${q.number}. ${annotate ? annotations.textHtml('pdf',`q:${key}`,q.prompt) : esc(q.prompt)}</h3><p class="small muted">PDF 第 ${q.page} 页</p>${control}</article>`;
}

main.addEventListener('click', event => {
  const button = event.target.closest('[data-pdf-action]');
  if (!button) return;
  const action = button.dataset.pdfAction;
  if (action === 'upload') upload();
  if (action === 'open') { activeId = button.dataset.pdfId; wrongOnly = false; render(); }
  if (action === 'delete' && confirm('删除这份浏览器中的 PDF 练习及作答记录？')) {
    const paper = papers.find(p => p.id === button.dataset.pdfId);
    const previous = papers;
    papers = papers.filter(p => p.id !== button.dataset.pdfId);
    if (save()) { if (paper?.skill === 'listening') audioRecord(paper.id, null).catch(() => {}); }
    else papers = previous;
    render();
  }
  if (action === 'back') { activeId = null; wrongOnly = false; render(); }
  if (action === 'cancel-draft') { draft = null; pendingAudio = null; render(); }
  if (action === 'add-question' && draft) { const group = draft.groups.at(-1)?.id || 1; if (!draft.groups.length) draft.groups.push({id:group,title:'手动添加',questions:0}); draft.questions.push({number:Math.max(0,...draft.questions.filter(q => q.group === group).map(q => Number(q.number)||0))+1,group,page:1,prompt:'',options:[],answer:''}); render(); }
  if (action === 'remove-question' && draft) { draft.questions.splice(Number(button.dataset.pdfIndex),1); render(); }
  if (action === 'save-draft' && draft) saveDraft();
  if (action === 'submit') { const paper = activePaper(); if (paper && confirm('提交这份 PDF 练习？')) { paper.submittedAt = Date.now(); rememberSubmission(paper); save(); render(); } }
  if (action === 'toggle-wrong') { wrongOnly = !wrongOnly; render(); }
  if (action === 'restart' && confirm('重新作答？已提交的答案和笔记会保留在练习记录中。')) { redoHistory(activeId); render(); }
});
main.addEventListener('input', event => {
  const el = event.target;
  if (draft && el.id === 'pdf-title') draft.title = el.value;
  if (draft && el.id === 'pdf-reference') draft.referenceText = el.value;
  if (draft && el.dataset.pdfGroupTitle) {
    const group = draft.groups.find(g => g.id === Number(el.dataset.pdfGroupTitle));
    if (group) group.title = el.value;
  }
  if (draft && el.dataset.pdfField) {
    const question = draft.questions[Number(el.dataset.pdfIndex)];
    question[el.dataset.pdfField] = el.dataset.pdfField === 'number' ? Number(el.value) : el.dataset.pdfField === 'options' ? el.value.split('\n').map(x => x.trim()).filter(Boolean) : el.value;
  }
  if (!draft || el.dataset.pdfAnswer) {
    const paper = activePaper();
    if (paper && !paper.submittedAt && el.dataset.pdfAnswer) { paper.answers[el.dataset.pdfAnswer] = el.value; scheduleSave(); }
  }
});
main.addEventListener('change', event => {
  const el = event.target;
  if (el.id === 'pdf-skill') {
    const listening = el.value === 'listening';
    document.getElementById('pdf-audio-label').hidden = !listening;
    document.getElementById('pdf-file').multiple = !listening;
    document.getElementById('pdf-file').value = '';
    document.getElementById('pdf-message').textContent = listening ? '听力请选择一份 PDF 和对应音频。' : '可选择多份 PDF 一次导入。';
  }
  if (el.type === 'radio' && el.dataset.pdfAnswer) {
    const paper = activePaper();
    if (paper && !paper.submittedAt) { paper.answers[el.dataset.pdfAnswer] = el.value; save(); }
  }
});

window.IELTS_PDF_IMPORT = {render, getActivePaper:activePaper, persist:save, historyEntries, redoHistory};
})();
