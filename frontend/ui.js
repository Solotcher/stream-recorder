import { CONFIG } from './config.js';

// XSS 방지를 위한 HTML 이스케이프 유틸리티
export function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// 토스트 알림 함수
export function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? '✅' : '❌';
    toast.innerHTML = `<span class="toast-icon">${icon}</span> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), CONFIG.TOAST_SHOW_DELAY);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), CONFIG.TOAST_HIDE_DELAY);
    }, CONFIG.TOAST_DURATION);
}

// View 전환 (SPA 라우팅)
export function switchView(viewId, onSwitchCb = null) {
    // 모든 뷰와 메뉴 아이템의 active 클래스 제거
    document.querySelectorAll('.view-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    // 선택된 뷰 활성화
    const view = document.getElementById(`view-${viewId}`);
    if (view) view.classList.add('active');

    // 선택된 네비게이션 아이템 활성화 (속성 기반으로 변경하여 더 견고하게 만듦)
    const activeNavItem = document.querySelector(`.nav-item[data-view="${viewId}"]`);
    if (activeNavItem) activeNavItem.classList.add('active');

    if (onSwitchCb) onSwitchCb(viewId);
}

// 모달 제어 공통
export function openModal(id) { document.getElementById(id).classList.add('active'); }
export function closeModal(id) { document.getElementById(id).classList.remove('active'); }

export function switchMainTab(tabName, event = null) {
    // 1. 클릭된 버튼 하이라이트 (event가 있으면 해당 타겟 사용)
    const activeTabObj = event?.currentTarget || event?.target || null;
    
    if (activeTabObj) {
        document.querySelectorAll('.config-main-tab').forEach(b => b.classList.remove('active'));
        activeTabObj.classList.add('active');
    }

    // 2. 컨텐츠 전환
    document.querySelectorAll('.config-tab-content').forEach(c => c.style.display = 'none');
    const content = document.getElementById(`tab-content-${tabName}`);
    if (content) content.style.display = 'block';
}
