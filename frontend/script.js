const API_BASE = '/api';
let currentCookiePlatform = 'chzzk';

// XSS 방지를 위한 HTML 이스케이프 유틸리티
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// 토스트 알림 함수
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? '✅' : '❌';
    toast.innerHTML = `<span class="toast-icon">${icon}</span> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 초기 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    switchView('active'); // 기본 뷰
    fetchChannels();
    setInterval(fetchChannels, 10000); // 10초마다 갱신 (WebSocket 폴백)
    setInterval(fetchActiveJobs, 60000); // 1분마다 녹화 경과 시간 갱신
    initWebSocket(); // 실시간 업데이트 WebSocket 연결
});

// View 전환 (SPA 라우팅)
function switchView(viewId) {
    document.querySelectorAll('.view-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    document.getElementById(`view-${viewId}`).classList.add('active');

    // 네비게이션 아이템 활성화 설정 (임시 하드코딩 매칭)
    const navItems = document.querySelectorAll('.nav-item');
    if (viewId === 'active') {
        navItems[0].classList.add('active');
        fetchActiveJobs(); // 해당 뷰 진입 시 즉시 폴링
    }
    if (viewId === 'manual') navItems[1].classList.add('active');
    if (viewId === 'scheduled') navItems[2].classList.add('active');
}

// 수동 즉시 녹화 실행
async function submitManualRecord() {
    const rawInput = document.getElementById('manual_url_input').value;
    const rawPlatform = document.getElementById('manual_platform').value;
    const streamPassword = document.getElementById('manual_stream_password').value;

    if (!rawInput) return showToast('방송국 URL 또는 ID를 입력하세요.', 'error');

    const { platform, ch_id } = parseChannelUrl(rawInput, rawPlatform);

    try {
        const startRes = await fetch(`${API_BASE}/records/manual/start`, {
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

// 설정(Config) 통합 모달 제어
function openConfigModal() {
    document.getElementById('configModal').classList.add('active');
    fetchSystemConfig(); // 열 때 서버 설정값 불러오기
    fetchCookieStatus(); // 쿠키 적용 상태 불러오기
}
function closeConfigModal() { document.getElementById('configModal').classList.remove('active'); }

function switchMainTab(tabName) {
    document.querySelectorAll('.config-main-tab').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');

    document.querySelectorAll('.config-tab-content').forEach(c => c.style.display = 'none');
    document.getElementById(`tab-content-${tabName}`).style.display = 'block';
}

// 쿠키 적용 상태 조회
async function fetchCookieStatus() {
    try {
        const res = await fetch(`${API_BASE}/cookies/status`);
        const result = await res.json();
        if (res.ok && result.data) {
            const bar = document.getElementById('cookie_status_bar');
            const platforms = { chzzk: '치지직', twitch: '트위치', soop: '숲', youtube: '유튜브' };
            let html = '';
            for (const [key, label] of Object.entries(platforms)) {
                const info = result.data[key];
                const dot = document.getElementById(`cookie_dot_${key}`);
                if (info && info.applied) {
                    html += `<span style="margin-right:16px;">✅ <strong>${label}</strong> 적용됨 (${info.key_count}개 키)</span>`;
                    if (dot) dot.style.color = '#7ee787';
                } else {
                    html += `<span style="margin-right:16px;">❌ <strong>${label}</strong> 미적용</span>`;
                    if (dot) dot.style.color = '#da3633';
                }
            }
            bar.innerHTML = html;
        }
    } catch (e) {
        console.error('쿠키 상태 조회 실패:', e);
    }
}

function switchCookieTab(platform) {
    currentCookiePlatform = platform;
    document.querySelectorAll('.cookie-sub-tab').forEach(b => b.classList.remove('active'));
    event.target.closest('.cookie-sub-tab').classList.add('active');

    const label = document.getElementById('cookie_label');
    const textarea = document.getElementById('cookie_textarea');
    textarea.value = '';

    const names = { chzzk: '치지직(Chzzk)', twitch: '트위치(Twitch)', soop: '숲(SOOP)', youtube: '유튜브(YouTube)' };
    label.innerText = `${names[platform]} 통합 쿠키 뭉치 입력 (.txt / JSON)`;
    textarea.placeholder = `${names[platform]} 쿠키(EditThisCookie 등)를 복사하여 이곳에 붙여넣으세요.`;
}

// 현재 진행 중인 작업 폴링
async function fetchActiveJobs() {
    try {
        const res = await fetch(`${API_BASE}/records/active`);
        const data = await res.json();
        const tbody = document.getElementById('activeJobsTbody');
        tbody.innerHTML = '';

        const activeChannels = data.data;

        if (activeChannels.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color:var(--text-secondary);">진행 중인 녹화 작업이 없습니다.</td></tr>`;
            return;
        }

        activeChannels.forEach(ch => {
            const tr = document.createElement('tr');

            // 녹화 경과 시간 계산
            let elapsed = '';
            if (ch.started_at) {
                const startTime = new Date(ch.started_at);
                const now = new Date();
                const diffMs = now - startTime;
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
                    <button class="btn" style="color:var(--danger); border-color:rgba(218,54,51,0.5); margin-left:8px; padding:3px 8px; font-size:0.8em;" onclick="stopChannel('${escapeHtml(ch.id)}')">■ 중지</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Active Jobs 갱신 실패:", e);
    }
}

async function fetchChannels() {
    try {
        const res = await fetch(`${API_BASE}/channels`);
        const data = await res.json();
        const tbody = document.getElementById('channelTbody');
        tbody.innerHTML = '';

        data.data.forEach(ch => {
            const tr = document.createElement('tr');

            // 녹화상태 배지
            let badgeClass = 'status-offline';
            let statusText = '대기';
            if (ch.is_recording) {
                badgeClass = 'status-recording';
                statusText = '녹화 중 🔴';
            }

            let actionButtons = `
                <button class="btn" style="color:var(--accent); border-color:var(--accent); margin-right:4px;" onclick="startChannel('${ch.id}')">▶ 녹화</button>
                <button class="btn" style="color:var(--danger); border-color:rgba(218,54,51,0.5);" onclick="deleteChannel('${ch.id}')">삭제</button>
            `;

            if (ch.is_recording) {
                actionButtons = `
                    <button class="btn" style="color:var(--text-secondary); border-color:var(--glass-border); margin-right:4px;" onclick="stopChannel('${ch.id}')">■ 중지</button>
                    <button class="btn" style="color:var(--danger); border-color:rgba(218,54,51,0.5);" onclick="deleteChannel('${ch.id}')">삭제</button>
                `;
            }

            tr.innerHTML = `
                <td><strong>${escapeHtml(ch.platform).toUpperCase()}</strong></td>
                <td><strong>${escapeHtml(ch.name)}</strong><br><small style="color:var(--text-secondary)">${escapeHtml(ch.id)}</small></td>
                <td><span class="status-badge ${badgeClass}">${statusText}</span></td>
                <td>${actionButtons}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("채널 목록 불러오기 실패:", e);
    }
}

// 모달 제어
function openAddModal() { document.getElementById('addModal').classList.add('active'); }
function closeAddModal() { document.getElementById('addModal').classList.remove('active'); }

// URL 정규식 기반 채널 ID 자동 파싱 유틸리티
function parseChannelUrl(inputStr, fallbackPlatform) {
    let platform = fallbackPlatform;
    let ch_id = inputStr.trim();

    // 치지직 매칭 (chzzk.naver.com/live/어쩌고 또는 chzzk.naver.com/어쩌고)
    const chzzkMatch = inputStr.match(/(?:chzzk\.naver\.com\/live\/|chzzk\.naver\.com\/)([a-zA-Z0-9]+)/);
    if (chzzkMatch) { platform = 'chzzk'; ch_id = chzzkMatch[1]; }

    // SOOP 매칭 (play.sooplive.co.kr/아이디/어쩌고 또는 bj.afreecatv.com/아이디)
    // 슬래시(/) 뒤에 붙는 숫자는 무시하고 순수 채널ID만 가져옴
    const soopMatch = inputStr.match(/(?:play\.sooplive\.co\.kr\/|bj\.afreecatv\.com\/)([a-zA-Z0-9_]+)/);
    if (soopMatch) { platform = 'soop'; ch_id = soopMatch[1]; }

    // 트위치 매칭
    const twitchMatch = inputStr.match(/twitch\.tv\/([a-zA-Z0-9_]+)/);
    if (twitchMatch) { platform = 'twitch'; ch_id = twitchMatch[1]; }

    // URL 라우팅이 아닌 순수 문자열만 붙여넣었을 때 (경로 슬래시 제거)
    if (ch_id.includes('/')) {
        ch_id = ch_id.split('/')[0];
    }

    if (platform === 'auto') platform = 'chzzk';

    return { platform, ch_id };
}

// 채널 추가 서밋
async function submitChannel() {
    const rawPlatform = document.getElementById('modal_platform').value;
    const rawInput = document.getElementById('modal_channel_id').value;
    const name = document.getElementById('modal_channel_name').value;
    const resolution = document.getElementById('modal_resolution').value;

    if (!rawInput) return showToast('채널 ID 또는 주소를 입력하세요.', 'error');

    const { platform, ch_id } = parseChannelUrl(rawInput, rawPlatform);

    try {
        const res = await fetch(`${API_BASE}/channels`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: platform,
                id: ch_id,
                name: name || ch_id,
                resolution: resolution
            })
        });
        if (res.ok) {
            closeAddModal();
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

// 채널 삭제
async function deleteChannel(channel_id) {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
        const res = await fetch(`${API_BASE}/channels/${channel_id}`, { method: 'DELETE' });
        if (res.ok) {
            fetchChannels();
            showToast('채널이 삭제되었습니다.', 'success');
        }
    } catch (e) {
        showToast('삭제 실패', 'error');
    }
}

// 강제 녹화 시작
async function startChannel(channel_id) {
    try {
        const res = await fetch(`${API_BASE}/channel/${channel_id}/start`, { method: 'POST' });
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

// 강제 녹화 중단
async function stopChannel(channel_id) {
    try {
        const res = await fetch(`${API_BASE}/channel/${channel_id}/stop`, { method: 'POST' });
        if (res.ok) {
            showToast('녹화 중단 완료!', 'success');
            fetchChannels();
            fetchActiveJobs();
        }
    } catch (e) {
        showToast('서버 에러', 'error');
    }
}

// 통합 쿠키 저장 (파서 연동)
async function saveCookieParser() {
    const rawVal = document.getElementById('cookie_textarea').value;
    if (!rawVal) return showToast('쿠키를 텍스트 공간에 붙여넣어주세요.', 'error');

    try {
        const res = await fetch(`${API_BASE}/cookies/${currentCookiePlatform}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_cookie: rawVal })
        });
        if (res.ok) {
            const result = await res.json();
            const keyCount = result.key_count || 0;
            showToast(`${currentCookiePlatform.toUpperCase()} 쿠키 파싱 완료! (${keyCount}개 키 적용됨)`, 'success');
            document.getElementById('cookie_textarea').value = '';
            fetchCookieStatus();
        } else {
            showToast('저장 실패: 쿠키 양식이 잘못되었거나 서버 에러입니다.', 'error');
        }
    } catch (e) {
        showToast('서버 접근 에러', 'error');
    }
}

