/**
 * Behavioral Biometrics Capture Module
 * Captures field-level keystroke events for password verification.
 */

class BehavioralCapture {
    constructor() {
        this.keystrokeData = [];
        this.mouseData = [];
        this.lastMouseTime = null;
        this.lastMousePos = { x: 0, y: 0 };

        this.initializeCapture();
    }

    initializeCapture() {
        document.addEventListener('keydown', (event) => this.handleKeyDown(event), true);
        document.addEventListener('keyup', (event) => this.handleKeyUp(event), true);
        document.addEventListener('mousemove', (event) => this.handleMouseMove(event), true);
        document.addEventListener('click', (event) => this.handleClick(event), true);
    }

    getFieldName(target) {
        if (!target) {
            return 'unknown';
        }

        return target.id || target.name || target.tagName.toLowerCase();
    }

    isTrackableField(target) {
        if (!target) {
            return false;
        }

        const tagName = (target.tagName || '').toLowerCase();
        return tagName === 'input' || tagName === 'textarea';
    }

    handleKeyDown(event) {
        if (!this.isTrackableField(event.target)) {
            return;
        }

        this.keystrokeData.push({
            key: event.key,
            field: this.getFieldName(event.target),
            press_time: Date.now(),
            release_time: null
        });

        if (this.keystrokeData.length > 200) {
            this.keystrokeData = this.keystrokeData.slice(-200);
        }
    }

    handleKeyUp(event) {
        if (!this.isTrackableField(event.target)) {
            return;
        }

        const field = this.getFieldName(event.target);
        const now = Date.now();

        for (let i = this.keystrokeData.length - 1; i >= 0; i -= 1) {
            const candidate = this.keystrokeData[i];
            if (
                candidate.key === event.key &&
                candidate.field === field &&
                candidate.release_time === null
            ) {
                candidate.release_time = now;
                break;
            }
        }
    }

    handleMouseMove(event) {
        const now = Date.now();
        const x = event.clientX;
        const y = event.clientY;

        if (this.lastMousePos.x !== 0 || this.lastMousePos.y !== 0) {
            const distance = Math.sqrt(
                ((x - this.lastMousePos.x) ** 2) +
                ((y - this.lastMousePos.y) ** 2)
            );
            const timeDiff = this.lastMouseTime ? now - this.lastMouseTime : 0;

            this.mouseData.push({
                x,
                y,
                timestamp: now,
                velocity: timeDiff > 0 ? (distance / timeDiff) * 1000 : 0
            });
        }

        this.lastMousePos = { x, y };
        this.lastMouseTime = now;

        if (this.mouseData.length > 200) {
            this.mouseData = this.mouseData.slice(-200);
        }
    }

    handleClick(event) {
        this.mouseData.push({
            x: event.clientX,
            y: event.clientY,
            timestamp: Date.now(),
            event_type: 'click'
        });
    }

    getKeystrokeEvents(fieldName = null) {
        return this.keystrokeData
            .filter((event) => event.release_time !== null)
            .filter((event) => !fieldName || event.field === fieldName)
            .map((event) => ({
                key: event.key,
                field: event.field,
                press_time: event.press_time,
                release_time: event.release_time
            }));
    }

    getMouseEvents() {
        return this.mouseData.map((event) => ({ ...event }));
    }

    reset() {
        this.keystrokeData = [];
        this.mouseData = [];
        this.lastMouseTime = null;
        this.lastMousePos = { x: 0, y: 0 };
    }
}

window.behavioralCapture = new BehavioralCapture();
