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
