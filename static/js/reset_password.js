/**
 * LeadFlow — reset_password.js
 * Handles the /reset-password page: reads the token from the URL,
 * validates the new password client-side, then POSTs to /auth/reset-password.
 */

(function () {
  "use strict";

  function getCookie(name) {
    return (
      document.cookie
        .split("; ")
        .find((row) => row.startsWith(name + "="))
        ?.split("=")[1] || ""
    );
  }

  function validatePasswordStrength(value) {
    if (value.length < 10) return "Password must be at least 10 characters.";
    if (value.length > 72) return "Password must not exceed 72 characters.";
    if (!/[A-Z]/.test(value)) return "Password must contain at least one uppercase letter.";
    if (!/[a-z]/.test(value)) return "Password must contain at least one lowercase letter.";
    if (!/\d/.test(value)) return "Password must contain at least one digit.";
    if (!/[^A-Za-z0-9]/.test(value)) return "Password must contain at least one special character.";
    return null;
  }

  function showError(message) {
    const existing = document.getElementById("reset-error");
    if (existing) existing.remove();
    const el = document.createElement("p");
    el.id = "reset-error";
    el.textContent = message;
    el.style.cssText =
      "color:var(--danger);font-size:13px;margin:12px 0 0;text-align:center;";
    document.getElementById("reset-submit").insertAdjacentElement("afterend", el);
  }

  function showSuccess(message) {
    const card = document.querySelector(".auth-card");
    card.innerHTML =
      '<div class="auth-eyebrow">Secure CRM</div>' +
      '<h1 class="auth-title" style="font-size:2rem;">Password updated</h1>' +
      '<p class="auth-copy" style="margin-top:12px;">' +
      message +
      "</p>" +
      '<a href="/" class="btn btn-primary btn-full" style="display:block;margin-top:24px;text-align:center;">Sign in</a>';
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Extract token from URL — never log or expose it in DOM attributes
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token") || "";

    if (!token) {
      showError("No reset token found. Please request a new password reset link.");
      document.getElementById("reset-submit").disabled = true;
      return;
    }

    const form = document.getElementById("reset-form");
    const passwordInput = document.getElementById("reset-password");
    const confirmInput  = document.getElementById("reset-confirm");
    const submitBtn     = document.getElementById("reset-submit");

    form.addEventListener("submit", async function (event) {
      event.preventDefault();

      const password = passwordInput.value;
      const confirm  = confirmInput.value;

      // Client-side validation (server re-validates — this is UX only)
      const strengthError = validatePasswordStrength(password);
      if (strengthError) {
        passwordInput.classList.add("invalid");
        showError(strengthError);
        passwordInput.focus();
        return;
      }
      if (password !== confirm) {
        confirmInput.classList.add("invalid");
        showError("Passwords do not match.");
        confirmInput.focus();
        return;
      }

      passwordInput.classList.remove("invalid");
      confirmInput.classList.remove("invalid");
      submitBtn.disabled = true;
      submitBtn.textContent = "Updating…";

      const csrf = decodeURIComponent(getCookie("csrf_token"));
      let payload;
      try {
        const response = await fetch("/auth/reset-password", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRF-Token": csrf,
          },
          body: JSON.stringify({ token, password }),
        });
        payload = await response.json();
      } catch (_err) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Update password";
        showError("Network error. Please try again.");
        return;
      }

      if (payload.success) {
        // Remove token from URL so it can't be bookmarked or shared
        window.history.replaceState({}, document.title, "/reset-password");
        showSuccess(payload.message || "Your password has been updated. You can now sign in.");
      } else {
        submitBtn.disabled = false;
        submitBtn.textContent = "Update password";
        showError(payload.error || "Reset failed. The link may have expired — please request a new one.");
      }
    });
  });
})();