// ---------------------------
// 텔레그램 / 시스템 환경설정
// ---------------------------
async function fetchSystemConfig() {
    try {
        const res = await fetch(`${API_BASE}/config`);
        const result = await res.json();
        if (res.ok && result.data) {
            document.getElementById('sys_tg_token').value = result.data.TELEGRAM_BOT_TOKEN || '';
            document.getElementById('sys_tg_chat_id').value = result.data.TELEGRAM_CHAT_ID || '';
            document.getElementById('sys_output_dir').value = result.data.OUTPUT_DIR || '';
            if (document.getElementById('sys_rclone_remote')) {
                document.getElementById('sys_rclone_remote').value = result.data.RCLONE_REMOTE || '';
            }
            if (document.getElementById('sys_filename_pattern')) {
                document.getElementById('sys_filename_pattern').value = result.data.FILENAME_PATTERN || '{date}_{streamer}_{title}_{quality}';
            }
        }
    } catch (e) {
        console.error("환경설정 로드 에러:", e);
    }
}

async function saveSystemConfig() {
    const token = document.getElementById('sys_tg_token').value.trim();
    const chat_id = document.getElementById('sys_tg_chat_id').value.trim();
    const output_dir = document.getElementById('sys_output_dir').value.trim();
    const rclone_remote = document.getElementById('sys_rclone_remote') ? document.getElementById('sys_rclone_remote').value.trim() : '';
    const filename_pattern = document.getElementById('sys_filename_pattern') ? document.getElementById('sys_filename_pattern').value.trim() : '';

    // 마스킹된 토큰(***포함)은 서버에 전송하지 않음 (기존 값 보존)
    const safeToken = (token && !token.includes('***')) ? token : null;

    try {
        const res = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                TELEGRAM_BOT_TOKEN: safeToken,
                TELEGRAM_CHAT_ID: chat_id,
                OUTPUT_DIR: output_dir,
                RCLONE_REMOTE: rclone_remote,
                FILENAME_PATTERN: filename_pattern
            })
        });
        if (res.ok) {
            showToast('시스템 환경설정이 터미널(.env)에 안전하게 저장되었습니다.', 'success');
            closeConfigModal();
        } else {
            showToast('저장 실패', 'error');
        }
    } catch (e) {
        showToast('서버 에러', 'error');
    }
}

