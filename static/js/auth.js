document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const isAuthenticated = body.dataset.authenticated === "1";
    const modal = document.getElementById("auth-modal");
    const form = document.getElementById("auth-modal-form");
    const title = document.getElementById("auth-modal-title");
    const kicker = document.getElementById("auth-modal-kicker");
    const subtitle = document.getElementById("auth-modal-subtitle");
    const submit = document.getElementById("auth-modal-submit");
    const hint = document.getElementById("auth-modal-hint");
    const status = document.getElementById("auth-modal-status");
    const usernameInput = form?.querySelector('input[name="username"]');

    if (!modal || !form || !title || !kicker || !subtitle || !submit || !hint || !status) {
        return;
    }

    let currentMode = "login";
    let pendingUrl = "";

    const bindAvatarPicker = (root) => {
        const avatarInput = root.querySelector("[data-avatar-input]");
        const avatarPreview = root.querySelector("[data-avatar-preview]");
        const avatarPlaceholder = root.querySelector("[data-avatar-placeholder]");

        if (!avatarInput || !avatarPreview || !avatarPlaceholder) return;

        const clearAvatarPreview = () => {
            avatarPreview.hidden = true;
            avatarPreview.removeAttribute("src");
            avatarPlaceholder.hidden = false;
        };

        const setAvatarPreview = (file) => {
            if (!file) {
                clearAvatarPreview();
                return;
            }

            const reader = new FileReader();
            reader.onload = () => {
                avatarPreview.src = String(reader.result || "");
                avatarPreview.hidden = false;
                avatarPlaceholder.hidden = true;
            };
            reader.readAsDataURL(file);
        };

        avatarInput.addEventListener("change", () => {
            const file = avatarInput.files?.[0];
            setAvatarPreview(file || null);
        });

        return clearAvatarPreview;
    };

    const avatarClearers = Array.from(document.querySelectorAll(".auth-avatar"))
        .map((root) => bindAvatarPicker(root))
        .filter(Boolean);

    const clearAvatarPreviews = () => {
        avatarClearers.forEach((clearAvatarPreview) => clearAvatarPreview());
        document.querySelectorAll("[data-avatar-input]").forEach((input) => {
            input.value = "";
        });
    };

    const userMenus = Array.from(document.querySelectorAll("[data-user-menu]"));
    const profileAvatarInput = document.querySelector("[data-profile-avatar-input]");
    const profileAvatarStatus = document.querySelector("[data-profile-avatar-status]");
    const currentAvatarImage = document.querySelector("[data-current-avatar-image]");
    const currentAvatarFallback = document.querySelector("[data-current-avatar-fallback]");

    const renderAvatarMarkup = (container, avatarUrl, size = "top") => {
        if (!container) return;
        if (size === "top") {
            container.innerHTML = `<img class="auth-profile__avatar" src="${avatarUrl}" alt="头像">`;
            return;
        }
        container.innerHTML = `<img class="auth-profile__menu-avatar" src="${avatarUrl}" alt="头像">`;
    };

    const setProfileAvatar = (avatarPath) => {
        if (!avatarPath) return;
        const cacheBust = `?t=${Date.now()}`;
        const avatarUrl = `/static/images/${avatarPath.replace(/^\/+/, "")}${cacheBust}`;
        if (currentAvatarImage) {
            currentAvatarImage.src = avatarUrl;
            currentAvatarImage.hidden = false;
        }
        if (currentAvatarFallback) {
            currentAvatarFallback.hidden = true;
        }
        document.querySelectorAll("[data-user-menu-toggle]").forEach((button) => renderAvatarMarkup(button, avatarUrl, "top"));
        document.querySelectorAll("[data-avatar-display]").forEach((button) => renderAvatarMarkup(button, avatarUrl, "menu"));
    };

    const uploadProfileAvatar = async (file) => {
        if (!file) return;
        if (profileAvatarStatus) profileAvatarStatus.textContent = "正在更新头像...";

        const formData = new FormData();
        formData.append("avatar", file);

        const response = await fetch("/profile/avatar", {
            method: "POST",
            credentials: "same-origin",
            body: formData,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || "头像更新失败");
        }

        setProfileAvatar(String(data.avatar_path || ""));
        if (profileAvatarStatus) profileAvatarStatus.textContent = "头像已更新";
        window.setTimeout(() => {
            if (profileAvatarStatus) profileAvatarStatus.textContent = "";
        }, 1800);
    };

    const closeUserMenus = () => {
        userMenus.forEach((menu) => {
            menu.classList.remove("is-open");
            const panel = menu.querySelector("[data-user-menu-panel]");
            const button = menu.querySelector("[data-user-menu-toggle]");
            if (panel) panel.hidden = true;
            if (button) button.setAttribute("aria-expanded", "false");
        });
    };

    const toggleUserMenu = (menu) => {
        const panel = menu.querySelector("[data-user-menu-panel]");
        const button = menu.querySelector("[data-user-menu-toggle]");
        const isOpen = menu.classList.contains("is-open");
        closeUserMenus();
        if (isOpen) return;
        menu.classList.add("is-open");
        if (panel) panel.hidden = false;
        if (button) button.setAttribute("aria-expanded", "true");
    };

    const setMode = (mode) => {
        currentMode = mode === "register" ? "register" : "login";
        const isRegister = currentMode === "register";

        modal.dataset.mode = currentMode;
        title.textContent = isRegister ? "注册账号" : "登录到博客";
        kicker.textContent = isRegister ? "Create account" : "Welcome back";
        subtitle.textContent = isRegister
            ? "上传头像后，你的账号会更有辨识度。"
            : "登录后可以查看文章详情、评论和点赞。";
        submit.textContent = isRegister ? "注册" : "登录";
        hint.innerHTML = isRegister
            ? '已有账号？<button type="button" class="auth-link" data-auth-switch="login">去登录</button>'
            : '没有账号？<button type="button" class="auth-link" data-auth-switch="register">去注册</button>';

        if (!isRegister) {
            clearAvatarPreviews();
        }
        status.textContent = "";
    };

    const openModal = (mode = "login", nextUrl = "") => {
        pendingUrl = nextUrl;
        closeUserMenus();
        setMode(mode);
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        window.setTimeout(() => usernameInput?.focus(), 0);
    };

    const closeModal = () => {
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        status.textContent = "";
        form.reset();
        clearAvatarPreviews();
        pendingUrl = "";
    };

    document.querySelectorAll("[data-auth-open]").forEach((button) => {
        button.addEventListener("click", () => openModal(button.dataset.authOpen || "login"));
    });

    document.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;

        const menuToggle = target.closest("[data-user-menu-toggle]");
        const activeMenu = target.closest("[data-user-menu]");
        if (menuToggle) {
            const menu = menuToggle.closest("[data-user-menu]");
            if (menu) toggleUserMenu(menu);
            return;
        }

        if (target.matches("[data-auth-close]")) {
            closeModal();
        }

        if (target.matches("[data-auth-switch]")) {
            setMode(target.dataset.authSwitch || "login");
        }

        if (!activeMenu) {
            closeUserMenus();
        }
    });

    document.querySelectorAll("[data-avatar-change-trigger]").forEach((trigger) => {
        trigger.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (!profileAvatarInput) return;
            profileAvatarInput.click();
        });
    });

    if (profileAvatarInput) {
        profileAvatarInput.addEventListener("change", async () => {
            const file = profileAvatarInput.files?.[0];
            if (!file) return;
            try {
                await uploadProfileAvatar(file);
            } catch (error) {
                if (profileAvatarStatus) profileAvatarStatus.textContent = error instanceof Error ? error.message : "头像更新失败";
            } finally {
                profileAvatarInput.value = "";
            }
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modal.classList.contains("is-open")) {
            closeModal();
        }
        if (event.key === "Escape") {
            closeUserMenus();
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = currentMode === "register" ? "正在注册..." : "正在登录...";

        try {
            let response;
            if (currentMode === "register") {
                const formData = new FormData(form);
                response = await fetch("/register", {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    credentials: "same-origin",
                    body: formData,
                });
            } else {
                const formData = new FormData(form);
                const payload = Object.fromEntries(formData.entries());
                response = await fetch("/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    credentials: "same-origin",
                    body: JSON.stringify(payload),
                });
            }

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                status.textContent = data.detail || "请求失败";
                return;
            }

            const targetUrl = pendingUrl || "/";
            closeModal();
            window.location.href = targetUrl;
        } catch (error) {
            status.textContent = "网络错误，请稍后重试。";
        }
    });
});
