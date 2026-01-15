/**
 * OBS Overlay - Live Subtitles
 * Connects to WebSocket and renders subtitles in real-time.
 */

// Defaults (will be overridden by server config)
let SUBTITLE_TTL_MS = 4500;
let MAX_LINES = 2;
const RECONNECT_DELAY_MS = 2000;

class SubtitleOverlay {
    constructor() {
        this.textElement = document.getElementById('subtitle-text');
        this.ws = null;
        this.fadeTimeout = null;
        this.lines = [];
        this.init();
    }

    async init() {
        await this.loadConfig();
        this.connect();
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            if (response.ok) {
                const config = await response.json();
                SUBTITLE_TTL_MS = config.subtitle_ttl_ms || SUBTITLE_TTL_MS;
                MAX_LINES = config.max_lines || MAX_LINES;
                console.log(`Config loaded: TTL=${SUBTITLE_TTL_MS}ms, MaxLines=${MAX_LINES}`);
            }
        } catch (e) {
            console.warn('Failed to load config, using defaults:', e);
        }
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        console.log(`[WebSocket] Connecting to: ${wsUrl}`);

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('[WebSocket] Connected ✓');
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(event.data);
        };

        this.ws.onclose = () => {
            console.log('[WebSocket] Disconnected, reconnecting in 2s...');
            setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
        };

        this.ws.onerror = (error) => {
            console.error('[WebSocket] Error:', error);
        };
    }

    handleMessage(data) {
        console.log('[WebSocket] Raw message:', data);
        try {
            const event = JSON.parse(data);
            const timestamp = new Date().toLocaleTimeString();

            switch (event.type) {
                case 'final':
                    console.log(`[${timestamp}] [WebSocket] FINAL (${event.language || 'unknown'}): "${event.text}" [Mic: ${event.microphone || 'default'}]`);
                    this.showSubtitle(event.text);
                    break;
                case 'partial':
                    console.log(`[${timestamp}] [WebSocket] PARTIAL: "${event.text}"`);
                    this.showPartial(event.text);
                    break;
                case 'clear':
                    console.log(`[${timestamp}] [WebSocket] CLEAR`);
                    this.clearSubtitle();
                    break;
                default:
                    console.log(`[${timestamp}] [WebSocket] UNKNOWN EVENT:`, event);
            }
        } catch (e) {
            console.error('[WebSocket] Parse error:', e, '| Raw data:', data);
        }
    }

    showSubtitle(text) {
        if (!text || !text.trim()) {
            return;
        }

        // Add to lines buffer
        this.lines.push(text.trim());

        // Keep only last N lines
        if (this.lines.length > MAX_LINES) {
            this.lines.shift();
        }

        // Render
        this.textElement.textContent = this.lines.join('\n');
        this.textElement.classList.remove('hidden');

        // Reset fade timeout
        this.resetFadeTimeout();
    }

    showPartial(text) {
        // For partial results, show in a lighter style
        // Currently just showing the same way as final
        if (!text || !text.trim()) {
            return;
        }

        const displayText = this.lines.length > 0
            ? this.lines.join('\n') + '\n' + text.trim()
            : text.trim();

        this.textElement.textContent = displayText;
        this.textElement.classList.remove('hidden');
    }

    clearSubtitle() {
        this.lines = [];
        this.textElement.classList.add('hidden');
        if (this.fadeTimeout) {
            clearTimeout(this.fadeTimeout);
            this.fadeTimeout = null;
        }
    }

    resetFadeTimeout() {
        if (this.fadeTimeout) {
            clearTimeout(this.fadeTimeout);
        }

        this.fadeTimeout = setTimeout(() => {
            this.textElement.classList.add('hidden');
            // Clear lines after fade animation
            setTimeout(() => {
                this.lines = [];
            }, 500);
        }, SUBTITLE_TTL_MS);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.subtitleOverlay = new SubtitleOverlay();
});
