(() => {
'use strict';

const COLORS = ['yellow', 'green', 'pink'];
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
    html += `<span class="${classes.join(' ')}"${highlight ? ` data-annot-highlight="${escapeHtml(highlight.id)}"` : ''}${note ? ` data-annot-note="${escapeHtml(note.id)}"` : ''} title="${note ? `笔记：${escapeHtml(note.text)}；单击删除` : '单击取消高光'}">${part}</span>`;
  }
  return html;
}

function create({getAttempt, persist, toast}) {
  let chosenColor = 'yellow';
  let selected = null;
  let editorTarget = null;
  let toolbar;
  let editor;

  function entries(kind, key, sourceLength) {
    const attempt = getAttempt(kind);
    return validRecords(attempt?.annotations?.[key], sourceLength);
  }

  function textHtml(kind, key, source) {
    const text = String(source ?? '');
    return `<span class="annot-text" data-annot-kind="${escapeHtml(kind)}" data-annot-key="${escapeHtml(key)}" data-annot-source="${escapeHtml(text)}">${renderMarkedText(text, entries(kind, key, text.length))}</span>`;
  }

  function notesHtml(kind, prefix) {
    const attempt = getAttempt(kind);
    const matches = key => Array.isArray(prefix) ? prefix.some(item => key === item || key.startsWith(`${item}:opt:`)) : key.startsWith(prefix);
    const scope = Array.isArray(prefix) ? `data-annot-keys="${escapeHtml(JSON.stringify(prefix))}"` : `data-annot-prefix="${escapeHtml(prefix)}"`;
    const items = Object.entries(attempt?.annotations || {}).filter(([key]) => matches(key))
      .flatMap(([key, records]) => (Array.isArray(records) ? records : []).filter(item => item?.type === 'note' && item.text).map(item => ({key, ...item})));
    return `<details class="annot-notes-panel" data-annot-notes-panel data-annot-kind="${escapeHtml(kind)}" ${scope}><summary>选词笔记（${items.length}）</summary>${items.length ? items.map(item => `<div class="annot-note-item"><small>${escapeHtml(item.quote || '')}</small><p>${escapeHtml(item.text)}</p><button type="button" data-annot-edit="${escapeHtml(item.id)}" data-annot-key="${escapeHtml(item.key)}">编辑</button><button type="button" data-annot-delete="${escapeHtml(item.id)}" data-annot-key="${escapeHtml(item.key)}">删除</button></div>`).join('') : '<p class="annot-empty">选中原文或题干，点击“笔记”即可记录。</p>'}</details>`;
  }

  function refresh(kind, key) {
    document.querySelectorAll('.annot-text').forEach(element => {
      if (element.dataset.annotKind === kind && element.dataset.annotKey === key) {
        element.innerHTML = renderMarkedText(element.dataset.annotSource, entries(kind, key, element.dataset.annotSource.length));
      }
    });
    document.querySelectorAll('[data-annot-notes-panel]').forEach(panel => {
      const scope = panel.dataset.annotKeys ? JSON.parse(panel.dataset.annotKeys) : panel.dataset.annotPrefix;
      if (panel.dataset.annotKind !== kind || !(Array.isArray(scope) ? scope.some(item => key === item || key.startsWith(`${item}:opt:`)) : key.startsWith(scope))) return;
      const replacement = document.createElement('div');
      replacement.innerHTML = notesHtml(kind, scope);
      const next = replacement.firstElementChild;
      next.open = panel.open;
      panel.replaceWith(next);
    });
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
    return {kind, key:startElement.dataset.annotKey, start, end, quote:source.slice(start, end), rect:range.getBoundingClientRect()};
  }

  function position(node, rect) {
    const left = Math.min(window.innerWidth - node.offsetWidth - 12, Math.max(12, rect.left));
    const top = rect.bottom + node.offsetHeight + 12 < window.innerHeight ? rect.bottom + 8 : Math.max(8, rect.top - node.offsetHeight - 8);
    node.style.left = `${left}px`;
    node.style.top = `${top}px`;
  }

  function hideToolbar() { if (toolbar) toolbar.hidden = true; selected = null; }
  function hideEditor() { if (editor) editor.hidden = true; editorTarget = null; }

  function showToolbar(data) {
    if (!toolbar) {
      toolbar = document.createElement('div');
      toolbar.className = 'annot-toolbar';
      toolbar.setAttribute('role', 'toolbar');
      toolbar.setAttribute('aria-label', '选中文字后的高光和笔记工具');
      toolbar.innerHTML = `<span>高光</span>${COLORS.map(color => `<button type="button" class="annot-color annot-${color}" data-annot-color="${color}" aria-label="${{yellow:'黄色',green:'绿色',pink:'粉色'}[color]}高光" title="${{yellow:'黄色',green:'绿色',pink:'粉色'}[color]}高光"></button>`).join('')}<button type="button" class="annot-note-button" data-annot-new-note>＋ 笔记</button>`;
      document.body.appendChild(toolbar);
    }
    selected = data;
    toolbar.hidden = false;
    toolbar.querySelectorAll('[data-annot-color]').forEach(button => button.classList.toggle('chosen', button.dataset.annotColor === chosenColor));
    position(toolbar, data.rect);
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
    if (event.target.closest('.annot-toolbar,.annot-editor')) return;
    const data = selectionData();
    if (data) showToolbar(data);
    else hideToolbar();
  });
  document.addEventListener('contextmenu', event => {
    const data = selectionData();
    if (data && event.target.closest('.annot-text')) { event.preventDefault(); showToolbar(data); }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { hideToolbar(); hideEditor(); }
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && !editor?.hidden && editor?.contains(document.activeElement)) saveNote();
  });
  document.addEventListener('click', event => {
    const color = event.target.closest('[data-annot-color]');
    if (color) { addHighlight(color.dataset.annotColor); return; }
    if (event.target.closest('[data-annot-new-note]')) {
      if (selected) { const target = selected; hideToolbar(); showEditor(target); }
      return;
    }
    if (event.target.closest('[data-annot-save]')) { saveNote(); return; }
    if (event.target.closest('[data-annot-cancel]')) { hideEditor(); return; }
    const edit = event.target.closest('[data-annot-edit]');
    if (edit) {
      const panel = edit.closest('[data-annot-notes-panel]');
      const record = getAttempt(panel.dataset.annotKind)?.annotations?.[edit.dataset.annotKey]?.find(item => item.id === edit.dataset.annotEdit);
      if (record) showEditor({kind:panel.dataset.annotKind, key:edit.dataset.annotKey, ...record, rect:edit.getBoundingClientRect()}, record.text);
      return;
    }
    const del = event.target.closest('[data-annot-delete]');
    if (del) { const kind = del.closest('[data-annot-notes-panel]').dataset.annotKind; if (getAttempt(kind)) remove(kind, del.dataset.annotKey, del.dataset.annotDelete); return; }
    const mark = event.target.closest('.annot-mark');
    if (mark && window.getSelection()?.isCollapsed) {
      event.preventDefault();
      const container = mark.closest('.annot-text');
      const id = mark.dataset.annotNote || mark.dataset.annotHighlight;
      if (id && getAttempt(container.dataset.annotKind)) { remove(container.dataset.annotKind, container.dataset.annotKey, id); toast(mark.dataset.annotNote ? '笔记已删除' : '高光已取消'); }
    }
  });

  return {textHtml, notesHtml};
}

const api = {create, renderMarkedText, validRecords};
if (typeof module !== 'undefined' && module.exports) module.exports = api;
if (typeof window !== 'undefined') window.IELTS_ANNOTATIONS = api;
})();
