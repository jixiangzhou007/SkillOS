/* storage-keys.js — single source for localStorage keys */

var StorageKeys = {
  SESSION: 'sd_session',
  AUTH_TOKEN: 'sd_auth_token',
  USER: 'sd_user',
  WORKSPACE: 'sd_workspace',
  MODEL: 'sd_model',
  MODELS: 'sd_models',
  MODE: 'sd_mode',
  AUTO: 'sd_auto',
  ONBOARDING_DONE: 'skillos_onboarding_done',
  DISABLED_SKILLS: 'sd_disabled_skills',
  INSTALLED_SKILLS: 'sd_installed_skills',
  TTS_BACKEND: 'sd_tts_backend',
  TTS_VOICE: 'sd_tts_voice',
  TTS_SPEED: 'sd_tts_speed',
  TTS_EMOTION: 'sd_tts_emotion',
  ASR_ENGINE: 'sd_asr_engine'
};

function getSessionId() {
  return localStorage.getItem(StorageKeys.SESSION) || '';
}

function setSessionId(id) {
  if (id) localStorage.setItem(StorageKeys.SESSION, id);
  else localStorage.removeItem(StorageKeys.SESSION);
}

function lsGet(key, fallback) {
  var v = localStorage.getItem(key);
  return v != null && v !== '' ? v : (fallback != null ? fallback : '');
}
