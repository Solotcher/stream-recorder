import { CONFIG, currentCookiePlatform } from './config.js';
import { showToast, escapeHtml, switchView, closeModal, openModal } from './ui.js';

/**
 * URL 정규식 기반 채널 ID 자동 파싱 유틸리티
 */
export function parseChannelUrl(inputStr, fallbackPlatform) {
    let platform = fallbackPlatform;
    let ch_id = inputStr.trim();

    const chzzkMatch = inputStr.match(/(?:chzzk\.naver\.com\/live\/|chzzk\.naver\.com\/)([a-zA-Z0-9]+)/);
    if (chzzkMatch) { platform = 'chzzk'; ch_id = chzzkMatch[1]; }

    const soopMatch = inputStr.match(/(?:play\.sooplive\.co\.kr\/|bj\.afreecatv\.com\/)([a-zA-Z0-9_]+)/);
    if (soopMatch) { platform = 'soop'; ch_id = soopMatch[1]; }

    const twitchMatch = inputStr.match(/twitch\.tv\/([a-zA-Z0-9_]+)/);
    if (twitchMatch) { platform = 'twitch'; ch_id = twitchMatch[1]; }

    if (ch_id.includes('/')) {
        ch_id = ch_id.split('/')[0];
    }

    if (platform === 'auto') platform = 'chzzk';

    return { platform, ch_id };
}

export async function fetchChannels() {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/channels`);
        const data = await res.json();
        const tbody = document.getElementById('channelTbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        data.data.forEach(ch => {
            const tr = document.createElement('tr');
            let badgeClass = 'status-offline';
            let statusText = '대기';
            if (ch.is_recording) {
                badgeClass = 'status-recording';
                statusText = '녹화 중 🔴';
            }

            let actionButtons = `
                <button class="btn" style="color:var(--accent); border-color:var(--accent); margin-right:4px;" data-action="start-channel" data-id="${ch.id}">▶ 녹화</button>
                <button class="btn" style="color:var(--danger); border-color:rgba(218,54,51,0.5);" data-action="delete-channel" data-id="${ch.id}">삭제</button>
            `;

            if (ch.is_recording) {
                actionButtons = `
                    <button class="btn" style="color:var(--text-secondary); border-color:var(--glass-border); margin-right:4px;" data-action="stop-channel" data-id="${ch.id}">■ 중지</button>
                    <button class="btn" style="color:var(--danger); border-color:rgba(218,54,51,0.5);" data-action="delete-channel" data-id="${ch.id}">삭제</button>
                `;
            }

            const rawResolution = ch.resolution || 'best';
            let displayResolution = rawResolution === 'best' ? '최고 화질' : (rawResolution === 'worst' ? '최저 화질' : rawResolution.toUpperCase());

            tr.innerHTML = `
                <td><strong>${escapeHtml(ch.platform).toUpperCase()}</strong></td>
                <td><strong>${escapeHtml(ch.name)}</strong><br><small style="color:var(--text-secondary)">${escapeHtml(ch.id)}</small></td>
                <td><span style="color:var(--accent); font-weight:500;">${escapeHtml(displayResolution)}</span></td>
                <td><span class="status-badge ${badgeClass}">${statusText}</span></td>
                <td>${actionButtons}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("채널 목록 불러오기 실패:", e);
    }
}

