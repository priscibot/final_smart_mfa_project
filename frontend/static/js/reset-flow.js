/**
 * Password reset token verification and keystroke re-enrollment flow.
 */

function showResetMessage(element, message, type = '') {
    if (!element) {
        return;
    }

    element.className = `message ${type}`.trim();
    element.textContent = message;
    element.style.display = 'block';
}

const resetTokenForm = document.getElementById('resetTokenForm');
if (resetTokenForm) {
    resetTokenForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const role = resetTokenForm.dataset.role;
        const token = document.getElementById('token').value.trim();
        const messageEl = document.getElementById('resetTokenMessage');

        showResetMessage(messageEl, 'Verifying token...');
        try {
            const response = await fetch(`/api/${role}/verify-reset-token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });
            const result = await response.json();
            showResetMessage(messageEl, result.message || 'Verification failed.', response.ok ? 'success' : 'error');
            if (response.ok && result.success) {
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 700);
            }
        } catch (error) {
            console.error('Token verification error:', error);
            showResetMessage(messageEl, 'Unable to verify token right now.', 'error');
        }
    });
}

const resetPasswordForm = document.getElementById('resetPasswordForm');
if (resetPasswordForm) {
    resetPasswordForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const role = resetPasswordForm.dataset.role;
        const token = resetPasswordForm.dataset.token;
        const messageEl = document.getElementById('resetPasswordMessage');
        const successCard = document.getElementById('resetPasswordSuccess');

        showResetMessage(messageEl, 'Saving your new password and keystroke profile...');

        const payload = {
            token,
            password_one: document.getElementById('reset_password_1').value,
            password_two: document.getElementById('reset_password_2').value
        };

        try {
            const response = await fetch(`/api/${role}/complete-reset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            showResetMessage(messageEl, result.message || 'Reset failed.', response.ok ? 'success' : 'error');

            if (response.ok && result.success) {
                if (window.behavioralCapture) {
                    window.behavioralCapture.reset();
                }
                if (successCard) {
                    successCard.hidden = false;
                }
                resetPasswordForm.querySelector('button[type="submit"]').disabled = true;
            }
        } catch (error) {
            console.error('Reset completion error:', error);
            showResetMessage(messageEl, 'Unable to complete the reset right now.', 'error');
        }
    });
}
