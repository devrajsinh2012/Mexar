/**
 * MEXAR API Client - Phase 2
 * Clean API client aligned with backend endpoints.
 */

import axios from 'axios';

// API Base URL - uses environment variable for production
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// Create axios instance
const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token interceptor
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ===== AUTHENTICATION =====

export const login = async (email, password) => {
  const response = await client.post('/api/auth/login', { email, password });
  return response.data;
};

export const register = async (email, password) => {
  const response = await client.post('/api/auth/register', { email, password });
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await client.get('/api/auth/me');
  return response.data;
};

export const changePassword = async (oldPassword, newPassword) => {
  const response = await client.post('/api/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  });
  return response.data;
};

// ===== AGENTS =====

export const listAgents = async () => {
  const response = await client.get('/api/agents/');
  // Frontend expects { agents: [...] }
  return { agents: response.data };
};

export const getAgent = async (agentName) => {
  const response = await client.get(`/api/agents/${agentName}`);
  return response.data;
};

export const deleteAgent = async (agentName) => {
  const response = await client.delete(`/api/agents/${agentName}`);
  return response.data;
};

export const getAgentGraph = async (agentName) => {
  const response = await client.get(`/api/agents/${agentName}/graph`);
  return response.data;
};

// ===== COMPILATION =====

export const compileAgent = async (name, systemPrompt, files) => {
  const formData = new FormData();
  formData.append('agent_name', name);
  formData.append('system_prompt', systemPrompt);
  files.forEach(file => formData.append('files', file));

  const response = await client.post('/api/compile/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getCompileStatus = async (agentName) => {
  const response = await client.get(`/api/compile/${agentName}/status`);
  return response.data;
};

// ===== CHAT =====

export const sendMessage = async (agentName, message, includeTTS = false, ttsProvider = 'elevenlabs') => {
  const response = await client.post('/api/chat/', {
    agent_name: agentName,
    message: message,
    include_explainability: true,
    include_tts: includeTTS,
    tts_provider: ttsProvider
  });
  return response.data;
};

export const sendMultimodalMessage = async (agentName, message, audio = null, image = null, includeTTS = false, ttsProvider = 'elevenlabs') => {
  const formData = new FormData();
  formData.append('agent_name', agentName);
  formData.append('message', message);
  formData.append('include_tts', includeTTS);
  formData.append('tts_provider', ttsProvider);
  if (audio) formData.append('audio', audio);
  if (image) formData.append('image', image);

  const response = await client.post('/api/chat/multimodal', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getChatHistory = async (agentName, limit = 50) => {
  const response = await client.get(`/api/chat/${agentName}/history?limit=${limit}`);
  return response.data;
};

export const clearChatHistory = async (agentName) => {
  const response = await client.delete(`/api/chat/${agentName}/history`);
  return response.data;
};

// ===== TEXT-TO-SPEECH =====

export const generateTTS = async (text, provider = 'elevenlabs', voiceId = null) => {
  const response = await client.post('/api/chat/tts/generate', {
    text,
    provider,
    voice_id: voiceId
  });
  return response.data;
};

export const getTTSVoices = async (provider = 'elevenlabs') => {
  const response = await client.get(`/api/chat/tts/voices?provider=${provider}`);
  return response.data;
};

export const getTTSQuota = async () => {
  const response = await client.get('/api/chat/tts/quota');
  return response.data;
};

export const getTTSAudioURL = (filename) => {
  return `${API_BASE_URL}/api/chat/tts/audio/${filename}`;
};

// ===== LIVE AUDIO TRANSCRIPTION =====

export const transcribeAudio = async (audioBlob, language = 'en') => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');
  formData.append('language', language);

  const response = await client.post('/api/chat/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// ===== VALIDATION & PROMPTS =====

export const validateFiles = async (files) => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  const response = await client.post('/api/validate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const analyzePrompt = async (prompt) => {
  const response = await client.post('/api/analyze-prompt', { prompt });
  return response.data;
};

export const getPromptTemplates = async () => {
  const response = await client.get('/api/prompt-templates');
  return response.data;
};

// Legacy alias for backward compatibility
export const checkAgentStatus = getAgent;

export default client;
