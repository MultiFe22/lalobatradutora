/**
 * OBS Overlay - Live Subtitles
 * Connects to WebSocket and renders subtitles in real-time.
 */

const SUBTITLE_TTL_MS = 4500;  // Optimized for RPG dialogue pacing
const RECONNECT_DELAY_MS = 2000;
const MAX_LINES = 2;

class SubtitleOverlay {
    constructor() {
        this.textElement = document.getElementById('subtitle-text');
        this.ws = null;
        this.fadeTimeout = null;
        this.lines = [];
        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(event.data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting...');
            setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(data) {
        try {
            const event = JSON.parse(data);

            switch (event.type) {
                case 'final':
                    this.showSubtitle(event.text);
                    break;
                case 'partial':
                    // Optionally show interim results with different styling
                    this.showPartial(event.text);
                    break;
                case 'clear':
                    this.clearSubtitle();
                    break;
                default:
                    console.log('Unknown event type:', event.type);
            }
        } catch (e) {
            console.error('Failed to parse message:', e);
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
