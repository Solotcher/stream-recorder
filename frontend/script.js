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

// --- 동적 이벤트 리스너 등록 (신규 Event Delegation 방식) ---
function bindEvents() {
    console.log('[App] 전역 이벤트 위임 리스너 바인딩 중...');

    document.addEventListener('click', (e) => {
        // 1. 사이드바 네비게이션
        const navItem = e.target.closest('.nav-item[data-view]');
        if (navItem) return switchView(navItem.dataset.view);

        // 2. 모달 열기/닫기
        if (e.target.closest('#btn_open_config')) return openConfigModalWithData();
        if (e.target.closest('#btn_close_config_modal')) return closeModal('configModal');
        if (e.target.closest('#btn_open_add_modal')) return openModal('addModal');
        if (e.target.closest('#btn_close_add_modal')) return closeModal('addModal');

        // 3. 설정 탭 전환
        const mainTab = e.target.closest('.config-main-tab[data-tab]');
        if (mainTab) return switchMainTab(mainTab.dataset.tab, { currentTarget: mainTab });

        const cookieTab = e.target.closest('.cookie-sub-tab[data-cookie-platform]');
        if (cookieTab) return switchCookieTab(cookieTab.dataset.cookiePlatform);

        // 4. 주요 액션 버튼
        if (e.target.closest('#btn_manual_record')) return submitManualRecord();
        if (e.target.closest('#btn_submit_channel')) return submitChannel();
        if (e.target.closest('#btn_save_cookie')) return saveCookieParser();
        if (e.target.closest('#btn_save_system_config')) return saveSystemConfig();

        // 5. 동적 렌더링된 채널 목록 버튼 (api.js에서 주입)
        const startBtn = e.target.closest('[data-action="start-channel"]');
        if (startBtn) return startChannel(startBtn.dataset.id);

        const stopBtn = e.target.closest('[data-action="stop-channel"]');
        if (stopBtn) return stopChannel(stopBtn.dataset.id);

        const deleteBtn = e.target.closest('[data-action="delete-channel"]');
        if (deleteBtn) return deleteChannel(deleteBtn.dataset.id);
    });
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