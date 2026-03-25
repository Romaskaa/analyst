const state = {
  messages: [
    {
      role: 'assistant',
      content:
        'Привет! Загрузите документы в базу знаний и задайте вопрос - я отвечу на основе материалов, которые найду в базе знаний.',
    },
  ],
};

const elements = {
  apiBaseUrl: document.getElementById('api-base-url'),
  uploadForm: document.getElementById('upload-form'),
  fileInput: document.getElementById('file-input'),
  uploadButton: document.getElementById('upload-button'),
  uploadStatus: document.getElementById('upload-status'),
  filesList: document.getElementById('files-list'),
  filesCounter: document.getElementById('files-counter'),
  refreshFiles: document.getElementById('refresh-files'),
  resetChat: document.getElementById('reset-chat'),
  chatMessages: document.getElementById('chat-messages'),
  chatForm: document.getElementById('chat-form'),
  chatInput: document.getElementById('chat-input'),
  sendButton: document.getElementById('send-button'),
  chatStatus: document.getElementById('chat-status'),
  messageTemplate: document.getElementById('message-template'),
};

function apiUrl(path) {
  const rawBaseUrl= elements.apiBaseUrl instanceof HTMLInputElement ? elements.apiBaseUrl.value : '/api/v1';
  const baseUrl = rawBaseUrl.trim().replace(/\/$/, '') || '/api/v1';
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

function setStatus(target, message, type = 'success') {

  if (!target) {
    return;
  }

  if (!message) {
    target.hidden = true;
    target.textContent = '';
    target.className = 'status-box';
    return;
  }

  target.hidden = false;
  target.textContent = message;
  target.className = `status-box ${type}`;
}

function normalizeRenderableText(content) {
  const normalized = String(content || '').replace(/\r\n?/g, '\n');
  return normalized.includes('\\n') ? normalized.replace(/\\n/g, '\n').replace(/\\t/g, '\t') : normalized;
}

function looksLikeStructuredResponse(content) {
  return /^(#{1,6}\s|[-*]\s|\d+\.\s|\|.+\||---\s*$)/m.test(content) || content.includes('```');
}

function createFragmentFromInline(text) {
  const fragment = document.createDocumentFragment();
  const pattern = /(\*\*[^*]+\*\*)|(`[^`]+`)|(\[[^\]]+\]\((https?:\/\/[^\s)]+)\))/g;
  let cursor = 0;

  for (const match of text.matchAll(pattern)) {
    const [token] = match;
    const index = match.index ?? 0;

    if (index > cursor) {
      fragment.append(document.createTextNode(text.slice(cursor, index)));
    }

    if (token.startsWith('**') && token.endsWith('**')) {
      const strong = document.createElement('strong');
      strong.textContent = token.slice(2, -2);
      fragment.append(strong);
    } else if (token.startsWith('`') && token.endsWith('`')) {
      const code = document.createElement('code');
      code.textContent = token.slice(1, -1);
      fragment.append(code);
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
      if (linkMatch) {
        const anchor = document.createElement('a');
        anchor.href = linkMatch[2];
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.textContent = linkMatch[1];
        fragment.append(anchor);
      } else {
        fragment.append(document.createTextNode(token));
      }
    }

    cursor = index + token.length;
  }

  if (cursor < text.length) {
    fragment.append(document.createTextNode(text.slice(cursor)));
  }

  return fragment;
}

function appendInlineContent(target, text) {
  target.append(createFragmentFromInline(text));
}

function isTableDividerRow(line) {
  return /^\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(line.trim());
}

function isTableRow(line) {
  return /^\s*\|.+\|\s*$/.test(line);
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

function buildMarkdownTable(lines) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message-table-scroll';

  const table = document.createElement('table');
  table.className = 'message-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  for (const cell of splitTableRow(lines[0])) {
    const th = document.createElement('th');
    appendInlineContent(th, cell);
    headerRow.append(th);
  }
  thead.append(headerRow);
  table.append(thead);

  const bodyRows = lines.slice(2);
  if (bodyRows.length) {
    const tbody = document.createElement('tbody');
    for (const row of bodyRows) {
      const tr = document.createElement('tr');
      for (const cell of splitTableRow(row)) {
        const td = document.createElement('td');
        appendInlineContent(td, cell);
        tr.append(td);
      }
      tbody.append(tr);
    }
    table.append(tbody);
  }

  wrapper.append(table);
  return wrapper;
}

function isSpecialBlockStart(line) {
  return (
    !line.trim() ||
    /^```/.test(line) ||
    /^#{1,6}\s+/.test(line) ||
    /^---\s*$/.test(line) ||
    /^\s*[-*]\s+/.test(line) ||
    /^\s*\d+\.\s+/.test(line) ||
    isTableRow(line)
  );
}

function renderStructuredMessage(container, content) {
  container.textContent = '';
  const lines = content.split('\n');
  let index = 0;

  while (index < lines.length) {
    const rawLine = lines[index];
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (/^```/.test(trimmed)) {
      const codeLines = [];
      index += 1;

      while (index < lines.length && !/^```/.test(lines[index].trim())) {
        codeLines.push(lines[index]);
        index += 1;
      }

      if (index < lines.length) {
        index += 1;
      }

      const pre = document.createElement('pre');
      const code = document.createElement('code');
      code.textContent = codeLines.join('\n');
      pre.append(code);
      container.append(pre);
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = Math.min(headingMatch[1].length, 6);
      const heading = document.createElement(`h${level}`);
      appendInlineContent(heading, headingMatch[2]);
      container.append(heading);
      index += 1;
      continue;
    }

    if (/^---\s*$/.test(trimmed)) {
      container.append(document.createElement('hr'));
      index += 1;
      continue;
    }

    if (isTableRow(trimmed) && index + 1 < lines.length && isTableDividerRow(lines[index + 1])) {
      const tableLines = [trimmed, lines[index + 1].trim()];
      index += 2;

      while (index < lines.length && isTableRow(lines[index].trim())) {
        tableLines.push(lines[index].trim());
        index += 1;
      }

      container.append(buildMarkdownTable(tableLines));
      continue;
    }

    if (/^\s*[-*]\s+/.test(rawLine)) {
      const list = document.createElement('ul');
      while (index < lines.length) {
        const itemMatch = lines[index].match(/^\s*[-*]\s+(.*)$/);
        if (!itemMatch) {
          break;
        }

        const item = document.createElement('li');
        appendInlineContent(item, itemMatch[1]);
        list.append(item);
        index += 1;
      }
      container.append(list);
      continue;
    }

    if (/^\s*\d+\.\s+/.test(rawLine)) {
      const list = document.createElement('ol');
      while (index < lines.length) {
        const itemMatch = lines[index].match(/^\s*\d+\.\s+(.*)$/);
        if (!itemMatch) {
          break;
        }

        const item = document.createElement('li');
        appendInlineContent(item, itemMatch[1]);
        list.append(item);
        index += 1;
      }
      container.append(list);
      continue;
    }

    const paragraphLines = [trimmed];
    index += 1;

    while (index < lines.length && !isSpecialBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }

    const paragraph = document.createElement('p');
    paragraphLines.forEach((paragraphLine, paragraphIndex) => {
      if (paragraphIndex > 0) {
        paragraph.append(document.createElement('br'));
      }
      appendInlineContent(paragraph, paragraphLine);
    });
    container.append(paragraph);
  }
}