// ---------------------------
// WebSocket 실시간 업데이트
// ---------------------------
let ws = null;
let wsReconnectDelay = 1000; // 초기 재연결 딜레이 (1초)
const WS_MAX_RECONNECT_DELAY = 30000; // 최대 재연결 딜레이 (30초)

function initWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[WS] 실시간 연결 수립됨');
        wsReconnectDelay = 1000; // 연결 성공 시 딜레이 초기화
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWsEvent(msg.event, msg.data);
        } catch (e) {
            console.error('[WS] 메시지 파싱 실패:', e);
        }
    };

    ws.onclose = () => {
        console.log(`[WS] 연결 해제됨. ${wsReconnectDelay / 1000}초 후 재연결 시도...`);
        setTimeout(() => {
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, WS_MAX_RECONNECT_DELAY);
            initWebSocket();
        }, wsReconnectDelay);
    };

    ws.onerror = (err) => {
        console.error('[WS] 에러 발생:', err);
        ws.close();
    };
}

function handleWsEvent(eventType, data) {
    switch (eventType) {
        case 'recording_started':
        case 'recording_stopped':
            fetchActiveJobs();
            fetchChannels();
            break;
        case 'channel_added':
        case 'channel_deleted':
            fetchChannels();
            break;
        default:
            console.log('[WS] 알 수 없는 이벤트:', eventType);
    }
}