export async function fetchActiveJobs() {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/records/active`);
        const data = await res.json();
        const tbody = document.getElementById('activeJobsTbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        const activeChannels = data.data;

        if (activeChannels.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color:var(--text-secondary);">진행 중인 녹화 작업이 없습니다.</td></tr>`;
            return;
        }

        activeChannels.forEach(ch => {
            const tr = document.createElement('tr');
            let elapsed = '';
            if (ch.started_at) {
                const diffMs = new Date() - new Date(ch.started_at);
                const hours = Math.floor(diffMs / 3600000);
                const mins = Math.floor((diffMs % 3600000) / 60000);
                elapsed = hours > 0 ? `${hours}시간 ${mins}분` : `${mins}분`;
            }

            const badgeLabel = ch.record_type === 'manual' ?
                '<span class="status-badge" style="background-color: var(--accent); color: black;">수동</span>' :
                '<span class="status-badge" style="background-color: #238636; color: white;">예약</span>';

            tr.innerHTML = `
                <td><strong>${escapeHtml(ch.platform).toUpperCase()}</strong> ${badgeLabel}</td>
                <td><strong>${escapeHtml(ch.name)}</strong></td>
                <td>${escapeHtml(ch.title) || '<span style="color:var(--text-secondary)">제목 없음</span>'}</td>
                <td>${escapeHtml(ch.category) || '<span style="color:var(--text-secondary)">-</span>'}</td>
                <td>
                    <span style="color:#7ee787;">녹화 중 🔴</span>
                    <span style="color:var(--text-secondary); font-size:0.85em; margin-left:6px;">${elapsed}</span>
                    <button class="btn" style="color:var(--danger); border-color:rgba(218,54,51,0.5); margin-left:8px; padding:3px 8px; font-size:0.8em;" data-action="stop-channel" data-id="${ch.id}">■ 중지</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Active Jobs 갱신 실패:", e);
    }
}

export async function submitManualRecord() {
    const rawInput = document.getElementById('manual_url_input').value;
    const rawPlatform = document.getElementById('manual_platform').value;
    const streamPassword = document.getElementById('manual_stream_password').value;

    if (!rawInput) return showToast('방송국 URL 또는 ID를 입력하세요.', 'error');

    const { platform, ch_id } = parseChannelUrl(rawInput, rawPlatform);

    try {
        const startRes = await fetch(`${CONFIG.API_BASE}/records/manual/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: platform,
                id: ch_id,
                name: `수동녹화_${ch_id}`,
                stream_password: streamPassword
            })
        });

        if (startRes.ok) {
            showToast('녹화 시작을 요청했습니다. 현황을 확인하세요.', 'success');
            document.getElementById('manual_url_input').value = '';
            switchView('active');
        } else {
            let errorMsg = '녹화 명령 실패. 오프라인이거나 이미 녹화 중일 수 있습니다.';
            try {
                const errData = await startRes.json();
                if (errData.detail) errorMsg = `오류: ${errData.detail}`;
            } catch (e) { }
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('서버 처리 중 에러 발생: ' + e.message, 'error');
    }
}

export async function submitChannel() {
    const rawPlatform = document.getElementById('modal_platform').value;
    const rawInput = document.getElementById('modal_channel_id').value;
    const name = document.getElementById('modal_channel_name').value;
    const resolution = document.getElementById('modal_resolution').value;

    if (!rawInput) return showToast('채널 ID 또는 주소를 입력하세요.', 'error');
    const { platform, ch_id } = parseChannelUrl(rawInput, rawPlatform);

    try {
        const res = await fetch(`${CONFIG.API_BASE}/channels`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform, id: ch_id, name: name || ch_id, resolution })
        });
        if (res.ok) {
            closeModal('addModal');
            fetchChannels();
            document.getElementById('modal_channel_id').value = '';
            document.getElementById('modal_channel_name').value = '';
            showToast('채널이 성공적으로 등록/업데이트 되었습니다!', 'success');
        } else {
            showToast('등록 실패! 이미 있는 채널인지 확인하세요.', 'error');
        }
    } catch (e) {
        showToast('서버 접속 또는 처리 중 에러가 발생했습니다.', 'error');
    }
}

export async function deleteChannel(channel_id) {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
        const res = await fetch(`${CONFIG.API_BASE}/channels/${channel_id}`, { method: 'DELETE' });
        if (res.ok) {
            fetchChannels();
            showToast('채널이 삭제되었습니다.', 'success');
        }
    } catch (e) {
        showToast('삭제 실패', 'error');
    }
}

export async function startChannel(channel_id) {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/channel/${channel_id}/start`, { method: 'POST' });
        if (res.ok) {
            showToast('녹화 시작 요청 성공!', 'success');
            fetchChannels();
            fetchActiveJobs();
        } else {
            let errorMsg = '서버 처리 실패. 이미 녹화 중이거나 채널이 오프라인일 수 있습니다.';
            try {
                const errData = await res.json();
                if (errData.detail) errorMsg = `오류: ${errData.detail}`;
            } catch (e) { }
            showToast(errorMsg, 'error');
        }
    } catch (e) {
        showToast('서버 호출 에러: ' + e.message, 'error');
    }
}

export async function stopChannel(channel_id) {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/channel/${channel_id}/stop`, { method: 'POST' });
        if (res.ok) {
            showToast('녹화 중단 완료!', 'success');
            fetchChannels();
            fetchActiveJobs();
        }
    } catch (e) {
        showToast('서버 에러', 'error');
    }
}

// =====================================================================
// 환경 설정 및 쿠키 관련 함수 모음
// =====================================================================

