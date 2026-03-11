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

// --- 전역 함수 바인딩 (하위 호환성 유지) ---
window.switchView = switchView;
window.openModal = openModal;
window.closeModal = closeModal;
window.startChannel = startChannel;
window.stopChannel = stopChannel;
window.deleteChannel = deleteChannel;
window.submitChannel = submitChannel;
window.submitManualRecord = submitManualRecord;
window.switchMainTab = (tabName, e) => switchMainTab(tabName, e);
window.switchCookieTab = switchCookieTab;
window.openConfigModal = openConfigModalWithData;
window.saveCookieParser = saveCookieParser;
window.saveSystemConfig = saveSystemConfig;

// --- 동적 이벤트 리스너 등록 (신규 방식) ---
function bindEvents() {
    console.log('[App] 이벤트 리스너 바인딩 중...');
    
    // 1. 사이드바 네비게이션
    document.querySelectorAll('.nav-item[data-view]').forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.getAttribute('data-view');
            switchView(viewId);
        });
    });

    // 2. 모달 열기/닫기 버튼
    const btnOpenConfig = document.getElementById('btn_open_config');
    if (btnOpenConfig) btnOpenConfig.onclick = openConfigModalWithData; // api.js의 복합 로직

    const btnCloseConfig = document.getElementById('btn_close_config_modal');
    if (btnCloseConfig) btnCloseConfig.onclick = () => closeModal('configModal');

    const btnOpenAdd = document.getElementById('btn_open_add_modal');
    if (btnOpenAdd) btnOpenAdd.onclick = () => openModal('addModal');

    const btnCloseAdd = document.getElementById('btn_close_add_modal');
    if (btnCloseAdd) btnCloseAdd.onclick = () => closeModal('addModal');

    // 3. 설정 모달 내 탭 전환
    document.querySelectorAll('.config-main-tab[data-tab]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabName = btn.getAttribute('data-tab');
            switchMainTab(tabName, e);
        });
    });

    document.querySelectorAll('.cookie-sub-tab[data-cookie-platform]').forEach(btn => {
        btn.addEventListener('click', () => {
            const platform = btn.getAttribute('data-cookie-platform');
            switchCookieTab(platform);
        });
    });

    // 4. 주요 액션 버튼
    if (document.getElementById('btn_manual_record')) 
        document.getElementById('btn_manual_record').onclick = submitManualRecord;

    if (document.getElementById('btn_submit_channel')) 
        document.getElementById('btn_submit_channel').onclick = submitChannel;

    if (document.getElementById('btn_save_cookie')) 
        document.getElementById('btn_save_cookie').onclick = saveCookieParser;

    if (document.getElementById('btn_save_system_config')) 
        document.getElementById('btn_save_system_config').onclick = saveSystemConfig;
}

// --- 앱 초기화 실행 ---
const initApp = async () => {
    console.log('[App] 초기화 시작...');
    bindEvents();
    
    try {
        await fetchChannels();
    } catch (e) {
        console.error('[App] 초기 데이터 로드 실패:', e);
    }

    setInterval(fetchChannels, CONFIG.POLLING_INTERVAL_CHANNELS); 
    setInterval(fetchActiveJobs, CONFIG.POLLING_INTERVAL_JOBS);
    
    try {
        initWebSocket();
    } catch (e) {
        console.error('[App] WebSocket 초기화 실패:', e);
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
