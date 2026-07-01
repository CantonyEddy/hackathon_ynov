class ChatFeature {
  constructor({ apiBase, threadElement, inputElement, formElement, onMessageAdded, onError }) {
    this.apiBase = apiBase;
    this.threadElement = threadElement;
    this.inputElement = inputElement;
    this.formElement = formElement;
    this.onMessageAdded = onMessageAdded;
    this.onError = onError;
    this.isSending = false;
    this.bindEvents();
  }

  bindEvents() {
    this.formElement.addEventListener('submit', (event) => this.handleSubmit(event));
    this.inputElement.addEventListener('input', () => this.autoResize());
    this.inputElement.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        this.formElement.requestSubmit();
      }
    });
  }

  autoResize() {
    this.inputElement.style.height = 'auto';
    this.inputElement.style.height = Math.min(this.inputElement.scrollHeight, 140) + 'px';
  }

  async handleSubmit(event) {
    event.preventDefault();
    if (this.isSending) return;

    const message = this.inputElement.value.trim();
    if (!message) return;

    this.appendMessage('user', message);
    this.inputElement.value = '';
    this.autoResize();
    this.appendThinking();
    this.setSending(true);

    try {
      const response = await fetch(`${this.apiBase}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      this.removeThinking();
      this.appendMessage('ai', data.response || 'Reponse indisponible.');
    } catch (error) {
      this.removeThinking();
      this.appendMessage('ai', "Le serveur est indisponible. Verifiez l'URL du backend.");
      this.onError?.(error);
    } finally {
      this.setSending(false);
    }
  }

  appendMessage(role, text, options = {}) {
    const { persist = true } = options;
    const wrapper = document.createElement('div');
    wrapper.className = `msg ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    wrapper.appendChild(bubble);

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    meta.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    wrapper.appendChild(meta);

    this.threadElement.appendChild(wrapper);
    this.scrollDown();

    if (persist) {
      this.onMessageAdded?.({ role, text, createdAt: new Date().toISOString() });
    }
  }

  renderMessages(messages) {
    this.clear();
    messages.forEach((message) => {
      this.appendMessage(message.role, message.text, { persist: false });
    });
  }

  appendThinking() {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg ai';
    wrapper.innerHTML = '<div class="thinking"><span class="dot"></span><span>Analyse en cours...</span></div>';
    this.threadElement.appendChild(wrapper);
    this.scrollDown();
  }

  removeThinking() {
    const thinkingRow = this.threadElement.querySelector('.thinking')?.parentElement;
    if (thinkingRow) thinkingRow.remove();
  }

  clear() {
    this.threadElement.innerHTML = '';
  }

  setSending(isSending) {
    this.isSending = isSending;
    this.inputElement.disabled = isSending;

    const submitButton = this.formElement.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = isSending;
  }

  scrollDown() {
    const messages = document.getElementById('messages');
    messages.scrollTop = messages.scrollHeight;
  }
}

export default ChatFeature;
