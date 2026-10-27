/* Alpine store aliases + initAuth trigger */
function _def(n,s,k){Object.defineProperty(window,n,{get:function(){try{return Alpine.store(s)[k]}catch(e){return undefined}},set:function(v){try{Alpine.store(s)[k]=v}catch(e){}},configurable:true,enumerable:true});}
_def('_mode','chat','mode');_def('_currentSkill','nav','currentSkill');_def('_currentTab','nav','currentTab');
_def('_settingsTab','nav','settingsTab');_def('_skillListTab','nav','skillListTab');
_def('_selectedModel','chat','selectedModel');_def('_autoMode','chat','autoMode');_def('_sessionId','chat','sessionId');
_def('_allSkillsCache','skill','allSkillsCache');_def('_authUser','auth','user');_def('_authWorkspace','auth','workspace');

// All scripts loaded, auth.js defines initAuth
if(typeof initAuth==='function')initAuth();
