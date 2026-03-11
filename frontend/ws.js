import { CONFIG } from './config.js';
import { fetchActiveJobs, fetchChannels } from './api.js';

let ws = null;
let wsReconnectDelay = CONFIG.WS_INITIAL_RECONNECT_DELAY;

export function initWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[WS] 실시간 연결 수립됨');
        wsReconnectDelay = CONFIG.WS_INITIAL_RECONNECT_DELAY;
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
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, CONFIG.WS_MAX_RECONNECT_DELAY);
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
