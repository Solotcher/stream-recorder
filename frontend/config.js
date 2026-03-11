export const CONFIG = {
    API_BASE: '/api',
    POLLING_INTERVAL_CHANNELS: 10000,
    POLLING_INTERVAL_JOBS: 60000,
    TOAST_DURATION: 3000,
    TOAST_SHOW_DELAY: 10,
    TOAST_HIDE_DELAY: 300,
    WS_INITIAL_RECONNECT_DELAY: 1000,
    WS_MAX_RECONNECT_DELAY: 30000
};

export let currentCookiePlatform = 'chzzk';

export function setCurrentCookiePlatform(platform) {
    currentCookiePlatform = platform;
}