function renderMessageContent(contentNode, message) {
  const normalizedContent = normalizeRenderableText(message.content);
  const isStructuredAssistantMessage =
    message.role === 'assistant' && looksLikeStructuredResponse(normalizedContent);

  contentNode.classList.toggle('rich-content', isStructuredAssistantMessage);

  if (isStructuredAssistantMessage) {
    renderStructuredMessage(contentNode, normalizedContent);
    return;
  }

  contentNode.textContent = normalizedContent;
}

function renderMessages() {
  elements.chatMessages.innerHTML = '';

  for (const message of state.messages) {
    const fragment = elements.messageTemplate.content.cloneNode(true);
    const root = fragment.querySelector('.message');
    const role = fragment.querySelector('.message-role');
    const content = fragment.querySelector('.message-content');

    root.classList.add(message.role);
    role.textContent = message.role === 'user' ? 'Вы' : 'Ассистент';
    renderMessageContent(content, message);

    elements.chatMessages.appendChild(fragment);
  }

  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function renderFiles(files) {

  elements.filesCounter.textContent = `${files.length} файлов`;
  elements.filesList.innerHTML = '';

  if (!files.length) {
    const emptyState = document.createElement('li');
    emptyState.className = 'file-item';
    emptyState.textContent = 'Файлы ещё не загружены.';
    elements.filesList.appendChild(emptyState);
    return;
  }

  for (const file of files) {
    const item = document.createElement('li');
    item.className = 'file-item';
    item.innerHTML = `
      <span class="file-name"></span>
      <span class="file-path"></span>
    `;
    item.querySelector('.file-name').textContent = file.name;
    item.querySelector('.file-path').textContent = file.path;
    elements.filesList.appendChild(item);
  }
}

async function fetchFiles() {
  setStatus(elements.uploadStatus, 'Обновляю список файлов...');

  try {
    const response = await fetch(apiUrl('/knowledge-base/files'));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    renderFiles(payload.files || []);
    setStatus(elements.uploadStatus, 'Список файлов обновлён.');
  } catch (error) {
    setStatus(elements.uploadStatus, `Не удалось получить список файлов: ${error.message}`, 'error');
  }
}

async function uploadFiles(event) {
  event.preventDefault();
  if (!(elements.fileInput instanceof HTMLInputElement) || !(elements.uploadButton instanceof HTMLButtonElement)) {
    setStatus(elements.uploadStatus, 'Форма загрузки недоступна: не найден input[type=file].', 'error');
    return;
  }

  const files = [...elements.fileInput.files];

  if (!files.length) {
    setStatus(elements.uploadStatus, 'Сначала выберите хотя бы один файл.', 'error');
    return;
  }

  elements.uploadButton.disabled = true;
  const uploaded = [];
  const failed = [];

  for (const file of files) {
    const formData = new FormData();
    formData.append('file', file);
    setStatus(elements.uploadStatus, `Загружаю: ${file.name}...`);

    try {
      const response = await fetch(apiUrl('/upload'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const payload = await response.json();
      uploaded.push(payload.path || file.name);
    } catch (error) {
      failed.push(`${file.name} (${error.message})`);
    }
  }

  elements.uploadButton.disabled = false;
  elements.fileInput.value = '';

  const statusParts = [];
  if (uploaded.length) {
    statusParts.push(`Успешно загружено:\n- ${uploaded.join('\n- ')}`);
  }
  if (failed.length) {
    statusParts.push(`Не удалось загрузить:\n- ${failed.join('\n- ')}`);
  }

  setStatus(elements.uploadStatus, statusParts.join('\n\n'), failed.length ? 'error' : 'success');
  await fetchFiles();
}

async function resetChat() {
  if (!(elements.resetChat instanceof HTMLButtonElement)) {
    setStatus(elements.chatStatus, 'Кнопка сброса недоступна.', 'error');
    return;
  }

  elements.resetChat.disabled = true;
  setStatus(elements.chatStatus, 'Сбрасываю диалог...');

  try {
    const response = await fetch(apiUrl('/chat/reset'), { method: 'POST' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    state.messages = [
      {
        role: 'assistant',
        content: 'Диалог очищен. Можете задать новый вопрос по базе знаний.',
      },
    ];
    renderMessages();
    setStatus(elements.chatStatus, 'Диалог очищен.');
  } catch (error) {
    setStatus(elements.chatStatus, `Не удалось сбросить чат: ${error.message}`, 'error');
  } finally {
    elements.resetChat.disabled = false;
  }
}

async function sendMessage(event) {
  event.preventDefault();
  if (!(elements.chatInput instanceof HTMLTextAreaElement)) {
    setStatus(elements.chatStatus, 'Поле ввода вопроса недоступно.', 'error');
    return;
  }
  if (!(elements.sendButton instanceof HTMLButtonElement)) {
    setStatus(elements.chatStatus, 'Кнопка отправки недоступна.', 'error');
    return;
  }

  const question = elements.chatInput.value.trim();

  if (!question) {
    setStatus(elements.chatStatus, 'Введите вопрос перед отправкой.', 'error');
    return;
  }

  state.messages.push({ role: 'user', content: question });
  renderMessages();
  setStatus(elements.chatStatus, 'Генерирую ответ...');
  elements.sendButton.disabled = true;
  elements.chatInput.value = '';

  try {
    const response = await fetch(apiUrl('/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: 'user', content: question }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }

    state.messages.push({
      role: 'assistant',
      content: payload.answer || 'Backend вернул пустой ответ.',
    });
    renderMessages();
    setStatus(elements.chatStatus, 'Ответ получен.');
  } catch (error) {
    state.messages.push({
      role: 'assistant',
      content: `Не удалось получить ответ от backend: ${error.message}`,
    });
    renderMessages();
    setStatus(elements.chatStatus, `Ошибка запроса: ${error.message}`, 'error');
  } finally {
    elements.sendButton.disabled = false;
  }
}

function bootstrap() {
  if (!elements.chatMessages || !elements.messageTemplate || !elements.filesList || !elements.filesCounter) {
    console.error('UI bootstrap aborted: required DOM nodes are missing.');
    return;
  }

  if (!(elements.apiBaseUrl instanceof HTMLInputElement)) {
    console.warn('Base URL input not found, fallback to /api/v1 will be used.');
  }

  renderMessages();
  renderFiles([]);
  fetchFiles();

  elements.uploadForm?.addEventListener('submit', uploadFiles);
  elements.refreshFiles?.addEventListener('click', fetchFiles);
  elements.resetChat?.addEventListener('click', resetChat);
  elements.chatForm?.addEventListener('submit', sendMessage);
}

bootstrap();