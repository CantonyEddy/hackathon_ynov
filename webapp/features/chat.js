class ChatFeature {
  constructor({ apiBase, threadElement, inputElement, formElement, onMessageSent, onError }) {
    this.apiBase = apiBase;
    this.threadElement = threadElement;
    this.inputElement = inputElement;
    this.formElement = formElement;
    this.onMessageSent = onMessageSent;
    this.onError = onError;
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
    const message = this.inputElement.value.trim();
    if (!message) return;

    this.appendMessage('user', message);
    this.inputElement.value = '';
    this.autoResize();
    this.appendThinking();

    try {
      const response = await fetch(`${this.apiBase}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      this.removeThinking();
      this.appendMessage('ai', data.response || 'Réponse indisponible.');
      this.onMessageSent?.(message, data.response);
    } catch (error) {
      this.removeThinking();
      this.appendMessage('ai', 'Le serveur est indisponible. Vérifiez l’URL du backend.');
      this.onError?.(error);
    }
  }

  appendMessage(role, text) {
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
  }

  appendThinking() {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg ai';
    wrapper.innerHTML = '<div class="thinking"><span class="dot"></span><span>Analyse en cours…</span></div>';
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

  scrollDown() {
    const messages = document.getElementById('messages');
    messages.scrollTop = messages.scrollHeight;
  }
}

export default ChatFeature;
