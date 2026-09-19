function setupAuthDialog(name, unavailableMessage) {
    const dialog = document.querySelector(`#${name}-dialog`);
    const form = document.querySelector(`#${name}-form`);
    const password = document.querySelector(`#${name}-password`);
    const passwordToggle = document.querySelector(`#toggle-${name}-password`);
    const status = document.querySelector(`#${name}-status`);

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

    form.addEventListener("submit", (event) => {
        // Frontend previews only: do not submit or store account details yet.
        event.preventDefault();
        status.hidden = false;
        status.textContent = unavailableMessage;
    });

    dialog.addEventListener("close", () => {
        form.reset();
        password.type = "password";
        passwordToggle.textContent = "Show";
        passwordToggle.setAttribute("aria-label", "Show password");
        passwordToggle.setAttribute("aria-pressed", "false");
        status.hidden = true;
        status.textContent = "";
    });
}

setupAuthDialog("register", "Registration isn't available yet. Your details haven't been saved.");
setupAuthDialog("login", "Login isn't available yet. You haven't been signed in.");
