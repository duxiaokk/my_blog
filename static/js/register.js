document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("register-form");
    const statusEl = document.getElementById("register-status");
    const submitButton = form?.querySelector('button[type="submit"]');

    if (!form || !statusEl || !submitButton) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        statusEl.textContent = "正在注册...";
        submitButton.disabled = true;

        try {
            const formData = new FormData(form);
            const response = await fetch("/register", {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "same-origin",
                body: formData,
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                statusEl.textContent = data.detail || "注册失败";
                return;
            }

            window.location.href = "/";
        } catch (error) {
            statusEl.textContent = "网络错误，请稍后再试。";
        } finally {
            submitButton.disabled = false;
        }
    });
});