export async function openConfigModalWithData() {
    openModal('configModal');
    await fetchSystemConfig();
    await fetchCookieStatus();
}

export async function fetchSystemConfig() {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/config`);
        if (res.ok) {
            const result = await res.json();
            const data = result.data || {};

            document.getElementById('sys_tg_token').value = data.TELEGRAM_BOT_TOKEN || '';
            document.getElementById('sys_tg_chat_id').value = data.TELEGRAM_CHAT_ID || '';
            document.getElementById('sys_output_dir').value = data.OUTPUT_DIR || '';
            document.getElementById('sys_rclone_remote').value = data.RCLONE_REMOTE || '';
            document.getElementById('sys_filename_pattern').value = data.FILENAME_PATTERN || '';
        } else {
            console.warn("시스템 설정을 불러오지 못했습니다. (API 확인 필요)");
        }
    } catch (e) {
        console.error("시스템 설정 Fetch 에러:", e);
    }
}

export async function saveSystemConfig() {
    const payload = {
        TELEGRAM_BOT_TOKEN: document.getElementById('sys_tg_token').value,
        TELEGRAM_CHAT_ID: document.getElementById('sys_tg_chat_id').value,
        OUTPUT_DIR: document.getElementById('sys_output_dir').value,
        RCLONE_REMOTE: document.getElementById('sys_rclone_remote').value,
        FILENAME_PATTERN: document.getElementById('sys_filename_pattern').value
    };

    try {
        const res = await fetch(`${CONFIG.API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast('시스템 설정이 저장되었습니다.', 'success');
            closeModal('configModal');
        } else {
            showToast('설정 저장 실패!', 'error');
        }
    } catch (e) {
        showToast('서버 접속 에러: ' + e.message, 'error');
    }
}

export async function fetchCookieStatus() {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/cookies/status`);
        if (res.ok) {
            const result = await res.json();
            const data = result.data || {};
            const statusBar = document.getElementById('cookie_status_bar');

            if (statusBar) {
                let statusHtml = '';
                const platforms = { chzzk: '치지직', twitch: '트위치', soop: '숲', youtube: '유튜브' };

                for (const [plat, name] of Object.entries(platforms)) {
                    // 서버가 {"applied": true} 형태로 주는 값을 파싱합니다.
                    const isOk = data[plat] && data[plat].applied;
                    statusHtml += `<span style="margin-right:12px; color:${isOk ? '#7ee787' : 'var(--text-secondary)'};">${name}: ${isOk ? '✅' : '❌'}</span>`;

                    const dot = document.getElementById(`cookie_dot_${plat}`);
                    if (dot) dot.style.color = isOk ? '#7ee787' : 'var(--text-secondary)';
                }
                statusBar.innerHTML = statusHtml || '쿠키 상태를 불러왔습니다.';
            }
        }
    } catch (e) {
        console.error("쿠키 상태 Fetch 에러:", e);
    }
}

export async function saveCookieParser() {
    const cookieText = document.getElementById('cookie_textarea').value;

    if (!cookieText.trim()) {
        return showToast('쿠키 내용을 입력하세요.', 'error');
    }

    const activeTab = document.querySelector('.cookie-sub-tab.active');
    const platform = activeTab ? activeTab.dataset.cookiePlatform : 'chzzk';

    try {
        const res = await fetch(`${CONFIG.API_BASE}/cookies/${platform}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_cookie: cookieText })
        });

        if (res.ok) {
            showToast(`${platform} 쿠키가 성공적으로 저장되었습니다!`, 'success');
            document.getElementById('cookie_textarea').value = '';
            fetchCookieStatus();
        } else {
            showToast('쿠키 저장 실패! 형식을 확인하세요.', 'error');
        }
    } catch (e) {
        showToast('서버 접속 에러: ' + e.message, 'error');
    }
}

export async function switchCookieTab(tabName) {
    document.querySelectorAll('.cookie-sub-tab').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`.cookie-sub-tab[data-cookie-platform="${tabName}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    const label = document.getElementById('cookie_label');
    if (label) {
        const platformNames = { 'chzzk': '치지직(Chzzk)', 'twitch': '트위치(Twitch)', 'soop': '숲(SOOP)', 'youtube': '유튜브(YouTube)' };
        label.innerText = `${platformNames[tabName] || tabName} 통합 쿠키 뭉치 입력`;
    }
}

export async function loadConfigAndCookies() {
    fetchSystemConfig();
    fetchCookieStatus();
}