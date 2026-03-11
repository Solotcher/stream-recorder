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
    document.querySelectorAll('.view-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    const view = document.getElementById(`view-${viewId}`);
    if (view) view.classList.add('active');

    // 네비게이션 아이템 활성화 설정
    const navItems = document.querySelectorAll('.nav-item');
    if (viewId === 'active' && navItems[0]) navItems[0].classList.add('active');
    if (viewId === 'manual' && navItems[1]) navItems[1].classList.add('active');
    if (viewId === 'scheduled' && navItems[2]) navItems[2].classList.add('active');

    if (onSwitchCb) onSwitchCb(viewId);
}

// 모달 제어 공통
export function openModal(id) { document.getElementById(id).classList.add('active'); }
export function closeModal(id) { document.getElementById(id).classList.remove('active'); }

export function switchMainTab(tabName) {
    const activeTabObj = event ? event.target : null;
    document.querySelectorAll('.config-main-tab').forEach(b => b.classList.remove('active'));
    if (activeTabObj) activeTabObj.classList.add('active');

    document.querySelectorAll('.config-tab-content').forEach(c => c.style.display = 'none');
    const content = document.getElementById(`tab-content-${tabName}`);
    if (content) content.style.display = 'block';
}
