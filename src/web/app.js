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
  const baseUrl = elements.apiBaseUrl.value.trim().replace(/\/$/, '') || '/api/v1';
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

function setStatus(target, message, type = 'success') {
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

function renderMessages() {
  elements.chatMessages.innerHTML = '';

  for (const message of state.messages) {
    const fragment = elements.messageTemplate.content.cloneNode(true);
    const root = fragment.querySelector('.message');
    const role = fragment.querySelector('.message-role');
    const content = fragment.querySelector('.message-content');

    root.classList.add(message.role);
    role.textContent = message.role === 'user' ? 'Вы' : 'Ассистент';
    content.textContent = message.content;

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
  renderMessages();
  renderFiles([]);
  fetchFiles();

  elements.uploadForm.addEventListener('submit', uploadFiles);
  elements.refreshFiles.addEventListener('click', fetchFiles);
  elements.resetChat.addEventListener('click', resetChat);
  elements.chatForm.addEventListener('submit', sendMessage);
}

bootstrap();