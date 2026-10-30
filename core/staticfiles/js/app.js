(function ($) {
    "use strict";

    const accountApi = "/accounts/api/v1/";
    const todoApi = "/todos/api/v1/";
    let csrfToken = "";
    let toastTimer;
    let currentPage = 1;
    let totalPages = 1;
    let historyPage = 1;
    let historyPages = 1;
    let searchTimer;

    function showToast(message, success) {
        const toast = $("#toast");
        toast.text(message).toggleClass("success", Boolean(success)).addClass("show");
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(function () { toast.removeClass("show"); }, 3800);
    }

    function flattenError(value) {
        if (value === null || value === undefined) return "";
        if (typeof value === "string") return value;
        if (Array.isArray(value)) return value.map(flattenError).filter(Boolean).join("، ");
        if (typeof value === "object") {
            if (value.error && value.error.message) return flattenError(value.error.message);
            if (value.detail) return flattenError(value.detail);
            return Object.keys(value).map(function (key) { return flattenError(value[key]); }).filter(Boolean).join("، ");
        }
        return String(value);
    }

    function apiRequest(method, url, data, options) {
        const settings = {
            url: url,
            method: method,
            dataType: "json",
            dataFilter: function (raw, type) { return type === "json" && raw === "" ? "{}" : raw; },
            headers: { "X-Client-Type": "web" },
            xhrFields: { withCredentials: true }
        };
        if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
            settings.headers["X-CSRFToken"] = csrfToken;
        }
        if (options && options.formData) {
            settings.data = data;
            settings.processData = false;
            settings.contentType = false;
        } else if (data !== undefined && method === "GET") {
            settings.data = data;
        } else if (data !== undefined) {
            settings.contentType = "application/json; charset=utf-8";
            settings.data = JSON.stringify(data);
        }
        return $.ajax(settings);
    }

    function handleApiError(xhr) {
        if (xhr.status === 401) {
            window.location.href = "/accounts/login/";
            return;
        }
        showToast(flattenError(xhr.responseJSON) || "ارتباط با سرور با مشکل روبه‌رو شد. دوباره تلاش کن.", false);
    }

    function setFormBusy(form, busy) {
        form.find(":submit").prop("disabled", busy);
    }

    function startPage() {
        const page = $("body").data("page");
        if (page === "login") bindLogin();
        if (page === "register") bindRegistration();
        if (page === "todos") bindTodos();
        if (page === "profile") loadProfile();
        if (page === "change-password") bindPasswordChange();
    }

    function initialize() {
        $.ajax({
            url: accountApi + "csrf/",
            method: "GET",
            dataType: "json",
            headers: { "X-Client-Type": "web" },
            xhrFields: { withCredentials: true }
        }).done(function (response) {
            csrfToken = response.csrfToken;
            startPage();
        }).fail(function () {
            showToast("دریافت اطلاعات امنیتی از سرور ناموفق بود. صفحه را دوباره بارگذاری کن.", false);
        });
    }

    function bindLogin() {
        $("#login-form").on("submit", function (event) {
            event.preventDefault();
            const form = $(this);
            setFormBusy(form, true);
            apiRequest("POST", accountApi + "login/", {
                email: $("#login-email").val(),
                password: $("#login-password").val()
            }).done(function () {
                window.location.href = "/todos/";
            }).fail(handleApiError).always(function () { setFormBusy(form, false); });
        });
    }

    function bindRegistration() {
        $("#register-form").on("submit", function (event) {
            event.preventDefault();
            const form = $(this);
            setFormBusy(form, true);
            apiRequest("POST", accountApi + "register/", {
                email: $("#register-email").val(),
                password: $("#register-password").val(),
                password1: $("#register-password1").val()
            }).done(function () {
                showToast("حساب کاربری با موفقیت ساخته شد. حالا وارد حساب شو.", true);
                window.setTimeout(function () { window.location.href = "/accounts/login/"; }, 900);
            }).fail(handleApiError).always(function () { setFormBusy(form, false); });
        });
    }

    function bindPasswordChange() {
        $("#change-password-form").on("submit", function (event) {
            event.preventDefault();
            const form = $(this);
            setFormBusy(form, true);
            apiRequest("PATCH", accountApi + "change-password/", {
                old_password: $("#old-password").val(),
                new_password: $("#new-password").val(),
                new_password1: $("#new-password1").val()
            }).done(function () {
                showToast("رمز عبور تغییر کرد. لطفاً دوباره وارد شو.", true);
                window.setTimeout(function () { window.location.href = "/accounts/login/"; }, 900);
            }).fail(handleApiError).always(function () { setFormBusy(form, false); });
        });
    }

    function loadProfile() {
        apiRequest("GET", accountApi + "users/me/").done(function (profile) {
            $("#first-name").val(profile.first_name || "");
            $("#last-name").val(profile.last_name || "");
            $("#profile-email").text(profile.email || "");
            $("#profile-name").text([profile.first_name, profile.last_name].filter(Boolean).join(" ") || "کاربر Todo App");
            $("#profile-avatar").attr("src", profile.image || "/static/img/profile/default.png");
        }).fail(handleApiError);

        $("#profile-form").on("submit", function (event) {
            event.preventDefault();
            const form = $(this);
            const data = new FormData();
            data.append("first_name", $("#first-name").val());
            data.append("last_name", $("#last-name").val());
            const image = $("#profile-image")[0].files[0];
            if (image) data.append("image", image);
            setFormBusy(form, true);
            apiRequest("PATCH", accountApi + "users/me/", data, { formData: true })
                .done(function (profile) {
                    $("#profile-email").text(profile.email || "");
                    $("#profile-name").text([profile.first_name, profile.last_name].filter(Boolean).join(" ") || "کاربر Todo App");
                    if (profile.image) $("#profile-avatar").attr("src", profile.image);
                    showToast("پروفایل با موفقیت به‌روز شد.", true);
                }).fail(handleApiError).always(function () { setFormBusy(form, false); });
        });
    }

    function bindTodos() {
        $("#logout-button").on("click", function () {
            const button = $(this).prop("disabled", true);
            apiRequest("POST", accountApi + "logout/").done(function () {
                window.location.href = "/accounts/login/";
            }).fail(function (xhr) {
                if (xhr.status === 401) {
                    window.location.href = "/accounts/login/";
                    return;
                }
                handleApiError(xhr);
                button.prop("disabled", false);
            });
        });

        $("#new-task-button").on("click", function () { openTaskModal(); });
        $("#close-task-modal, #cancel-task").on("click", closeTaskModal);
        $("#task-modal").on("click", function (event) {
            if (event.target === this) closeTaskModal();
        });
        $("#task-form").on("submit", saveTask);
        $("#task-search").on("input", function () {
            window.clearTimeout(searchTimer);
            searchTimer = window.setTimeout(function () { loadTasks(1); }, 300);
        });
        $("#status-filter, #priority-filter, #sort-filter").on("change", function () { loadTasks(1); });
        $("#previous-page").on("click", function () { if (currentPage > 1) loadTasks(currentPage - 1); });
        $("#next-page").on("click", function () { if (currentPage < totalPages) loadTasks(currentPage + 1); });
        $("#bulk-complete-button").on("click", completeSelectedTasks);
        $("#bulk-delete-button").on("click", deleteSelectedTasks);
        $("#show-history-button").on("click", showHistory);
        $("#hide-history-button").on("click", hideHistory);
        $("#history-previous-page").on("click", function () {
            if (historyPage > 1) loadDeletedTasks(historyPage - 1);
        });
        $("#history-next-page").on("click", function () {
            if (historyPage < historyPages) loadDeletedTasks(historyPage + 1);
        });
        loadTasks(1);
        loadStats();
        apiRequest("GET", accountApi + "users/me/").done(function (profile) {
            $("#user-email").text(profile.email || "حساب کاربری");
        }).fail(handleApiError);
    }

    function loadStats() {
        apiRequest("GET", todoApi + "task/stats/").done(function (stats) {
            $("#stat-total").text(stats.total);
            $("#stat-completed").text(stats.completed);
            $("#stat-pending").text(stats.pending);
            $("#stat-overdue").text(stats.overdue);
        }).fail(handleApiError);
    }

    function loadTasks(page) {
        const params = {
            page: page,
            page_size: 10,
            ordering: $("#sort-filter").val() || "-created_date"
        };
        const search = $("#task-search").val().trim();
        const completed = $("#status-filter").val();
        const priority = $("#priority-filter").val();
        if (search) params.search = search;
        if (completed !== "") params.is_completed = completed;
        if (priority) params.priority = priority;

        $("#task-list").html('<div class="loading-state">در حال بارگذاری کارها...</div>');
        apiRequest("GET", todoApi + "tasks-list/", params).done(function (response) {
            currentPage = response.page;
            totalPages = response.pages;
            renderTasks(response.results);
            updatePagination(response.total);
        }).fail(handleApiError);
    }

    function renderTasks(tasks) {
        const list = $("#task-list").empty();
        $("#bulk-complete-button, #bulk-delete-button").prop("disabled", true);
        if (!tasks.length) {
            list.append($("<div>", { class: "empty-state", text: "هنوز کاری در این فهرست نیست؛ اولین کار را اضافه کن." }));
            return;
        }
        tasks.forEach(function (task) {
            const row = $("<article>", { class: "task-row", "data-id": task.id });
            const checkbox = $("<input>", { class: "task-check", type: "checkbox", "aria-label": "انتخاب کار" });
            const copy = $("<div>", { class: "task-copy" });
            const title = $("<div>", { class: "task-title", text: task.title });
            if (task.is_completed) title.addClass("completed");
            copy.append(title);
            if (task.description) copy.append($("<p>", { class: "task-description", text: task.description }));

            const meta = $("<div>", { class: "task-meta" });
            meta.append($("<span>", { class: "task-badge priority-" + task.priority, text: priorityLabel(task.priority) }));
            if (task.due_date) meta.append($("<span>", { text: "موعد: " + formatDate(task.due_date) }));
            copy.append(meta);

            const actions = $("<div>", { class: "task-actions" });
            actions.append($("<button>", { type: "button", class: "icon-button edit-task", text: "✎", title: "ویرایش", "aria-label": "ویرایش کار" }));
            actions.append($("<button>", { type: "button", class: "icon-button delete delete-task", text: "×", title: "حذف", "aria-label": "حذف کار" }));
            row.append(checkbox, copy, actions).data("task", task);
            list.append(row);
        });

        list.find(".task-check").on("change", function () {
            const checked = list.find(".task-check:checked").length;
            $("#bulk-complete-button").prop("disabled", checked === 0);
            $("#bulk-delete-button").prop("disabled", checked === 0);
            $(this).closest(".task-row").toggleClass("selected", $(this).prop("checked"));
        });
        list.find(".edit-task").on("click", function () {
            openTaskModal($(this).closest(".task-row").data("task"));
        });
        list.find(".delete-task").on("click", function () {
            const row = $(this).closest(".task-row");
            if (!window.confirm("این کار حذف شود؟")) return;
            apiRequest("DELETE", todoApi + "task/" + row.data("id") + "/").done(function () {
                showToast("کار حذف شد.", true);
                loadTasks(currentPage);
                loadStats();
            }).fail(handleApiError);
        });
        list.find(".task-title").on("click", function () {
            const task = $(this).closest(".task-row").data("task");
            apiRequest("PATCH", todoApi + "task/" + task.id + "/", { is_completed: !task.is_completed })
                .done(function () { loadTasks(currentPage); loadStats(); }).fail(handleApiError);
        }).css("cursor", "pointer");
    }

    function updatePagination(total) {
        $("#page-label").text(total + " کار • صفحه " + currentPage + " از " + Math.max(totalPages, 1));
        $("#previous-page").prop("disabled", currentPage <= 1);
        $("#next-page").prop("disabled", currentPage >= totalPages);
    }

    function openTaskModal(task) {
        const form = $("#task-form")[0];
        form.reset();
        $("#task-id").val(task ? task.id : "");
        $("#task-modal-title").text(task ? "ویرایش کار" : "کار جدید");
        if (task) {
            $("#task-title").val(task.title);
            $("#task-description").val(task.description || "");
            $("#task-priority").val(task.priority);
            $("#task-due-date").val(task.due_date ? toLocalDateTime(task.due_date) : "");
        }
        $("#task-modal").addClass("open").attr("aria-hidden", "false");
        $("#task-title").trigger("focus");
    }

    function closeTaskModal() {
        $("#task-modal").removeClass("open").attr("aria-hidden", "true");
    }

    function saveTask(event) {
        event.preventDefault();
        const form = $(this);
        const id = $("#task-id").val();
        const dueDate = $("#task-due-date").val();
        const data = {
            title: $("#task-title").val().trim(),
            description: $("#task-description").val().trim(),
            priority: $("#task-priority").val(),
            due_date: dueDate ? new Date(dueDate).toISOString() : null
        };
        setFormBusy(form, true);
        apiRequest(id ? "PATCH" : "POST", id ? todoApi + "task/" + id + "/" : todoApi + "tasks-list/", data)
            .done(function () {
                closeTaskModal();
                showToast(id ? "کار به‌روز شد." : "کار جدید اضافه شد.", true);
                loadTasks(id ? currentPage : 1);
                loadStats();
            }).fail(handleApiError).always(function () { setFormBusy(form, false); });
    }

    function completeSelectedTasks() {
        const ids = $("#task-list .task-check:checked").map(function () {
            return Number($(this).closest(".task-row").data("id"));
        }).get();
        if (!ids.length) return;
        const button = $("#bulk-complete-button").prop("disabled", true);
        apiRequest("PATCH", todoApi + "task/bulk-complete/", { ids: ids }).done(function () {
            showToast("کارهای انتخاب‌شده تکمیل شدند.", true);
            loadTasks(currentPage);
            loadStats();
        }).fail(handleApiError).always(function () { button.prop("disabled", false); });
    }

    function deleteSelectedTasks() {
        const ids = $("#task-list .task-check:checked").map(function () {
            return Number($(this).closest(".task-row").data("id"));
        }).get();
        if (!ids.length || !window.confirm("کارهای انتخاب‌شده به تاریخچهٔ حذف منتقل شوند؟")) return;

        const buttons = $("#bulk-complete-button, #bulk-delete-button").prop("disabled", true);
        apiRequest("DELETE", todoApi + "task/bulk-delete/", { ids: ids }).done(function () {
            showToast("کارهای انتخاب‌شده به تاریخچه منتقل شدند.", true);
            loadTasks(currentPage);
            loadStats();
        }).fail(handleApiError).always(function () { buttons.prop("disabled", false); });
    }

    function showHistory() {
        $("#active-task-panel").prop("hidden", true);
        $("#history-panel").prop("hidden", false);
        loadDeletedTasks(1);
    }

    function hideHistory() {
        $("#history-panel").prop("hidden", true);
        $("#active-task-panel").prop("hidden", false);
    }

    function loadDeletedTasks(page) {
        $("#history-list").html('<div class="loading-state">در حال بارگذاری تاریخچه...</div>');
        apiRequest("GET", todoApi + "task/history/", { page: page, page_size: 10 })
            .done(function (response) {
                historyPage = response.page;
                historyPages = response.pages;
                renderDeletedTasks(response.results);
                $("#history-page-label").text(
                    response.total + " کار • صفحه " + historyPage + " از " + Math.max(historyPages, 1)
                );
                $("#history-previous-page").prop("disabled", historyPage <= 1);
                $("#history-next-page").prop("disabled", historyPage >= historyPages);
            }).fail(handleApiError);
    }

    function renderDeletedTasks(tasks) {
        const list = $("#history-list").empty();
        if (!tasks.length) {
            list.append($("<div>", { class: "empty-state", text: "تاریخچهٔ حذف خالی است." }));
            return;
        }

        tasks.forEach(function (task) {
            const row = $("<article>", { class: "task-row deleted-task" });
            const copy = $("<div>", { class: "task-copy" });
            copy.append($("<div>", { class: "task-title", text: task.title }));
            if (task.description) copy.append($("<p>", { class: "task-description", text: task.description }));

            const meta = $("<div>", { class: "task-meta" });
            meta.append($("<span>", { class: "task-badge priority-" + task.priority, text: priorityLabel(task.priority) }));
            if (task.deleted_at) {
                meta.append($("<span>", {
                    class: "deleted-date",
                    text: "حذف‌شده در " + formatDate(task.deleted_at)
                }));
            }
            copy.append(meta);

            const restore = $("<button>", {
                type: "button",
                class: "button button-outline restore-task",
                text: "بازگردانی"
            }).on("click", function () {
                const button = $(this).prop("disabled", true);
                apiRequest("POST", todoApi + "task/" + task.id + "/restore/").done(function () {
                    showToast("کار به فهرست اصلی بازگردانده شد.", true);
                    loadDeletedTasks(historyPage);
                    loadTasks(currentPage);
                    loadStats();
                }).fail(handleApiError).always(function () { button.prop("disabled", false); });
            });

            row.append(copy, restore);
            list.append(row);
        });
    }

    function priorityLabel(priority) {
        return { high: "اولویت زیاد", medium: "اولویت متوسط", low: "اولویت کم" }[priority] || priority;
    }

    function formatDate(value) {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return "";
        return new Intl.DateTimeFormat("fa-IR", { dateStyle: "medium", timeStyle: "short" }).format(date);
    }

    function toLocalDateTime(value) {
        const date = new Date(value);
        date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
        return date.toISOString().slice(0, 16);
    }

    $(initialize);
})(jQuery);
