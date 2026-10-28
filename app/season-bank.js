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
const historyStorageKey = 'ielts-season-history-v1';
let mode = 'library';
let subjectPart = 'all';
const subjectParts = {reading:['Passage 1','Passage 2','Passage 3','篇次未核实'],listening:['Part 1','Part 2','Part 3'],writing:['Task 1','Task 2'],speaking:['Part 1','Part 2','Part 3']};
function matchesPart(item, part) {
  if (part === 'all') return true;
  const value = item.section || item.part || item.task || '';
  if (part === '篇次未核实') return !value;
  return value === part || (value === 'Part 2 / Part 3' && (part === 'Part 2' || part === 'Part 3'));
}

function storageKey() { return `ielts-season-practice-${index.season.id}-v1`; }
function load() {
  try { saved = JSON.parse(localStorage.getItem(storageKey()) || '{}') || {}; }
  catch { saved = {}; }
}
function persist() {
  try { localStorage.setItem(storageKey(),JSON.stringify(saved)); }
  catch { status('浏览器存储空间不足，作答可能没有保存。'); }
}
function recordAttempt(item) {
  const at=Date.now();
  const answers=structuredClone(saved[item.id]?.answers||{});
  const questions=item.questions||[];
  const score=questions.filter(q=>isCorrect(q,answers[q.id]||'')).length;
  const entry={id:`season-${item.id}-${at}`,type:'season',skill,mode:'single',title:item.title,at,
    seasonId:index.season.id,item:structuredClone(item),answers,draft:saved[item.id]?.draft||'',
    score:questions.length?score:null,total:questions.length||null};
  try {const history=JSON.parse(localStorage.getItem(historyStorageKey)||'[]');history.unshift(entry);localStorage.setItem(historyStorageKey,JSON.stringify(history));status('已保存本次作答到练习记录。');}
  catch {status('无法保存练习记录，请检查浏览器存储空间。');}
}
function historyEntries(){try{return JSON.parse(localStorage.getItem(historyStorageKey)||'[]');}catch{return [];}}
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
    <span class="season-card-top"><span class="badge blue">${escapeHtml(item.task || item.part || '来源题')}</span><small>${escapeHtml(sourceLabel(item))}</small></span>
    <strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.basis || '当季来源题目')}</span>
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
    <button type="button" class="btn secondary" data-season-save-writing>保存本次写作到记录</button>
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
  return `<section class="panel season-detail"><div class="season-detail-head"><div><span class="badge blue">${escapeHtml(item.task || item.part || '当季来源题')}</span><h2>${escapeHtml(item.title)}</h2></div><button type="button" class="btn secondary" data-season-close>返回题库</button></div>
    <p class="small muted">${escapeHtml(item.basis || '当季来源题目')}。${link?`<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">核对题目来源 ↗</a>`:''}</p>${body}</section>`;
}
function reportRow(item) {
  const label = item.date ? `${item.kind==='third_party_dated_topic'?'来源标注考试':'来源发布'} ${item.date}` : `来源月份 ${item.month}`;
  const title = item.title || '未命名资料';
  const type = item.section || item.task || item.part || (skill==='reading'?'Passage 未核实':'Part / Section 未核实');
  const appearance = item.reportedAppearances?.[0];
  const where = appearance ? `来源标注出现于 ${appearance.date}${appearance.venue?` · ${appearance.venue}`:''}（未独立核验）`
    : item.reportedPeriod ? `来源标注考试周 ${item.reportedPeriod}；具体场次和考点未核实`
    : item.geography==='site_reported_mainland' ? '来源列为中国大陆话题；具体场次和考点未核实' : '具体出现场次和考点未核实';
  const descriptor = item.kind==='reported_topic'?'话题线索 · ':'';
  const source = item.sourceTitle ? `<small>出处：${escapeHtml(item.sourceTitle)}</small>` : '';
  const body=`<span><strong>${escapeHtml(descriptor+title)}</strong><small>${escapeHtml(label)} · ${escapeHtml(type)} · ${escapeHtml(where)}</small>${source}</span>`;
  if(mode==='subject'&&skill==='speaking')return `<div class="link-row season-report-row">${body}<span class="source-row-actions"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">来源 ↗</a><button type="button" class="btn secondary" data-season-open-speaking="${escapeHtml(item.id)}">录音练习</button></span></div>`;
  return `<div class="link-row season-report-row">${body}<span class="source-row-actions"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">核对来源 ↗</a></span></div>`;
}
function render(main, sourceIndex, nextCapabilities = {}) {
  root = main;
  capabilities = nextCapabilities;
  const changed = index?.season.id !== sourceIndex.season.id;
  index = sourceIndex;
  if (changed) { selected = null; showAnswers = false; wrongOnly = false; load(); }
  const items = authoredItems().filter(item=>mode==='library'||matchesPart(item,subjectPart));
  const chosen = items.find(item=>item.id===selected);
  const reports = (index[skill] || []).filter(item=>mode==='library'||matchesPart(item,subjectPart));
  const current = content.seasonId === index.season.id;
  if (mode === 'subject') {
    const title=skills.find(entry=>entry.id===skill).name;
    const readingBreakdown = skill==='reading' && subjectPart==='all'
      ? `<div class="notice blue">本期共有 ${index.reading.length} 条阅读话题出现记录：${subjectParts.reading.map(part=>`${part} ${index.reading.filter(item=>matchesPart(item,part)).length} 条`).join('、')}。它们来自不同文章和考试周，不能据此认定是同一套试卷。</div>` : '';
    root.innerHTML=`<div class="page-head"><div><p class="kicker">Current season · ${escapeHtml(title)}</p><h1>${escapeHtml(title)}${subjectPart==='all'?'整套模考':` · ${escapeHtml(subjectPart)}`}</h1><p class="lede">${escapeHtml(index.season.label)}。先选整套或单个部分，再查看有完整题目及来源证据的题组。</p></div></div>
      <div class="season-skill-tabs subject-part-tabs" role="tablist" aria-label="${escapeHtml(title)}部分选择"><button type="button" role="tab" aria-selected="${subjectPart==='all'}" class="${subjectPart==='all'?'active':''}" data-subject-part="all">整套模考</button>${subjectParts[skill].map(part=>`<button type="button" role="tab" aria-selected="${subjectPart===part}" class="${subjectPart===part?'active':''}" data-subject-part="${escapeHtml(part)}">${escapeHtml(part)}${skill==='reading'?` · ${(index.reading||[]).filter(item=>matchesPart(item,part)).length}`:''}</button>`).join('')}</div>
      ${readingBreakdown}
      ${chosen?detail(chosen):`<div class="section-title"><h2>${subjectPart==='all'?'当季完整模考':'可作答的当季题目'}</h2></div>${subjectPart==='all'?'<div class="empty">当前尚未收齐有来源和公开分发权的完整试卷，无法组成真实当季整套模考。</div>':items.length?`<div class="season-practice-grid">${items.map(practiceCard).join('')}</div>`:'<div class="empty">这个部分暂无可公开分发的完整题目，暂不能开始作答。</div>'}
      <div class="section-title"><h2>公开出现记录与来源 · ${reports.length}</h2></div><p class="small muted">链接标题可能只是话题摘要；没有完整原题、答案或音频的记录不会自动变成模考。${skill==='reading'?'按来源标注的 Passage 分组；未标明篇次的线索可在“篇次未核实”查看。':'标注了 Part / Task 的线索可按来源分组查看，其余请到“公开题库”查看。'}</p><div class="link-list">${reports.map(reportRow).join('')||'<div class="empty">本部分暂无已核实分组的公开记录。</div>'}</div>${skill!=='reading'&&subjectPart!=='all'&&(index[skill]||[]).some(item=>!item.section&&!item.part&&!item.task)?'<p class="small muted">还有未标明 Part / Section 的记录，可在“公开题库”查看。</p>':''}`}
      <div id="season-status" role="status" aria-live="polite"></div>`;
    return;
  }
  root.innerHTML = `<div class="page-head"><div><p class="kicker">Current season · Four skills</p><h1>${escapeHtml(index.season.label)}当季题库</h1><p class="lede">查看本期听、说、读、写的公开记录及来源；具体日期、考点只在来源有报告时标注。</p></div><span class="badge blue">核对 ${escapeHtml(index.checkedAt)}</span></div>
    <div class="notice blue">${current?escapeHtml(content.notice):'新资料期已开始，原期资料已退出当前练习区。本期公开记录在下方持续更新。'} 来源目录只证明第三方有相关报告，不证明覆盖全国考点。</div>
    <div class="season-skill-tabs" role="tablist" aria-label="当季四科题库">${skills.map(entry=>`<button type="button" role="tab" aria-selected="${skill===entry.id}" class="${skill===entry.id?'active':''}" data-season-tab="${entry.id}"><span>${entry.icon}</span>${entry.name}<small>${(index[entry.id]||[]).length} 条线索</small></button>`).join('')}</div>
    <div id="season-status" role="status" aria-live="polite"></div>
    ${chosen?detail(chosen):`<div class="section-title"><h2>可分发的完整题目 · ${items.length} 题组</h2><span class="small muted">仅收录有授权和出现证据的来源题</span></div>
    ${items.length?`<div class="season-practice-grid">${items.map(practiceCard).join('')}</div>`:'<div class="empty">本期暂无获授权、可随仓库分发的完整题目；下方仅是来源记录，不是站内模考题。</div>'}
    <details class="season-reports" open><summary>本期${skills.find(entry=>entry.id===skill).name}公开线索 · ${reports.length} 条</summary><p class="small muted">逐条收录来源明确提到的话题、日期或考试周；未核实的场次和考点会标明。完整试题请回源站核对。</p><input id="season-search" type="search" placeholder="筛选标题或日期" aria-label="筛选当季题库"><div class="link-list">${reports.map(reportRow).join('')}</div></details>`}`;
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
  const part = event.target.closest('[data-subject-part]');
  if (part) { stopAudio(); subjectPart=part.dataset.subjectPart; window.dispatchEvent(new CustomEvent('ielts:subject-part',{detail:{skill,part:subjectPart}})); selected=null; showAnswers=false; wrongOnly=false; render(root,index,capabilities); return; }
  const tab = event.target.closest('[data-season-tab]');
  if (tab) { stopAudio(); skill=tab.dataset.seasonTab; selected=null; showAnswers=false; wrongOnly=false; if(root)render(root,index,capabilities); return; }
  const card = event.target.closest('[data-season-item]');
  if (card) { stopAudio(); selected=card.dataset.seasonItem; showAnswers=false; wrongOnly=false; if(root)render(root,index,capabilities); root?.scrollIntoView({block:'start'}); return; }
  if (event.target.closest('[data-season-close]')) { selected=null; showAnswers=false; wrongOnly=false; stopAudio(); if(root)render(root,index,capabilities); return; }
  if (event.target.closest('[data-season-check]')) { const item=selectedItem();if(item)recordAttempt(item);showAnswers=true; if(root)render(root,index,capabilities); return; }
  if (event.target.closest('[data-season-save-writing]')) {const item=selectedItem();if(item?.prompt&&saved[item.id]?.draft?.trim())recordAttempt(item);else status('请先写下作文再保存。');return;}
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
window.IELTS_SEASON_BANK = {renderLibrary:(main,sourceIndex,nextCapabilities)=>{mode='library';return render(main,sourceIndex,nextCapabilities);},renderSubject:(main,sourceIndex,nextCapabilities,nextSkill,nextPart)=>{if(skill!==nextSkill)selected=null;mode='subject';skill=nextSkill;subjectPart=nextPart||'all';return render(main,sourceIndex,nextCapabilities);},historyEntries,replaceContent:next=>{
  if (!next?.seasonId || JSON.stringify(next)===JSON.stringify(content)) return false;
  content=next;
  window.IELTS_SEASON_CONTENT=next;
  return true;
},deactivate:()=>{root=null;stopAudio();}};
})();
