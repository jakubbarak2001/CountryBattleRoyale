function setupAuthDialog(name) {
    const dialog = document.querySelector(`#${name}-dialog`);
    const form = document.querySelector(`#${name}-form`);
    const password = document.querySelector(`#${name}-password`);
    const passwordToggle = document.querySelector(`#toggle-${name}-password`);

    document.querySelector(`#open-${name}`).addEventListener("click", () => {
        dialog.showModal();
    });

    dialog.querySelectorAll("[data-close-auth]").forEach((button) => {
        button.addEventListener("click", () => dialog.close());
    });

    dialog.addEventListener("click", (event) => {
        if (event.target !== dialog) return;

        const bounds = dialog.getBoundingClientRect();
        if (
            event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom
        ) {
            dialog.close();
        }
    });

    passwordToggle.addEventListener("click", () => {
        const showPassword = password.type === "password";
        password.type = showPassword ? "text" : "password";
        passwordToggle.textContent = showPassword ? "Hide" : "Show";
        passwordToggle.setAttribute("aria-label", showPassword ? "Hide password" : "Show password");
        passwordToggle.setAttribute("aria-pressed", String(showPassword));
    });

    dialog.addEventListener("close", () => {
        form.reset();
        password.type = "password";
        passwordToggle.textContent = "Show";
        passwordToggle.setAttribute("aria-label", "Show password");
        passwordToggle.setAttribute("aria-pressed", "false");
    });
}

setupAuthDialog("register");
setupAuthDialog("login");

const accountMenu = document.querySelector("#account-menu");
const accountToggle = accountMenu.querySelector("summary");

document.addEventListener("click", (event) => {
    if (!accountMenu.contains(event.target)) accountMenu.open = false;
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && accountMenu.open) {
        accountMenu.open = false;
        accountToggle.focus();
    }
});

document.addEventListener("focusin", (event) => {
    if (!accountMenu.contains(event.target)) accountMenu.open = false;
});

function showLoggedInAccount() {
    // The server confirms login; this only updates the visible header.
    document.querySelector("#guest-actions").hidden = true;
    accountMenu.hidden = false;
}

function setupRegistration() {
    const dialog = document.querySelector("#register-dialog");
    const form = document.querySelector("#register-form");
    const summary = document.querySelector("#register-form-error");
    const submit = form.querySelector('[type="submit"]');
    const success = document.querySelector("#register-success");
    const successMessage = document.querySelector("#register-success-message");
    const guest = dialog.querySelector(".auth-guest");
    const controls = [...form.querySelectorAll("input, button")];
    let pending = false;
    let dialogVersion = 0;

    function clearErrors() {
        form.querySelectorAll(".auth-error").forEach((error) => {
            error.hidden = true;
            error.textContent = "";
        });
        form.querySelectorAll('[aria-invalid="true"]').forEach((field) => {
            field.removeAttribute("aria-invalid");
        });
    }

    function highlightErrors() {
        // Restart the animation even if another error arrives during the shake.
        dialog.classList.remove("auth-dialog--error");
        void dialog.offsetWidth;
        dialog.classList.add("auth-dialog--error");
        const focusTarget = form.querySelector('[aria-invalid="true"]') || summary;
        focusTarget.focus();
    }

    function showErrors(errors) {
        clearErrors();
        for (const key of ["username", "email", "form"]) {
            const message = errors?.[key];
            if (typeof message !== "string" || !message.trim()) continue;

            const error = document.getElementById(`register-${key}-error`);
            error.textContent = message;
            error.hidden = false;
            if (key !== "form") {
                document.getElementById(`register-${key}`).setAttribute("aria-invalid", "true");
            }
        }
        if (!form.querySelector(".auth-error:not([hidden])")) {
            summary.textContent = "We couldn't create your account. Please try again.";
            summary.hidden = false;
        }
        highlightErrors();
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (pending) return;

        const body = new FormData(form);
        const version = dialogVersion;
        clearErrors();
        pending = true;
        controls.forEach((control) => { control.disabled = true; });
        form.setAttribute("aria-busy", "true");
        submit.textContent = "Creating account…";

        let response;
        let result;
        try {
            // FormData keeps Flask's request.form interface unchanged.
            response = await fetch(form.action, {
                method: "POST",
                headers: { Accept: "application/json" },
                body,
            });
            result = await response.json();
        } catch {
            result = null;
        } finally {
            pending = false;
            controls.forEach((control) => { control.disabled = false; });
            form.removeAttribute("aria-busy");
            submit.textContent = "Create account";
        }

        // Update the header even if registration finished after closing the dialog.
        if (response?.ok && result?.success === true && result?.logged === true) {
            showLoggedInAccount();
            window.location.assign("/");
            if (!dialog.open) accountToggle.focus();
        }

        // A response from a dismissed attempt must not change a reopened form.
        if (version !== dialogVersion || !dialog.open) return;

        if (response?.ok && result?.success === true) {
            form.reset();
            document.querySelector("#register-password").value = "";
            form.hidden = true;
            successMessage.textContent = typeof result.name === "string" && result.name.trim()
                ? `Welcome, ${result.name}! Your account has been created.`
                : "Your account has been created. Let the country battles begin.";
            success.hidden = false;
            guest.textContent = "Back to game";
            success.focus();
        } else if (response?.status === 409 && result?.errors) {
            showErrors(result.errors);
        } else {
            showErrors({ form: "We couldn't confirm your registration. Please try again." });
        }
    });

    form.addEventListener("input", (event) => {
        const field = event.target;
        const error = document.getElementById(`${field.id}-error`);
        if (error) {
            error.hidden = true;
            error.textContent = "";
            field.removeAttribute("aria-invalid");
        }
        summary.hidden = true;
        summary.textContent = "";
    });

    dialog.addEventListener("close", () => {
        dialogVersion += 1;
        clearErrors();
        form.hidden = false;
        success.hidden = true;
        successMessage.textContent = "";
        guest.textContent = "Keep playing as a guest";
        dialog.classList.remove("auth-dialog--error");
        if (!accountMenu.hidden) accountToggle.focus();
    });

    dialog.addEventListener("animationend", (event) => {
        if (event.target === dialog && event.animationName === "auth-shake") {
            dialog.classList.remove("auth-dialog--error");
        }
    });

    if (form.querySelector(".auth-error:not([hidden])")) {
        dialog.showModal();
        highlightErrors();
    }
}

setupRegistration();
