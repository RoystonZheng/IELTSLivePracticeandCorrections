(() => {
'use strict';

let content = window.IELTS_SEASON_CONTENT;
const skills = [
  {id:'reading',name:'阅读',icon:'▣'},
  {id:'listening',name:'听力',icon:'♫'},
  {id:'writing',name:'写作',icon:'✎'},
  {id:'speaking',name:'口语',icon:'◉'}
];
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const normal = value => String(value ?? '').trim().replace(/\s+/g,' ').toLowerCase();
const isCorrect = (question, answer) => [question.answer,...(question.accepted || [])].some(value => normal(answer) === normal(value));
const wordCount = value => (String(value ?? '').match(/\b[\w'-]+\b/g) || []).length;
let index;
let root;
let skill = 'reading';
let selected = null;
let showAnswers = false;
let wrongOnly = false;
let saved = {};
let capabilities = {};
let activeAudio = null;

function storageKey() { return `ielts-season-practice-${index.season.id}-v1`; }
function load() {
  try { saved = JSON.parse(localStorage.getItem(storageKey()) || '{}') || {}; }
  catch { saved = {}; }
}
function persist() {
  try { localStorage.setItem(storageKey(),JSON.stringify(saved)); }
  catch { status('浏览器存储空间不足，作答可能没有保存。'); }
}
function status(message) {
  const slot = document.getElementById('season-status');
  if (slot) slot.textContent = message;
}
function authoredItems() { return content.seasonId === index.season.id ? content[skill] || [] : []; }
function sourceItem(item) {
  const sources = index[skill] || [];
  if (item.sourceTitle) return sources.find(source => source.url === item.sourceUrl && source.title === item.sourceTitle);
  return sources.find(source => source.id === item.sourceId);
}
function sourceLabel(item) {
  const source = sourceItem(item);
  return source?.date || item.month || index.season.start.slice(0,7);
}
function practiceCard(item) {
  return `<button type="button" class="season-practice-card" data-season-item="${escapeHtml(item.id)}">
    <span class="season-card-top"><span class="badge blue">${escapeHtml(item.task || item.part || '独立编写')}</span><small>${escapeHtml(sourceLabel(item))}</small></span>
    <strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.basis || '依据当季公开话题独立编写')}</span>
    <small>在本站阅读题目并练习 →</small>
  </button>`;
}
function questionControl(item, question) {
  const answer = saved[item.id]?.answers?.[question.id] || '';
  if (question.type === 'tfng' || question.type === 'mcq') {
    const options = question.type === 'tfng' ? ['TRUE','FALSE','NOT GIVEN'] : question.options;
    return `<div class="season-options">${options.map(option => {
      const value = question.type === 'mcq' ? option.slice(0,1) : option;
      return `<label><input type="radio" name="season-${escapeHtml(item.id)}-${escapeHtml(question.id)}" data-season-answer="${escapeHtml(question.id)}" value="${escapeHtml(value)}" ${answer===value?'checked':''}>${escapeHtml(option)}</label>`;
    }).join('')}</div>`;
  }
  return `<input class="season-answer" type="text" data-season-answer="${escapeHtml(question.id)}" value="${escapeHtml(answer)}" aria-label="第 ${escapeHtml(question.id)} 题答案" autocomplete="off">`;
}
function questionList(item) {
  const isWrong = question => !isCorrect(question,saved[item.id]?.answers?.[question.id]);
  const shown = showAnswers && wrongOnly ? item.questions.filter(isWrong) : item.questions;
  return `<div class="season-questions">${shown.map(question => {
    const answer = saved[item.id]?.answers?.[question.id] || '';
    const correct = isCorrect(question,answer);
    const feedback = saved[item.id]?.feedback?.[question.id];
    return `<div class="season-question ${showAnswers?(correct?'right':'wrong'):''}"><strong>${escapeHtml(question.id)}. ${escapeHtml(question.prompt)}</strong>${questionControl(item,question)}${showAnswers?`<p>你的答案：${escapeHtml(answer || '未作答')} · 正确答案：<b>${escapeHtml(question.answer)}</b></p><p>${escapeHtml(question.explanation)}</p>${!correct&&capabilities.codexCli?`<button type="button" class="btn secondary" data-season-ai-question="${escapeHtml(question.id)}">用 Codex 解释这道错题</button>`:''}${feedback?feedbackView(feedback):''}`:''}</div>`;
  }).join('')}${shown.length?'':'<p class="empty">没有错题。</p>'}</div><div class="toolbar"><button type="button" class="btn" data-season-check>核对答案</button>${showAnswers?`<button type="button" class="btn secondary" data-season-wrong-only>${wrongOnly?'显示全部':'只看错题'}</button><span class="small muted">本次正确 ${item.questions.filter(q=>!isWrong(q)).length} / ${item.questions.length}</span>`:''}</div>`;
}
function readingDetail(item) {
  return `<div class="season-reading-text">${item.paragraphs.map((paragraph,i)=>`<p><b>${String.fromCharCode(65+i)}</b> ${escapeHtml(paragraph)}</p>`).join('')}</div>${questionList(item)}`;
}
function listeningDetail(item) {
  return `<div class="notice blue">原创合成音频练习。整段和逐句音频随仓库提供；核对答案后可查看文字稿。</div>
  <div class="toolbar"><button type="button" class="btn" data-season-play-all>▶ 播放整段</button><button type="button" class="btn secondary" data-season-stop>停止</button></div>
  ${questionList(item)}${showAnswers?`<details class="season-transcript" open><summary>文字稿与逐句朗读</summary>${item.sentences.map((sentence,i)=>`<button type="button" data-season-play-sentence="${i}">${i+1}. ${escapeHtml(sentence)}</button>`).join('')}</details>`:''}`;
}
function dataTable(table) {
  if (!table) return '';
  return `<div class="season-table-scroll"><table><thead><tr>${table.columns.map(column=>`<th>${escapeHtml(column)}</th>`).join('')}</tr></thead><tbody>${table.rows.map(row=>`<tr>${row.map(value=>`<td>${escapeHtml(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="small muted">表格数据由本项目虚构，不是考场图表。</p>`;
}
function writingDetail(item) {
  const draft = saved[item.id]?.draft || '';
  return `<p class="season-prompt">${escapeHtml(item.prompt)}</p>${dataTable(item.table)}
    <label class="season-writing-label" for="season-draft">你的作文 · 建议至少 ${item.minimumWords} 词</label>
    <textarea id="season-draft" class="draft" data-season-draft placeholder="Write your answer here...">${escapeHtml(draft)}</textarea>
    <p class="small muted">已写 <span id="season-word-count">${wordCount(draft)}</span> 词 · 自动保存在当前浏览器。${capabilities.codexCli?'可用自己的 Codex CLI 获取练习估分。':'未连接 Codex CLI 时可正常写作，不提供估分。'}</p>
    ${capabilities.codexCli?'<button type="button" class="btn" data-season-ai-writing>获取 AI 练习评分</button>':''}${saved[item.id]?.writingFeedback?feedbackView(saved[item.id].writingFeedback):''}`;
}
function feedbackView(feedback) {
  return `<div class="season-ai-feedback"><strong>Codex CLI 练习反馈${feedback.estimatedBand==null?'':` · 约 ${escapeHtml(feedback.estimatedBand)} 分`}</strong><p>${escapeHtml(feedback.summary)}</p>${(feedback.criteria||[]).map(entry=>`<p><b>${escapeHtml(entry.name)}${entry.estimate==null?'':` ${escapeHtml(entry.estimate)}`}</b>：${escapeHtml(entry.feedback)}</p>`).join('')}<p><b>修改建议：</b>${escapeHtml(feedback.correction)}</p><p><b>下一步：</b>${escapeHtml(feedback.nextStep)}</p><p class="small muted">${escapeHtml(feedback.limitations)}</p></div>`;
}
function speakingDetail(item) {
  return `<div class="season-speaking-questions">${item.questions.map((question,i)=>`<p><b>${i+1}.</b> ${escapeHtml(question)}</p>`).join('')}</div>
    <p class="small muted">这些问法由本项目独立编写。录音、回放和可选 Codex CLI 反馈请进入相应话题练习。</p>
    ${sourceItem(item)?`<button type="button" class="btn" data-season-open-speaking="${escapeHtml(sourceItem(item).id)}">打开录音练习 →</button>`:'<p class="small muted">本期目录暂未收录对应口语话题。</p>'}`;
}
function detail(item) {
  const source = sourceItem(item);
  const link = source?.url || item.sourceUrl;
  const body = skill==='reading'?readingDetail(item):skill==='listening'?listeningDetail(item):skill==='writing'?writingDetail(item):speakingDetail(item);
  return `<section class="panel season-detail"><div class="season-detail-head"><div><span class="badge blue">${escapeHtml(item.task || item.part || '当季主题练习')}</span><h2>${escapeHtml(item.title)}</h2></div><button type="button" class="btn secondary" data-season-close>返回题库</button></div>
    <p class="small muted">${escapeHtml(item.basis || '依据当季公开话题独立编写')} · 非考场原题、非原站试卷。${link?`<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">核对话题来源 ↗</a>`:''}</p>${body}</section>`;
}
function reportRow(item) {
  const label = item.date || item.month;
  const title = item.title || '未命名资料';
  const type = item.task || item.part || (skill==='reading'?'阅读重建入口':'听力重建入口');
  const region = item.venueReported?`第三方标注考点：${item.venueReported}`:({global_unattributed:'未核验国内考点',site_reported_mainland:'第三方大陆话题目录'}[item.geography]||'地域需回源站核对');
  return `<a class="link-row season-report-row" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer"><span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(label)} · ${escapeHtml(type)} · ${escapeHtml(region)}</small></span><span class="arrow">↗</span></a>`;
}
function render(main, sourceIndex, nextCapabilities = {}) {
  root = main;
  capabilities = nextCapabilities;
  const changed = index?.season.id !== sourceIndex.season.id;
  index = sourceIndex;
  if (changed) { selected = null; showAnswers = false; wrongOnly = false; load(); }
  const items = authoredItems();
  const chosen = items.find(item=>item.id===selected);
  const reports = index[skill] || [];
  const current = content.seasonId === index.season.id;
  root.innerHTML = `<div class="page-head"><div><p class="kicker">Current season · Four skills</p><h1>${escapeHtml(index.season.label)}当季题库</h1><p class="lede">先看本期能在站内打开的题目，再查完整公开线索目录。听、说、读、写均随仓库提供；新季开始时旧季练习不会冒充本期题。</p></div><span class="badge blue">核对 ${escapeHtml(index.checkedAt)}</span></div>
    <div class="notice blue">${current?escapeHtml(content.notice):'新资料期已开始，原期资料已退出当前练习区。本期公开线索在下方持续更新；独立编写的站内题目待核对后上架。'} 来源目录只证明第三方有相关报告，不证明覆盖全国考点。</div>
    <div class="season-skill-tabs" role="tablist" aria-label="当季四科题库">${skills.map(entry=>`<button type="button" role="tab" aria-selected="${skill===entry.id}" class="${skill===entry.id?'active':''}" data-season-tab="${entry.id}"><span>${entry.icon}</span>${entry.name}<small>${(index[entry.id]||[]).length} 条线索</small></button>`).join('')}</div>
    <div id="season-status" role="status" aria-live="polite"></div>
    ${chosen?detail(chosen):`<div class="section-title"><h2>站内可练习 · ${items.length} 题组</h2><span class="small muted">独立编写 · 随仓库下载</span></div>
    ${items.length?`<div class="season-practice-grid">${items.map(practiceCard).join('')}</div>`:'<div class="empty">本期暂无经核对的站内练习题组；下面仍可查看本期资料线索。</div>'}
    <details class="season-reports" open><summary>本期${skills.find(entry=>entry.id===skill).name}公开线索 · ${reports.length} 条</summary><p class="small muted">这里收录标题、日期与来源；部分来源仅有主题，完整第三方试卷需到原站查看。</p><input id="season-search" type="search" placeholder="筛选标题或日期" aria-label="筛选当季题库"><div class="link-list">${reports.map(reportRow).join('')}</div></details>`}`;
}
function selectedItem() { return authoredItems().find(item=>item.id===selected); }
function stopAudio() {
  if (activeAudio) { activeAudio.pause(); activeAudio.currentTime=0; activeAudio=null; }
  window.speechSynthesis?.cancel();
}
function speak(text) {
  if (!window.speechSynthesis) { status('当前浏览器没有可用的语音朗读功能。'); return; }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-GB';
  utterance.rate = .88;
  window.speechSynthesis.speak(utterance);
}
function playAudio(path, fallbackText) {
  stopAudio();
  if (!path) { speak(fallbackText); return; }
  activeAudio = new Audio(path);
  activeAudio.play().catch(() => {
    activeAudio=null;
    speak(fallbackText);
  });
}
async function requestFeedback(button, item, questionId) {
  const requestedSeason = index.season.id;
  const isWriting = skill === 'writing';
  const answer = isWriting ? saved[item.id]?.draft || '' : saved[item.id]?.answers?.[questionId] || '';
  const payload = {kind:isWriting?'season-writing':`season-${skill}`,itemId:item.id,answer};
  if (!isWriting) payload.questionId=questionId;
  button.disabled=true;
  button.textContent='生成中…';
  try {
    const response=await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result=await response.json();
    if (!response.ok) throw new Error(result.error||'请求失败');
    if (index.season.id !== requestedSeason) return;
    const currentAnswer = isWriting ? saved[item.id]?.draft || '' : saved[item.id]?.answers?.[questionId] || '';
    if (currentAnswer !== answer) {
      button.disabled=false;
      button.textContent=isWriting?'获取 AI 练习评分':'用 Codex 解释这道错题';
      return;
    }
    if (isWriting) (saved[item.id] ||= {}).writingFeedback=result.feedback;
    else (((saved[item.id] ||= {}).feedback ||= {}))[questionId]=result.feedback;
    persist();
    if (root && selected===item.id) render(root,index,capabilities);
  } catch(error) {
    status(`反馈未生成：${error.message}`);
    button.disabled=false;
    button.textContent=isWriting?'获取 AI 练习评分':'用 Codex 解释这道错题';
  }
}
document.addEventListener('click', event => {
  if (!root?.contains(event.target)) return;
  const tab = event.target.closest('[data-season-tab]');
  if (tab) { stopAudio(); skill=tab.dataset.seasonTab; selected=null; showAnswers=false; wrongOnly=false; if(root)render(root,index,capabilities); return; }
  const card = event.target.closest('[data-season-item]');
  if (card) { stopAudio(); selected=card.dataset.seasonItem; showAnswers=false; wrongOnly=false; if(root)render(root,index,capabilities); root?.scrollIntoView({block:'start'}); return; }
  if (event.target.closest('[data-season-close]')) { selected=null; showAnswers=false; wrongOnly=false; stopAudio(); if(root)render(root,index,capabilities); return; }
  if (event.target.closest('[data-season-check]')) { showAnswers=true; if(root)render(root,index,capabilities); return; }
  if (event.target.closest('[data-season-wrong-only]')) { wrongOnly=!wrongOnly; if(root)render(root,index,capabilities); return; }
  const aiQuestion=event.target.closest('[data-season-ai-question]');
  if (aiQuestion) { const item=selectedItem(); if(item)requestFeedback(aiQuestion,item,aiQuestion.dataset.seasonAiQuestion); return; }
  const aiWriting=event.target.closest('[data-season-ai-writing]');
  if (aiWriting) { const item=selectedItem(); if(item)requestFeedback(aiWriting,item); return; }
  if (event.target.closest('[data-season-play-all]')) { const item=selectedItem(); if(item) playAudio(item.audio,item.sentences.join(' ')); return; }
  if (event.target.closest('[data-season-stop]')) { stopAudio(); return; }
  const sentence=event.target.closest('[data-season-play-sentence]');
  if (sentence) { const item=selectedItem(),position=Number(sentence.dataset.seasonPlaySentence); if(item) playAudio(item.sentenceAudio?.[position],item.sentences[position]); return; }
  const speaking=event.target.closest('[data-season-open-speaking]');
  if (speaking) window.dispatchEvent(new CustomEvent('ielts:open-speaking',{detail:speaking.dataset.seasonOpenSpeaking}));
});
document.addEventListener('input', event => {
  if (!root?.contains(event.target)) return;
  const item=selectedItem();
  if (event.target.id==='season-search') {
    const query=normal(event.target.value);
    root.querySelectorAll('.season-report-row').forEach(row=>{row.hidden=!normal(row.textContent).includes(query);});
    return;
  }
  if (!item) return;
  if (event.target.matches('[data-season-draft]')) {
    (saved[item.id] ||= {}).draft=event.target.value;
    delete saved[item.id].writingFeedback;
    persist();
    const count=document.getElementById('season-word-count');
    if(count)count.textContent=wordCount(event.target.value);
  }
  if (event.target.matches('[data-season-answer]') && event.target.type==='text') {
    ((saved[item.id] ||= {}).answers ||= {})[event.target.dataset.seasonAnswer]=event.target.value;
    if (saved[item.id].feedback) delete saved[item.id].feedback[event.target.dataset.seasonAnswer];
    persist();
  }
});
document.addEventListener('change', event => {
  if (!root?.contains(event.target) || !event.target.matches('[data-season-answer]') || event.target.type!=='radio') return;
  const item=selectedItem();
  if (!item) return;
  ((saved[item.id] ||= {}).answers ||= {})[event.target.dataset.seasonAnswer]=event.target.value;
  if (saved[item.id].feedback) delete saved[item.id].feedback[event.target.dataset.seasonAnswer];
  persist();
});
window.IELTS_SEASON_BANK = {render,replaceContent:next=>{
  if (!next?.seasonId || JSON.stringify(next)===JSON.stringify(content)) return false;
  content=next;
  window.IELTS_SEASON_CONTENT=next;
  return true;
},deactivate:()=>{root=null;stopAudio();}};
})();
