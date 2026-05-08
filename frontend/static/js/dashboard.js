/**
 * Dashboard functionality with continuous keystroke verification.
 */

let verificationInterval;
const VERIFICATION_INTERVAL_MS = 30000;

async function verifyBehavior() {
    const statusSpan = document.getElementById('behavioralStatus');
    const passwordField = document.getElementById('password');

    if (!passwordField) {
        statusSpan.textContent = 'Login keystroke profile active';
        statusSpan.style.color = '#28a745';
        return;
    }

    const keystrokeEvents = window.behavioralCapture.getKeystrokeEvents('password');

    if (keystrokeEvents.length < 5) {
        statusSpan.textContent = 'Waiting for more password typing...';
        statusSpan.style.color = '#6c757d';
        return;
    }

    try {
        const response = await fetch('/api/verify_behavioral', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ keystroke_events: keystrokeEvents })
        });

        const result = await response.json();

        if (response.ok && result.success && result.behavioral_verified) {
            statusSpan.textContent = `Verified (${(result.confidence || 0).toFixed(2)})`;
            statusSpan.style.color = '#28a745';
            return;
        }

        statusSpan.textContent = 'Verification failed';
        statusSpan.style.color = '#dc3545';
        alert(result.message || 'Unusual behavior detected. Please re-authenticate.');
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        console.error('Verification error:', error);
        statusSpan.textContent = 'Verification unavailable';
        statusSpan.style.color = '#ffc107';
    }
}

function startContinuousVerification() {
    setTimeout(verifyBehavior, 10000);
    verificationInterval = setInterval(verifyBehavior, VERIFICATION_INTERVAL_MS);
}

window.addEventListener('load', () => {
    startContinuousVerification();
});

window.addEventListener('beforeunload', () => {
    if (verificationInterval) {
        clearInterval(verificationInterval);
    }
});
