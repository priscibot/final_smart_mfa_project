/**
 * Login page functionality
 */

const loginForm = document.getElementById('loginForm');
const messageDiv = document.getElementById('message');
const resetProfileButton = document.getElementById('resetProfileButton');
const simulateImpostorCheckbox = document.getElementById('simulateImpostor');

function showMessage(message, type = '') {
    messageDiv.className = `message ${type}`.trim();
    messageDiv.textContent = message;
    messageDiv.style.display = 'block';
}

function buildImpostorRhythm(events) {
    let pressOffset = 0;

    return events.map((event, index) => {
        const dwell = Math.max(20, event.release_time - event.press_time);
        const dwellMultiplier = index % 2 === 0 ? 2.4 : 1.8;
        const addedPause = 140 + (index * 35);
        const pressTime = event.press_time + pressOffset;
        const releaseTime = pressTime + Math.round(dwell * dwellMultiplier);

        pressOffset += addedPause;

        return {
            ...event,
            press_time: pressTime,
            release_time: releaseTime
        };
    });
}

loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const capturedEvents = window.behavioralCapture.getKeystrokeEvents('password');
    const keystrokeEvents = simulateImpostorCheckbox.checked
        ? buildImpostorRhythm(capturedEvents)
        : capturedEvents;

    showMessage('Authenticating with password and keystroke biometrics...');

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username,
                password,
                keystroke_events: keystrokeEvents
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            const successMessage = result.details ? `${result.message} ${result.details}` : result.message;
            showMessage(successMessage, 'success');
            window.behavioralCapture.reset();

            setTimeout(() => {
                window.location.href = result.redirect || '/dashboard';
            }, 1200);
            return;
        }

        const errorMessage = result.details ? `${result.message} ${result.details}` : (result.message || 'Authentication failed.');
        showMessage(errorMessage, 'error');
    } catch (error) {
        console.error('Login error:', error);
        showMessage('Connection error. Please try again.', 'error');
    }
});

resetProfileButton.addEventListener('click', async () => {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showMessage('Enter the username and password first so the correct typing profile can be reset.', 'error');
        return;
    }

    showMessage('Resetting keystroke profile...');

    try {
        const response = await fetch('/api/reset_keystroke_profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const result = await response.json();
        showMessage(result.message || 'Unable to reset keystroke profile.', response.ok ? 'success' : 'error');
        if (response.ok) {
            window.behavioralCapture.reset();
        }
    } catch (error) {
        console.error('Profile reset error:', error);
        showMessage('Connection error while resetting keystroke profile.', 'error');
    }
});
