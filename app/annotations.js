(() => {
'use strict';

const COLORS = ['yellow', 'green', 'pink'];
const COLOR_NAMES = {yellow:'黄色', green:'绿色', pink:'粉色'};
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

function validRecords(records, length) {
  return (Array.isArray(records) ? records : []).filter(item => item &&
    Number.isInteger(item.start) && Number.isInteger(item.end) &&
    item.start >= 0 && item.end <= length && item.start < item.end &&
    (item.type === 'note' || (item.type === 'highlight' && COLORS.includes(item.color))));
}

function renderMarkedText(source, records) {
  const text = String(source ?? '');
  const safe = validRecords(records, text.length);
  const edges = [...new Set([0, text.length, ...safe.flatMap(item => [item.start, item.end])])].sort((a, b) => a - b);
  let html = '';
  for (let index = 0; index < edges.length - 1; index++) {
    const start = edges[index], end = edges[index + 1];
    const part = escapeHtml(text.slice(start, end));
    const active = safe.filter(item => item.start <= start && item.end >= end);
    const highlight = active.filter(item => item.type === 'highlight').at(-1);
    const note = active.filter(item => item.type === 'note').at(-1);
    if (!highlight && !note) { html += part; continue; }
    const classes = ['annot-mark'];
    if (highlight) classes.push('annot-highlight', `annot-${highlight.color}`);
    if (note) classes.push('annot-note-mark');
    html += `<span class="${classes.join(' ')}"${highlight ? ` data-annot-highlight="${escapeHtml(highlight.id)}"` : ''}${note ? ` data-annot-note="${escapeHtml(note.id)}"` : ''} title="${note ? `笔记：${escapeHtml(note.text)}；单击查看操作` : `${COLOR_NAMES[highlight.color]}高光；单击查看操作`}">${part}</span>`;
  }
  return html;
}

function create({getAttempt, persist, toast}) {
  let chosenColor = 'yellow';
  let selected = null;
  let editorTarget = null;
  let toolbar;
  let editor;
  let markMenu;
  let markTarget = null;
  let drawerOpenKind = null;

  function entries(kind, key, sourceLength) {
    const attempt = getAttempt(kind);
    return validRecords(attempt?.annotations?.[key], sourceLength);
  }

  function textHtml(kind, key, source) {
    const text = String(source ?? '');
    return `<span class="annot-text" data-annot-kind="${escapeHtml(kind)}" data-annot-key="${escapeHtml(key)}" data-annot-source="${escapeHtml(text)}">${renderMarkedText(text, entries(kind, key, text.length))}</span>`;
  }

  function allNotes(kind) {
    const attempt = getAttempt(kind);
    const inline = Object.entries(attempt?.annotations || {}).flatMap(([key, records]) =>
      (Array.isArray(records) ? records : []).filter(item => item?.type === 'note' && item.text).map(item => ({key, ...item})));
    const passages = kind === 'reading' ? Object.entries(attempt?.notes || {}).filter(([,value]) => String(value).trim()) : [];
    return {inline, passages, count:inline.length + passages.length};
  }

  function locationLabel(kind, key) {
    const parts = key.split(':');
    if (parts[0] === 'p') return `Passage ${parts[1].replace(/\D/g,'')} · 段落 ${parts[2] || ''}`;
    if (parts[0] === 'q') return `第 ${parts[1]} 题${parts[2] === 'opt' ? ` · 选项 ${parts[3]}` : ''}`;
    if (parts[0] === 'ref') return `原文第 ${Number(parts[1]) + 1} 行`;
    return key;
  }

  function noteListHtml(kind) {
    const {inline, passages, count} = allNotes(kind);
    if (!count) return '<p class="annot-empty">还没有笔记。选中原文或题干，点击“笔记”即可记录。</p>';
    return `${passages.map(([id, value]) => `<article class="annot-note-item"><small>Passage ${escapeHtml(id.replace(/\D/g,''))} · 整篇笔记</small><p>${escapeHtml(value)}</p></article>`).join('')}${inline.map(item => `<article class="annot-note-item"><small>${escapeHtml(locationLabel(kind,item.key))} · “${escapeHtml(item.quote || '')}”</small><p>${escapeHtml(item.text)}</p><button type="button" data-annot-edit="${escapeHtml(item.id)}" data-annot-key="${escapeHtml(item.key)}">编辑</button><button type="button" data-annot-delete="${escapeHtml(item.id)}" data-annot-key="${escapeHtml(item.key)}">删除</button></article>`).join('')}`;
  }

  function drawerHtml(kind, currentPassage = '') {
    const open = drawerOpenKind === kind;
    const count = allNotes(kind).count;
    const quickNote = kind === 'reading' && currentPassage ? `<label class="annot-quick-note">Passage ${escapeHtml(currentPassage.replace(/\D/g,''))} 整篇笔记<textarea data-passage-note="${escapeHtml(currentPassage)}" placeholder="记下本篇思路，自动保存">${escapeHtml(getAttempt(kind)?.notes?.[currentPassage] || '')}</textarea></label>` : '';
    return `<button type="button" class="annot-drawer-toggle" data-annot-drawer-toggle="${escapeHtml(kind)}" aria-controls="annot-drawer" aria-expanded="${open}">✎ 全部笔记 <span data-annot-note-count>${count}</span></button><aside id="annot-drawer" class="annot-drawer" data-annot-drawer-kind="${escapeHtml(kind)}" aria-label="全部笔记" ${open ? '' : 'hidden'}><header><strong>全部笔记 <span data-annot-note-count>${count}</span></strong><button type="button" data-annot-drawer-close aria-label="收起笔记">收起 ×</button></header><div class="annot-drawer-scroll">${quickNote}<div data-annot-note-list>${noteListHtml(kind)}</div></div></aside>`;
  }

  function refreshDrawer(kind) {
    const drawer = document.querySelector('[data-annot-drawer-kind]');
    if (!drawer || drawer.dataset.annotDrawerKind !== kind) return;
    const scroll = drawer.querySelector('.annot-drawer-scroll');
    const scrollTop = scroll.scrollTop;
    drawer.querySelector('[data-annot-note-list]').innerHTML = noteListHtml(kind);
    scroll.scrollTop = scrollTop;
    document.querySelectorAll('[data-annot-note-count]').forEach(node => { node.textContent = allNotes(kind).count; });
  }

  function refresh(kind, key) {
    document.querySelectorAll('.annot-text').forEach(element => {
      if (element.dataset.annotKind === kind && element.dataset.annotKey === key) {
        element.innerHTML = renderMarkedText(element.dataset.annotSource, entries(kind, key, element.dataset.annotSource.length));
      }
    });
    refreshDrawer(kind);
  }

  function update(kind, key, fn) {
    const attempt = getAttempt(kind);
    if (!attempt || attempt.submittedAt) return;
    attempt.annotations ||= {};
    attempt.annotations[key] = fn(Array.isArray(attempt.annotations[key]) ? attempt.annotations[key] : []);
    persist(kind);
    refresh(kind, key);
  }

  function remove(kind, key, id) {
    update(kind, key, records => records.filter(item => item.id !== id));
    hideToolbar();
  }

  function selectionData() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.rangeCount) return null;
    const range = selection.getRangeAt(0);
    const startElement = (range.startContainer.nodeType === Node.ELEMENT_NODE ? range.startContainer : range.startContainer.parentElement)?.closest('.annot-text');
    const endElement = (range.endContainer.nodeType === Node.ELEMENT_NODE ? range.endContainer : range.endContainer.parentElement)?.closest('.annot-text');
    if (!startElement || startElement !== endElement || !document.querySelector('#main')?.contains(startElement)) return null;
    const kind = startElement.dataset.annotKind;
    if (!getAttempt(kind) || getAttempt(kind).submittedAt) return null;
    const before = range.cloneRange();
    before.selectNodeContents(startElement);
    before.setEnd(range.startContainer, range.startOffset);
    let start = before.toString().length;
    let end = start + range.toString().length;
    const source = startElement.dataset.annotSource;
    while (start < end && /\s/.test(source[start])) start++;
    while (end > start && /\s/.test(source[end - 1])) end--;
    if (end <= start || end > source.length) return null;
    const key = startElement.dataset.annotKey;
    const current = entries(kind,key,source.length).find(item => item.type === 'highlight' && item.start <= start && item.end >= end);
    return {kind, key, start, end, quote:source.slice(start, end), color:current?.color || null, rect:range.getBoundingClientRect()};
  }

  function position(node, rect) {
    const left = Math.min(window.innerWidth - node.offsetWidth - 12, Math.max(12, rect.left));
    const top = rect.bottom + node.offsetHeight + 12 < window.innerHeight ? rect.bottom + 8 : Math.max(8, rect.top - node.offsetHeight - 8);
    node.style.left = `${left}px`;
    node.style.top = `${top}px`;
  }

  function hideToolbar() { if (toolbar) toolbar.hidden = true; selected = null; }
  function hideEditor() { if (editor) editor.hidden = true; editorTarget = null; }
  function hideMarkMenu() { if (markMenu) markMenu.hidden = true; markTarget = null; }
  function dismiss() { hideToolbar(); hideEditor(); hideMarkMenu(); }

  function showToolbar(data) {
    if (!toolbar) {
      toolbar = document.createElement('div');
      toolbar.className = 'annot-toolbar';
      toolbar.setAttribute('role', 'toolbar');
      toolbar.setAttribute('aria-label', '选中文字后的高光和笔记工具');
      toolbar.innerHTML = `<span data-annot-color-label>高光</span>${COLORS.map(color => `<button type="button" class="annot-color annot-${color}" data-annot-color="${color}" aria-label="${COLOR_NAMES[color]}高光" title="${COLOR_NAMES[color]}高光">${COLOR_NAMES[color][0]}</button>`).join('')}<button type="button" class="annot-note-button" data-annot-new-note>＋ 笔记</button>`;
      document.body.appendChild(toolbar);
    }
    hideMarkMenu();
    selected = data;
    toolbar.hidden = false;
    toolbar.querySelector('[data-annot-color-label]').textContent = data.color ? `当前：${COLOR_NAMES[data.color]}` : '选择高光';
    toolbar.querySelectorAll('[data-annot-color]').forEach(button => button.classList.toggle('chosen', button.dataset.annotColor === (data.color || chosenColor)));
    position(toolbar, data.rect);
  }

  function showMarkMenu(mark) {
    const container = mark.closest('.annot-text');
    const kind = container?.dataset.annotKind;
    const key = container?.dataset.annotKey;
    if (!kind || !getAttempt(kind) || getAttempt(kind).submittedAt) return;
    const records = entries(kind,key,container.dataset.annotSource.length);
    const highlight = records.find(item => item.id === mark.dataset.annotHighlight);
    const note = records.find(item => item.id === mark.dataset.annotNote);
    if (!highlight && !note) return;
    if (!markMenu) {
      markMenu = document.createElement('div');
      markMenu.className = 'annot-mark-menu';
      markMenu.setAttribute('role', 'group');
      markMenu.setAttribute('aria-label', '标注操作');
      document.body.appendChild(markMenu);
    }
    hideToolbar();
    markTarget = {kind,key,highlightId:highlight?.id,noteId:note?.id,rect:mark.getBoundingClientRect()};
    markMenu.innerHTML = `${highlight ? `<span class="annot-current-color annot-${highlight.color}">当前高光：${COLOR_NAMES[highlight.color]}</span><button type="button" data-annot-remove-type="highlight">取消高光</button>` : ''}${note ? `<p>笔记：${escapeHtml(note.text)}</p><button type="button" data-annot-edit-mark>编辑笔记</button><button type="button" data-annot-remove-type="note">删除笔记</button>` : ''}`;
    markMenu.hidden = false;
    position(markMenu, markTarget.rect);
  }

  function showEditor(target, value = '') {
    if (!editor) {
      editor = document.createElement('div');
      editor.className = 'annot-editor';
      editor.setAttribute('role', 'dialog');
      editor.setAttribute('aria-label', '选词笔记');
      editor.innerHTML = '<label>笔记<textarea maxlength="2000" placeholder="写下这段文字的定位线索或想法"></textarea></label><div><button type="button" data-annot-save>保存笔记</button><button type="button" data-annot-cancel>取消</button></div>';
      document.body.appendChild(editor);
    }
    editorTarget = target;
    editor.querySelector('textarea').value = value;
    editor.hidden = false;
    position(editor, target.rect);
    editor.querySelector('textarea').focus();
  }

  function addHighlight(color) {
    if (!selected || !COLORS.includes(color)) return;
    chosenColor = color;
    const {kind, key, start, end, quote} = selected;
    update(kind, key, records => [
      ...records.flatMap(item => {
        if (item.type !== 'highlight' || item.end <= start || item.start >= end) return [item];
        const fragments = [];
        if (item.start < start) fragments.push({...item, id:crypto.randomUUID(), end:start, quote:item.quote?.slice(0,start-item.start)});
        if (item.end > end) fragments.push({...item, id:crypto.randomUUID(), start:end, quote:item.quote?.slice(end-item.start)});
        return fragments;
      }),
      {id:crypto.randomUUID(), type:'highlight', color, start, end, quote}
    ]);
    window.getSelection()?.removeAllRanges();
    hideToolbar();
    toast(`${{yellow:'黄色',green:'绿色',pink:'粉色'}[color]}高光已保存`);
  }

  function saveNote() {
    if (!editorTarget) return;
    const value = editor.querySelector('textarea').value.trim();
    if (!value) { toast('请先输入笔记内容'); return; }
    const {kind, key, start, end, quote, id} = editorTarget;
    update(kind, key, records => [...records.filter(item => item.id !== id && (item.type !== 'note' || item.end <= start || item.start >= end)), {id:id || crypto.randomUUID(), type:'note', text:value, start, end, quote}]);
    hideEditor();
    window.getSelection()?.removeAllRanges();
    toast('笔记已保存');
  }

  document.addEventListener('mouseup', event => {
    if (event.target.closest('.annot-toolbar,.annot-editor,.annot-mark-menu,.annot-drawer')) return;
    const data = selectionData();
    if (data) showToolbar(data);
    else hideToolbar();
  });
  document.addEventListener('contextmenu', event => {
    const data = selectionData();
    if (data && event.target.closest('.annot-text')) { event.preventDefault(); showToolbar(data); }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') dismiss();
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && !editor?.hidden && editor?.contains(document.activeElement)) saveNote();
  });
  document.addEventListener('click', event => {
    const drawerToggle = event.target.closest('[data-annot-drawer-toggle]');
    if (drawerToggle) {
      const kind = drawerToggle.dataset.annotDrawerToggle;
      const drawer = document.querySelector('[data-annot-drawer-kind]');
      drawerOpenKind = drawerOpenKind === kind ? null : kind;
      drawer.hidden = drawerOpenKind !== kind;
      drawerToggle.setAttribute('aria-expanded', String(!drawer.hidden));
      hideMarkMenu();
      return;
    }
    if (event.target.closest('[data-annot-drawer-close]')) {
      const drawer = document.querySelector('[data-annot-drawer-kind]');
      drawerOpenKind = null;
      drawer.hidden = true;
      document.querySelector('[data-annot-drawer-toggle]')?.setAttribute('aria-expanded','false');
      return;
    }
    const color = event.target.closest('[data-annot-color]');
    if (color) { addHighlight(color.dataset.annotColor); return; }
    if (event.target.closest('[data-annot-new-note]')) {
      if (selected) { const target = selected; hideToolbar(); showEditor(target); }
      return;
    }
    if (event.target.closest('[data-annot-save]')) { saveNote(); return; }
    if (event.target.closest('[data-annot-cancel]')) { hideEditor(); return; }
    const removeAction = event.target.closest('[data-annot-remove-type]');
    if (removeAction && markTarget) {
      const type = removeAction.dataset.annotRemoveType;
      const id = type === 'highlight' ? markTarget.highlightId : markTarget.noteId;
      if (id) { remove(markTarget.kind, markTarget.key, id); toast(type === 'highlight' ? '高光已取消' : '笔记已删除'); }
      hideMarkMenu();
      return;
    }
    if (event.target.closest('[data-annot-edit-mark]') && markTarget) {
      const {kind,key,noteId,rect} = markTarget;
      const record = getAttempt(kind)?.annotations?.[key]?.find(item => item.id === noteId);
      hideMarkMenu();
      if (record) showEditor({kind,key,...record,rect},record.text);
      return;
    }
    const edit = event.target.closest('[data-annot-edit]');
    if (edit) {
      const drawer = edit.closest('[data-annot-drawer-kind]');
      const kind = drawer?.dataset.annotDrawerKind;
      const record = getAttempt(kind)?.annotations?.[edit.dataset.annotKey]?.find(item => item.id === edit.dataset.annotEdit);
      if (record) showEditor({kind, key:edit.dataset.annotKey, ...record, rect:edit.getBoundingClientRect()}, record.text);
      return;
    }
    const del = event.target.closest('[data-annot-delete]');
    if (del) { const kind = del.closest('[data-annot-drawer-kind]')?.dataset.annotDrawerKind; if (getAttempt(kind)) remove(kind, del.dataset.annotKey, del.dataset.annotDelete); return; }
    const mark = event.target.closest('.annot-mark');
    if (mark && window.getSelection()?.isCollapsed) {
      event.preventDefault();
      showMarkMenu(mark);
      return;
    }
    if (!event.target.closest('.annot-mark-menu')) hideMarkMenu();
  });

  return {textHtml, drawerHtml, refreshDrawer, dismiss};
}

const api = {create, renderMarkedText, validRecords};
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof window !== 'undefined') window.IELTS_ANNOTATIONS = api;
})();
