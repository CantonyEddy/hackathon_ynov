class BackendConfigFeature {
  constructor({ inputElement, buttonElement, statusElement, modelElement, onConnect }) {
    this.inputElement = inputElement;
    this.buttonElement = buttonElement;
    this.statusElement = statusElement;
    this.modelElement = modelElement;
    this.onConnect = onConnect;
    this.apiBase = localStorage.getItem('techcorp-api-base') || 'http://127.0.0.1:8001';
    this.inputElement.value = this.apiBase;
    this.bindEvents();
  }

  bindEvents() {
    this.buttonElement.addEventListener('click', () => this.connect());
  }

  connect() {
    const value = this.inputElement.value.trim().replace(/\/$/, '');
    this.apiBase = value || 'http://127.0.0.1:8001';
    localStorage.setItem('techcorp-api-base', this.apiBase);
    this.inputElement.value = this.apiBase;
    this.onConnect?.(this.apiBase);
  }

  async check() {
    try {
      const response = await fetch(`${this.apiBase}/health`);
      const data = await response.json();
      this.statusElement.textContent = `OK • ${data.backend}`;
      this.modelElement.textContent = `Modèle: ${data.model}`;
    } catch (error) {
      this.statusElement.textContent = 'Hors ligne';
      this.modelElement.textContent = 'Vérifiez l’URL du backend';
    }
  }

  getApiBase() {
    return this.apiBase;
  }
}

export default BackendConfigFeature;
