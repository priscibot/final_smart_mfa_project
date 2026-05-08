/**
 * Role portal signup and signin logic.
 */

const roleAuthForm = document.getElementById('roleAuthForm');
const authMessage = document.getElementById('authMessage');
const resetKeystrokeButton = document.getElementById('resetKeystrokeButton');

function showAuthMessage(message, type = '') {
    authMessage.className = `message ${type}`.trim();
    authMessage.textContent = message;
    authMessage.style.display = 'block';
}

async function requestKeystrokeReset(role, username) {
    if (!username) {
        showAuthMessage('Enter your username first so the reset token can be sent to the registered email.', 'error');
        return;
    }

    showAuthMessage('Requesting reset token...', '');
    try {
        const response = await fetch(`/api/${role}/request-keystroke-reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username })
        });

        const result = await response.json();
        showAuthMessage(result.message || 'Reset token requested.', response.ok ? 'success' : 'error');
        if (response.ok && result.success) {
            setTimeout(() => {
                window.location.href = result.redirect || `/reset/${role}/verify-token`;
            }, 900);
        }
    } catch (error) {
        console.error('Reset request error:', error);
        showAuthMessage('Unable to request the reset token right now. Please try again.', 'error');
    }
}

if (resetKeystrokeButton) {
    resetKeystrokeButton.addEventListener('click', () => {
        if (!roleAuthForm) {
            return;
        }
        const role = roleAuthForm.dataset.role;
        const username = document.getElementById('username').value.trim();
        requestKeystrokeReset(role, username);
    });
}

if (roleAuthForm) {
    roleAuthForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const role = roleAuthForm.dataset.role;
        const mode = roleAuthForm.dataset.mode;
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        let endpoint = `/api/${role}/${mode}`;
        let payload = {};

        if (mode === 'signup') {
            payload = {
                full_name: document.getElementById('fullname').value.trim(),
                username,
                email: document.getElementById('email').value.trim(),
                password,
                confirm_password: document.getElementById('confirmPassword').value
            };
            showAuthMessage('Creating your account...');
        } else {
            payload = {
                username,
                password,
                keystroke_events: window.behavioralCapture.getKeystrokeEvents('password')
            };
            showAuthMessage('Verifying password and keystroke biometrics...');
        }

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            const message = result.details ? `${result.message} ${result.details}` : (result.message || 'Request failed.');

            if (response.ok && result.success) {
                showAuthMessage(message, 'success');
                if (window.behavioralCapture) {
                    window.behavioralCapture.reset();
                }

                setTimeout(() => {
                    window.location.href = result.redirect || `/${role}/homepage`;
                }, 1000);
                return;
            }

            showAuthMessage(message, 'error');
        } catch (error) {
            console.error('Role auth error:', error);
            showAuthMessage('Connection error. Please try again.', 'error');
        }
    });
}
