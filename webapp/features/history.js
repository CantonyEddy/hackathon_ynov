class HistoryFeature {
  constructor({ listElement, onSelect }) {
    this.listElement = listElement;
    this.onSelect = onSelect;
  }

  render(conversations, activeConversationId) {
    this.listElement.innerHTML = '';

    conversations.forEach((conversation, index) => {
      const item = document.createElement('li');
      item.className = `history-item${conversation.id === activeConversationId ? ' active' : ''}`;
      item.tabIndex = 0;
      item.dataset.id = conversation.id;

      const dot = document.createElement('span');
      dot.className = `history-dot ${this.getDotClass(index)}`;
      item.appendChild(dot);

      const content = document.createElement('div');
      const title = document.createElement('strong');
      title.textContent = conversation.title;
      const meta = document.createElement('small');
      meta.textContent = this.getSummary(conversation);
      content.append(title, meta);
      item.appendChild(content);

      item.addEventListener('click', () => this.onSelect?.(conversation.id));
      item.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          this.onSelect?.(conversation.id);
        }
      });

      this.listElement.appendChild(item);
    });
  }

  getSummary(conversation) {
    const messageCount = conversation.messages.length;
    if (messageCount === 0) return 'Aucun message';
    return `${messageCount} message${messageCount > 1 ? 's' : ''}`;
  }

  getDotClass(index) {
    return ['accent', 'muted', 'soft'][index % 3];
  }
}

export default HistoryFeature;
