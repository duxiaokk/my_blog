document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("login-form");
    const statusEl = document.getElementById("login-status");

    if (!form || !statusEl) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        statusEl.textContent = "正在登录...";

        const formData = new FormData(form);
        const payload = Object.fromEntries(formData.entries());

        try {
            const response = await fetch("/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify(payload),
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                statusEl.textContent = data.detail || "登录失败";
                return;
            }

            window.location.href = "/";
        } catch (error) {
            statusEl.textContent = "网络错误，请稍后再试。";
        }
    });
});
