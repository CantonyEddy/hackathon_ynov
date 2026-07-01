import ChatFeature from './features/chat.js';
import HistoryFeature from './features/history.js';
import BackendConfigFeature from './features/backend-config.js';

const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const serverStatus = document.getElementById('server-status');
const serverModel = document.getElementById('server-model');
const clearChat = document.getElementById('clear-chat');
const backendUrlInput = document.getElementById('backend-url');
const connectBackendButton = document.getElementById('connect-backend');
const thread = document.getElementById('thread');
const newChatButton = document.getElementById('new-chat');
const historyList = document.querySelector('.history-list');

let apiBase = localStorage.getItem('techcorp-api-base') || 'http://127.0.0.1:8001';

const backendConfig = new BackendConfigFeature({
  inputElement: backendUrlInput,
  buttonElement: connectBackendButton,
  statusElement: serverStatus,
  modelElement: serverModel,
  onConnect: (baseUrl) => {
    apiBase = baseUrl;
    chatFeature.apiBase = baseUrl;
    backendConfig.check();
  }
});

const chatFeature = new ChatFeature({
  apiBase,
  threadElement: thread,
  inputElement: messageInput,
  formElement: chatForm,
  onMessageSent: () => {},
  onError: () => {}
});

const historyFeature = new HistoryFeature({
  listElement: historyList,
  onSelect: () => {}
});

clearChat.addEventListener('click', () => {
  chatFeature.clear();
  chatFeature.appendMessage('ai', 'Bonjour, comment puis-je vous aider aujourd’hui ?');
});

newChatButton.addEventListener('click', () => {
  chatFeature.clear();
  chatFeature.appendMessage('ai', 'Nouvelle conversation prête. Dites-moi ce que vous souhaitez analyser.');
  historyFeature.reset();
});

backendConfig.check();
chatFeature.appendMessage('ai', 'Bonjour, comment puis-je vous aider aujourd’hui ?');
