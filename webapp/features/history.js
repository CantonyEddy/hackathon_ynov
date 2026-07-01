class HistoryFeature {
  constructor({ listElement, onSelect }) {
    this.listElement = listElement;
    this.onSelect = onSelect;
    this.bindEvents();
  }

  bindEvents() {
    this.listElement.querySelectorAll('.history-item').forEach((item) => {
      item.addEventListener('click', () => this.select(item));
    });
  }

  select(item) {
    this.listElement.querySelectorAll('.history-item').forEach((entry) => entry.classList.remove('active'));
    item.classList.add('active');
    this.onSelect?.(item);
  }

  reset() {
    this.listElement.querySelectorAll('.history-item').forEach((entry) => entry.classList.remove('active'));
    this.listElement.querySelector('.history-item')?.classList.add('active');
  }
}

export default HistoryFeature;
