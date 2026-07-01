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
const historyList = document.getElementById('history-list');

const CONVERSATIONS_KEY = 'techcorp-conversations';
const ACTIVE_CONVERSATION_KEY = 'techcorp-active-conversation';
const DEFAULT_GREETING = "Bonjour, comment puis-je vous aider aujourd'hui ?";

let apiBase = localStorage.getItem('techcorp-api-base') || 'http://127.0.0.1:8001';
let conversations = loadConversations();
let activeConversationId = getInitialActiveConversationId();

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
  onMessageAdded: (message) => addMessageToActiveConversation(message),
  onError: () => {}
});

const historyFeature = new HistoryFeature({
  listElement: historyList,
  onSelect: (conversationId) => selectConversation(conversationId)
});

clearChat.addEventListener('click', () => {
  const conversation = getActiveConversation();
  conversation.title = 'Nouvelle conversation';
  conversation.messages = [];
  conversation.updatedAt = new Date().toISOString();
  saveConversations();

  chatFeature.clear();
  chatFeature.appendMessage('ai', DEFAULT_GREETING);
  renderHistory();
});

newChatButton.addEventListener('click', () => {
  const conversation = createConversation();
  conversations.unshift(conversation);
  activeConversationId = conversation.id;
  saveConversations();
  saveActiveConversation();
  renderApp();
});

backendConfig.check();
renderApp();

function renderApp() {
  renderHistory();
  chatFeature.renderMessages(getActiveConversation().messages);
}

function renderHistory() {
  historyFeature.render(conversations, activeConversationId);
}

function selectConversation(conversationId) {
  if (!conversations.some((conversation) => conversation.id === conversationId)) return;

  activeConversationId = conversationId;
  saveActiveConversation();
  renderApp();
}

function addMessageToActiveConversation(message) {
  const conversation = getActiveConversation();
  conversation.messages.push(message);
  conversation.updatedAt = new Date().toISOString();

  if (message.role === 'user' && conversation.title === 'Nouvelle conversation') {
    conversation.title = makeTitle(message.text);
  }

  conversations = [
    conversation,
    ...conversations.filter((item) => item.id !== conversation.id)
  ];
  activeConversationId = conversation.id;

  saveConversations();
  saveActiveConversation();
  renderHistory();
}

function getActiveConversation() {
  return conversations.find((conversation) => conversation.id === activeConversationId) || conversations[0];
}

function getInitialActiveConversationId() {
  if (conversations.length === 0) {
    const conversation = createConversation();
    conversations = [conversation];
    saveConversations();
    return conversation.id;
  }

  const storedId = localStorage.getItem(ACTIVE_CONVERSATION_KEY);
  const storedConversationExists = conversations.some((conversation) => conversation.id === storedId);
  return storedConversationExists ? storedId : conversations[0].id;
}

function createConversation() {
  return {
    id: `conversation-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title: 'Nouvelle conversation',
    messages: [{ role: 'ai', text: DEFAULT_GREETING, createdAt: new Date().toISOString() }],
    updatedAt: new Date().toISOString()
  };
}

function loadConversations() {
  try {
    const parsed = JSON.parse(localStorage.getItem(CONVERSATIONS_KEY) || '[]');
    if (!Array.isArray(parsed)) return [];

    return parsed
      .filter((conversation) => conversation && Array.isArray(conversation.messages))
      .map((conversation) => ({
        id: conversation.id || `conversation-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        title: conversation.title || 'Nouvelle conversation',
        messages: conversation.messages.filter((message) => message.role && message.text),
        updatedAt: conversation.updatedAt || new Date().toISOString()
      }));
  } catch (error) {
    return [];
  }
}

function saveConversations() {
  localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations));
}

function saveActiveConversation() {
  localStorage.setItem(ACTIVE_CONVERSATION_KEY, activeConversationId);
}

function makeTitle(text) {
  return text.length > 34 ? `${text.slice(0, 31)}...` : text;
}
