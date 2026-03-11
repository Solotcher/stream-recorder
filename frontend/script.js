import { CONFIG } from './config.js';
import { switchView, openModal, closeModal, switchMainTab } from './ui.js';
import {
    fetchChannels,
    fetchActiveJobs,
    submitManualRecord,
    submitChannel,
    deleteChannel,
    startChannel,
    stopChannel,
    fetchSystemConfig,
    saveSystemConfig,
    fetchCookieStatus,
    saveCookieParser,
    openConfigModalWithData,
    switchCookieTab
} from './api.js';
import { initWebSocket } from './ws.js';

// HTML 안에 인라인으로 선언된 (onclick="...") 콜백들이 모듈화 이후에도 
// 전역 스코프에서 접근 가능하도록 window 객체에 맵핑해줍니다.
window.switchView = switchView;
window.openModal = openModal;
window.closeModal = closeModal;

// 채널, 작업 API 연동
window.startChannel = startChannel;
window.stopChannel = stopChannel;
window.deleteChannel = deleteChannel;
window.submitChannel = submitChannel;
window.submitManualRecord = submitManualRecord;

// 설정 및 쿠키 UI 연동
window.switchMainTab = switchMainTab;
window.switchCookieTab = switchCookieTab;
window.openConfigModal = openConfigModalWithData;
window.closeConfigModal = () => closeModal('configModal');
window.openAddModal = () => openModal('addModal');
window.closeAddModal = () => closeModal('addModal');
window.saveCookieParser = saveCookieParser;
window.saveSystemConfig = saveSystemConfig;

// 앱 로드 시점 초기화 실행
document.addEventListener('DOMContentLoaded', () => {
    switchView('active'); 
    fetchChannels();
    setInterval(fetchChannels, CONFIG.POLLING_INTERVAL_CHANNELS); 
    setInterval(fetchActiveJobs, CONFIG.POLLING_INTERVAL_JOBS);
    initWebSocket(); 
});
