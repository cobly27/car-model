const PLACEHOLDER_IMAGE = "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20400%20300'%3E%3Crect%20width='400'%20height='300'%20fill='%23f2f4f8'/%3E%3Ctext%20x='200'%20y='158'%20font-family='Arial'%20font-size='24'%20fill='%23909aaa'%20text-anchor='middle'%3ENo%20image%3C/text%3E%3C/svg%3E";
const UI_STATE_KEY = "catalogV2UiState";
const THEME_KEY = "minigtTheme";
const FAVORITE_SLIDESHOW_DISMISSED_KEY = "favoriteSlideshowDismissed";
const FAVORITE_SLIDESHOW_INTERVAL = 2300;

const state = {
    data: null,
    updateConfigs: [],
    imagePolicies: {},
    health: null,
    healthIssueFilter: null,
    productsByCategory: new Map(),
    stats: {},
    pageStats: { "Released": 0, "Pre-Order": 0, "Sold Out": 0 },
    filteredTotal: 0,
    categoryTotal: 0,
    currentPageProductsList: [],
    productRequestToken: 0,
    currentCategory: "",
    currentFilter: "",
    currentPage: 1,
    pageSize: 20,
    currentView: "cards",
    searchQuery: "",
    filteredProducts: [],
    filterByCategory: {},
    pageByCategory: {},
    searchTimer: null,
    statusTimer: null,
    statusAutoCloseTimer: null,
    activeUpdateType: "",
    favorites: loadFavorites(),
    imageCache: new Map(),
    pagePreloadTimer: null,
    modalImages: [],
    modalIndex: 0,
    modalName: "",
    modalToken: 0,
    slideshowItems: [],
    slideshowIndex: 0,
    slideshowTimer: null,
    slideshowPlaying: true,
    slideshowToken: 0,
    slideshowFailedUrls: new Set(),
    lastFavoriteSku: "",
};

const categoryScopedFilters = {
    "mini-gt": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "topspeed": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "spark": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "spark64": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "inno": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "poprace": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "gcd": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "dct": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "ar": new Set(["", "fav"]),
};

function $(selector) {
    return document.querySelector(selector);
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function loadFavorites() {
    try {
        const primary = JSON.parse(localStorage.getItem("minigtFavorites") || "[]");
        const legacy = JSON.parse(localStorage.getItem("minigt_favorites") || "[]");
        return new Set([...primary, ...legacy]);
    } catch {
        return new Set();
    }
}

function saveFavorites() {
    const values = [...state.favorites];
    localStorage.setItem("minigtFavorites", JSON.stringify(values));
    localStorage.setItem("minigt_favorites", JSON.stringify(values));
}

function favoriteSkus() {
    return [...state.favorites].filter(Boolean);
}

function loadUiState() {
    try {
        return JSON.parse(localStorage.getItem(UI_STATE_KEY) || "{}");
    } catch {
        return {};
    }
}

function saveUiState() {
    if (!state.data) return;
    localStorage.setItem(UI_STATE_KEY, JSON.stringify({
        currentCategory: state.currentCategory,
        currentFilter: state.currentFilter,
        currentPage: state.currentPage,
        pageSize: state.pageSize,
        currentView: state.currentView,
    }));
}

function statusClass(status) {
    if (status === "Released") return "released";
    if (status === "Pre-Order") return "preorder";
    if (status === "Sold Out") return "soldout";
    return "";
}

function productUrl(product) {
    const detailId = product.detail_id ?? "";
    if (product.categoryId === "ar") return `http://www.armodel.com.cn/product/detail.html?id=${detailId}`;
    if (product.categoryId === "topspeed") return `https://topspeed.tsm-models.com/index.php?action=product-detail&id=${detailId}`;
    if (product.categoryId === "spark" || product.categoryId === "spark64") return `https://www.sparkmodel.com/en/products/${detailId}`;
    if (product.categoryId === "inno") return product.inno_url || "https://www.inno-models.com/our-products/?jsf=jet-engine:shop-loop&tax=pa_scale:1-64";
    if (product.categoryId === "poprace") return product.poprace_source_url || "https://www.xcartoys.com/S_series";
    if (product.categoryId === "gcd") return product.gcd_url || "https://www.gcd-models.com/category/products/gcd/";
    if (product.categoryId === "dct") return product.dct_url || "https://www.gcd-models.com/category/products/dct/";
    return `https://minigt.tsm-models.com/index.php?action=product-detail&id=${detailId}`;
}

function imagePolicy(categoryId) {
    return state.imagePolicies[categoryId] || {};
}

function rawImages(product, mode = "display") {
    const images = [];
    const source = Array.isArray(product.images) && product.images.length ? product.images : [product.image];
    source.forEach(image => {
        if (image && !images.includes(image)) images.push(image);
    });
    const policy = imagePolicy(product.categoryId);
    const maxImages = policy.maxImages;
    const result = images.length ? images : [PLACEHOLDER_IMAGE];
    if ((mode === "modal" || mode === "card") && Number.isFinite(maxImages) && maxImages > 0) {
        return result.slice(0, maxImages);
    }
    return result;
}

function imageForDisplay(src, categoryId, mode = "card") {
    if (!src || src === PLACEHOLDER_IMAGE) return PLACEHOLDER_IMAGE;
    const policy = imagePolicy(categoryId);
    const modePolicy = policy[mode] || policy.card || {};
    if (modePolicy.proxy && modePolicy.sourcePrefix && src.startsWith(modePolicy.sourcePrefix)) {
        return `${modePolicy.proxy}?src=${encodeURIComponent(src)}`;
    }
    return src;
}

function preloadImage(src, priority = "auto") {
    if (!src || src === PLACEHOLDER_IMAGE) return Promise.resolve();
    const cached = state.imageCache.get(src);
    if (cached) {
        if (cached.status === "failed" && priority === "high") {
            state.imageCache.delete(src);
        } else {
            return cached.promise;
        }
    }

    const entry = { status: "loading", promise: null };
    entry.promise = new Promise((resolve, reject) => {
        const img = new Image();
        img.decoding = "async";
        if ("fetchPriority" in img) img.fetchPriority = priority;
        img.onload = () => {
            entry.status = "ready";
            resolve(src);
        };
        img.onerror = () => {
            entry.status = "failed";
            reject(new Error(`image failed: ${src}`));
        };
        img.src = src;
    });
    state.imageCache.set(src, entry);
    return entry.promise;
}

function uniqueUrls(urls) {
    return urls.filter((url, index) => url && urls.indexOf(url) === index && url !== PLACEHOLDER_IMAGE);
}

function runWhenIdle(callback) {
    if ("requestIdleCallback" in window) {
        window.requestIdleCallback(callback, { timeout: 900 });
    } else {
        setTimeout(callback, 120);
    }
}

function preloadInBatches(urls, { firstBatch = 8, batchSize = 8 } = {}) {
    const unique = uniqueUrls(urls);
    unique.slice(0, firstBatch).forEach(src => preloadImage(src, "high").catch(() => {}));

    let index = firstBatch;
    function loadNextBatch() {
        unique.slice(index, index + batchSize).forEach(src => preloadImage(src).catch(() => {}));
        index += batchSize;
        if (index < unique.length) runWhenIdle(loadNextBatch);
    }
    if (index < unique.length) runWhenIdle(loadNextBatch);
}

function scheduleCurrentPageImagePreload(products) {
    clearTimeout(state.pagePreloadTimer);
    state.pagePreloadTimer = setTimeout(() => {
        const urls = products.map(product => {
            const images = rawImages(product, "card");
            return imageForDisplay(images[0], product.categoryId, "card");
        });
        preloadInBatches(urls);
    }, 80);
}

function modalImages(product) {
    return rawImages(product, "modal").map(src => imageForDisplay(src, product.categoryId, "modal"));
}

function getCategory(categoryId = state.currentCategory) {
    return state.data?.categories?.find(category => category.id === categoryId) || null;
}

async function loadCatalog() {
    const [catalogResponse, updateConfigResponse] = await Promise.all([
        fetch("/api/catalog-meta"),
        fetch("/api/update-config"),
    ]);
    if (!catalogResponse.ok) throw new Error(`catalog HTTP ${catalogResponse.status}`);
    if (!updateConfigResponse.ok) throw new Error(`update-config HTTP ${updateConfigResponse.status}`);
    const data = await catalogResponse.json();
    const updateConfig = await updateConfigResponse.json();

    applyCatalogPayload(data, updateConfig, false, loadUiState());
}

function applyCatalogPayload(data, updateConfig, preserveState = false, savedState = {}) {
    const previousFilters = preserveState ? { ...state.filterByCategory } : {};
    const previousPages = preserveState ? { ...state.pageByCategory } : {};
    const previousCategory = preserveState ? state.currentCategory : savedState.currentCategory || "";

    state.productsByCategory.clear();
    state.filterByCategory = {};
    state.pageByCategory = {};

    let index = 1;
    data.categories.forEach(category => {
        const products = (category.products || []).map(product => ({
            ...product,
            categoryId: category.id,
            index: index++,
        }));
        state.productsByCategory.set(category.id, products);
        state.filterByCategory[category.id] = previousFilters[category.id] || "";
        state.pageByCategory[category.id] = previousPages[category.id] || 1;
    });

    state.data = data;
    state.updateConfigs = updateConfig.updates || [];
    state.imagePolicies = data.image_policies || {};
    state.stats = data.category_stats || {};
    if (!preserveState) {
        state.pageSize = [20, 50, 100].includes(Number(savedState.pageSize)) ? Number(savedState.pageSize) : 20;
        state.currentView = savedState.currentView === "table" ? "table" : "cards";
        state.searchQuery = "";
    }

    const categoryExists = data.categories.some(category => category.id === previousCategory);
    state.currentCategory = preserveState && categoryExists ? previousCategory : data.categories[0]?.id || "";
    if (!preserveState && categoryExists) state.currentCategory = previousCategory;
    state.currentFilter = state.filterByCategory[state.currentCategory] || "";
    if (!preserveState && savedState.currentFilter) {
        const allowed = categoryScopedFilters[state.currentCategory] || new Set(["", "fav"]);
        state.currentFilter = allowed.has(savedState.currentFilter) ? savedState.currentFilter : "";
        state.filterByCategory[state.currentCategory] = state.currentFilter;
    }
    state.currentPage = state.pageByCategory[state.currentCategory] || 1;
    if (!preserveState && Number(savedState.currentPage) > 0) {
        state.currentPage = Number(savedState.currentPage);
        state.pageByCategory[state.currentCategory] = state.currentPage;
    }
}

async function refreshCatalogDataAfterUpdate() {
    const [catalogResponse, updateConfigResponse, healthResponse] = await Promise.all([
        fetch("/api/catalog-meta"),
        fetch("/api/update-config"),
        fetch("/api/catalog-health"),
    ]);
    if (!catalogResponse.ok) throw new Error(`catalog HTTP ${catalogResponse.status}`);
    if (!updateConfigResponse.ok) throw new Error(`update-config HTTP ${updateConfigResponse.status}`);
    if (!healthResponse.ok) throw new Error(`health HTTP ${healthResponse.status}`);

    const data = await catalogResponse.json();
    const updateConfig = await updateConfigResponse.json();
    const health = await healthResponse.json();
    applyCatalogPayload(data, updateConfig, true);
    state.health = health;
    updateHealthBadge(health);
    renderCategoryOptions();
    renderUpdateButtons();
    syncScopedControls();
    applyFilter();
}

function initializeUI() {
    applyTheme();
    renderCategoryOptions();
    renderUpdateButtons();
    bindEvents();
    $("#search").value = state.searchQuery;
    syncSearchClear();
    setView(state.currentView);
    syncScopedControls();
    applyFilter();
    refreshHealthBadge();
    syncFavoriteSlideshowButton();
    scheduleFavoriteSlideshowAutoOpen();
    $("#loadingState").classList.add("hidden");
}

function renderCategoryOptions() {
    const select = $("#categorySelect");
    select.innerHTML = state.data.categories.map(category => {
        const count = category.count ?? category.products?.length ?? 0;
        return `<option value="${escapeHtml(category.id)}">全部 · ${escapeHtml(category.name)} (${count})</option>`;
    }).join("");
    select.value = state.currentCategory;
    renderCategoryMenu();
    syncCategoryPicker();

    const total = state.data.meta?.total_products ?? state.data.meta?.computed_total_products ?? 0;
    $("#metaLine").textContent = `数据来源: minigt.tsm-models.com · 新版架构验证 · 共 ${total} 款`;
}

function categoryDisplay(categoryId) {
    const category = state.data?.categories?.find(item => item.id === categoryId) || state.data?.categories?.[0];
    if (!category) return { name: "全部", count: 0 };
    return {
        name: category.name,
        count: category.count ?? category.products?.length ?? 0,
    };
}

function renderCategoryMenu() {
    const menu = $("#categoryMenu");
    if (!menu || !state.data) return;
    menu.innerHTML = state.data.categories.map(category => {
        const count = category.count ?? category.products?.length ?? 0;
        const selected = category.id === state.currentCategory;
        return `
            <button class="category-option${selected ? " selected" : ""}" type="button" role="option" aria-selected="${selected}" data-category="${escapeHtml(category.id)}">
                <span class="category-option-check">${selected ? "✓" : ""}</span>
                <span class="category-option-main">
                    <span class="category-option-name">全部 · ${escapeHtml(category.name)}</span>
                    <span class="category-option-count">${count} 款</span>
                </span>
            </button>
        `;
    }).join("");
}

function syncCategoryPicker() {
    const select = $("#categorySelect");
    const button = $("#categoryPickerButton");
    const picker = $("#categoryPicker");
    if (!button || !picker) return;
    const category = categoryDisplay(state.currentCategory);
    if (select) select.value = state.currentCategory;
    button.innerHTML = `
        <span class="category-picker-label">全部 · ${escapeHtml(category.name)} (${category.count})</span>
        <span class="category-picker-arrow" aria-hidden="true">⌄</span>
    `;
    button.setAttribute("aria-expanded", picker.classList.contains("open") ? "true" : "false");
    $("#categoryMenu")?.querySelectorAll(".category-option").forEach(option => {
        const selected = option.dataset.category === state.currentCategory;
        option.classList.toggle("selected", selected);
        option.setAttribute("aria-selected", selected ? "true" : "false");
        const check = option.querySelector(".category-option-check");
        if (check) check.textContent = selected ? "✓" : "";
    });
}

function closeCategoryPicker() {
    const picker = $("#categoryPicker");
    if (!picker) return;
    picker.classList.remove("open");
    $("#categoryPickerButton")?.setAttribute("aria-expanded", "false");
}

function closePageSizePickers() {
    document.querySelectorAll(".page-size-picker.open").forEach(picker => {
        picker.classList.remove("open");
        picker.querySelector("[data-page-size-toggle]")?.setAttribute("aria-expanded", "false");
    });
}

function toggleCategoryPicker() {
    const picker = $("#categoryPicker");
    if (!picker) return;
    picker.classList.toggle("open");
    syncCategoryPicker();
}

function updateButtonConfig(type) {
    return state.updateConfigs.find(config => config.id === type);
}

function renderUpdateButtons() {
    $("#updateActions").innerHTML = state.updateConfigs.map(config => `
        <button class="update-btn" data-update="${escapeHtml(config.id)}" data-scope="${escapeHtml(config.categoryId)}">${escapeHtml(config.label)}</button>
    `).join("");
}

function bindEvents() {
    $("#search").addEventListener("input", onSearchInput);
    $("#searchClearBtn").addEventListener("click", clearSearch);
    $("#categorySelect").addEventListener("change", event => switchCategory(event.target.value));
    $("#categoryPickerButton").addEventListener("click", event => {
        event.stopPropagation();
        toggleCategoryPicker();
    });
    $("#categoryMenu").addEventListener("click", event => {
        const option = event.target.closest("[data-category]");
        if (!option) return;
        closeCategoryPicker();
        switchCategory(option.dataset.category);
    });
    document.addEventListener("click", event => {
        if (!event.target.closest("#categoryPicker")) closeCategoryPicker();
        if (!event.target.closest(".page-size-picker")) closePageSizePickers();
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeCategoryPicker();
            closePageSizePickers();
        }
    });

    document.querySelectorAll(".status-filter, .fav-filter").forEach(button => {
        button.addEventListener("click", () => setFilter(button.dataset.filter || ""));
    });

    document.querySelectorAll(".view-btn").forEach(button => {
        button.addEventListener("click", () => setView(button.dataset.view));
    });

    $("#themeBtn").addEventListener("click", toggleTheme);
    $("#healthBtn").addEventListener("click", showCatalogHealth);
    $("#healthExportBtn").addEventListener("click", exportHealthIssues);
    $("#historyBtn").addEventListener("click", showUpdateHistory);
    $("#favoriteSlideshowBtn").addEventListener("click", () => openFavoriteSlideshow({ manual: true }));
    $("#statusPanel").addEventListener("click", handleStatusPanelClick);
    $("#updateActions").addEventListener("click", event => {
        const button = event.target.closest(".update-btn");
        if (button) triggerUpdate(button.dataset.update);
    });

    $("#cardsView").addEventListener("click", handleProductClick);
    $("#tableBody").addEventListener("click", handleProductClick);

    $("#modalClose").addEventListener("click", closeModal);
    $("#modalPrev").addEventListener("click", previousModalImage);
    $("#modalNext").addEventListener("click", nextModalImage);
    $("#modalOverlay").addEventListener("click", event => {
        if (event.target.id === "modalOverlay") closeModal();
    });
    $("#slideshowClose").addEventListener("click", closeFavoriteSlideshow);
    $("#slideshowPrev").addEventListener("click", () => showPreviousFavoriteSlide(true));
    $("#slideshowNext").addEventListener("click", () => showNextFavoriteSlide(true));
    $("#slideshowToggle").addEventListener("click", toggleFavoriteSlideshowPlayback);
    $("#favoriteSlideshowOverlay").addEventListener("click", event => {
        if (event.target.id === "favoriteSlideshowOverlay") closeFavoriteSlideshow();
    });
    document.addEventListener("keydown", handleKeydown);

    $("#backToTop").addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    window.addEventListener("scroll", () => {
        $("#backToTop").classList.toggle("visible", window.scrollY > 500);
    });
}

function onSearchInput() {
    clearTimeout(state.searchTimer);
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    if ($("#search").value.trim() && state.currentFilter && state.currentFilter !== "fav") {
        state.currentFilter = "";
        state.filterByCategory[state.currentCategory] = "";
        syncFilterButtons();
    }
    syncSearchClear();
    state.searchTimer = setTimeout(applyFilter, 180);
    saveUiState();
}

function clearSearch() {
    $("#search").value = "";
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    syncSearchClear();
    applyFilter();
    saveUiState();
    $("#search").focus();
}

function switchCategory(categoryId) {
    if (!categoryId || categoryId === state.currentCategory) return;
    state.filterByCategory[state.currentCategory] = state.currentFilter;
    state.pageByCategory[state.currentCategory] = state.currentPage;
    state.currentCategory = categoryId;
    if (state.healthIssueFilter && state.healthIssueFilter.categoryId !== categoryId) {
        state.healthIssueFilter = null;
    }
    const allowed = categoryScopedFilters[categoryId] || new Set(["", "fav"]);
    state.currentFilter = allowed.has(state.filterByCategory[categoryId]) ? state.filterByCategory[categoryId] : "";
    state.currentPage = state.pageByCategory[categoryId] || 1;
    syncCategoryPicker();
    syncScopedControls();
    applyFilter();
    saveUiState();
}

function setFilter(filter) {
    const allowed = categoryScopedFilters[state.currentCategory] || new Set(["", "fav"]);
    state.currentFilter = allowed.has(filter) ? filter : "";
    state.filterByCategory[state.currentCategory] = state.currentFilter;
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    syncFilterButtons();
    applyFilter();
    saveUiState();
}

function setView(view) {
    state.currentView = view === "table" ? "table" : "cards";
    document.querySelectorAll(".view-btn").forEach(button => button.classList.toggle("active", button.dataset.view === state.currentView));
    $("#cardsView").classList.toggle("hidden", state.currentView !== "cards");
    $("#tableView").classList.toggle("hidden", state.currentView !== "table");
    renderCurrentPage();
    saveUiState();
}

function syncScopedControls() {
    const allowed = categoryScopedFilters[state.currentCategory] || new Set(["", "fav"]);
    document.querySelectorAll(".status-filter").forEach(button => {
        button.classList.toggle("control-hidden", !allowed.has(button.dataset.filter));
    });
    document.querySelectorAll(".update-btn").forEach(button => {
        button.classList.toggle("control-hidden", button.dataset.scope !== state.currentCategory);
    });
    syncFilterButtons();
}

function syncFilterButtons() {
    document.querySelectorAll(".status-filter, .fav-filter").forEach(button => {
        button.classList.toggle("active", (button.dataset.filter || "") === state.currentFilter);
    });
    $("#categorySelect").classList.toggle("active", state.currentFilter === "");
}

function syncSearchClear() {
    $("#searchClearBtn").classList.toggle("visible", $("#search").value.length > 0);
}

function currentSourceProducts() {
    if (state.currentFilter === "fav") {
        return [...state.productsByCategory.values()].flat();
    }
    return state.productsByCategory.get(state.currentCategory) || [];
}

async function applyFilter() {
    const query = $("#search").value.trim().toLowerCase();
    state.searchQuery = query;
    const requestToken = ++state.productRequestToken;
    const healthKeys = state.healthIssueFilter?.categoryId === state.currentCategory
        ? [...state.healthIssueFilter.keys]
        : [];
    const params = new URLSearchParams({
        category: state.currentCategory,
        q: query,
        filter: state.currentFilter,
        page: String(state.currentPage),
        pageSize: String(state.pageSize),
    });
    if (state.currentFilter === "fav") {
        params.set("favorites", [...state.favorites].join(","));
    }
    if (healthKeys.length) {
        params.set("healthKeys", healthKeys.join(","));
    }

    const response = await fetch(`/api/products?${params.toString()}`);
    if (!response.ok) throw new Error(`products HTTP ${response.status}`);
    const pageData = await response.json();
    if (requestToken !== state.productRequestToken) return;

    state.filteredProducts = pageData.products || [];
    state.currentPageProductsList = state.filteredProducts;
    state.filteredTotal = pageData.total || 0;
    state.categoryTotal = pageData.categoryTotal || 0;
    state.pageStats = pageData.stats || { "Released": 0, "Pre-Order": 0, "Sold Out": 0 };
    state.currentPage = pageData.page || state.currentPage;

    const totalPages = totalPagesForCurrentFilter();
    state.currentPage = Math.max(1, Math.min(state.currentPage, totalPages));
    state.pageByCategory[state.currentCategory] = state.currentPage;
    updateStats();
    renderPagination();
    renderCurrentPage();
    saveUiState();
}

function updateStats() {
    const category = getCategory();
    const totalForCategory = state.categoryTotal || category?.count || category?.products?.length || 0;
    const counts = state.pageStats || { "Released": 0, "Pre-Order": 0, "Sold Out": 0 };
    $("#statsGroup").innerHTML = `
        <span class="stat-badge">显示 ${state.filteredTotal} / 共 ${totalForCategory}</span>
        ${state.healthIssueFilter?.categoryId === state.currentCategory ? '<span class="stat-badge health-active">🩺 问题产品</span>' : ''}
        <span class="stat-badge released">✅ ${counts["Released"]}</span>
        <span class="stat-badge preorder">📦 ${counts["Pre-Order"]}</span>
        <span class="stat-badge soldout">❌ ${counts["Sold Out"]}</span>
    `;
}

function totalPagesForCurrentFilter() {
    return Math.max(1, Math.ceil(state.filteredTotal / state.pageSize));
}

function currentPageProducts() {
    return state.currentPageProductsList;
}

function renderPagination() {
    const totalPages = totalPagesForCurrentFilter();
    const pageSizeOptions = [20, 50, 100].map(size => `
        <button class="page-size-option${state.pageSize === size ? " selected" : ""}" type="button" data-page-size="${size}" aria-selected="${state.pageSize === size}">
            <span>${size}/页</span>
            <span class="page-size-check">${state.pageSize === size ? "✓" : ""}</span>
        </button>
    `).join("");
    const html = `
        <button data-page="first" ${state.currentPage === 1 ? "disabled" : ""}>首页</button>
        <button data-page="prev" ${state.currentPage === 1 ? "disabled" : ""}>上一页</button>
        <span class="page-info">第 ${state.currentPage} 页 / 共 ${totalPages} 页</span>
        <label>跳至 <input class="page-jump-input" type="number" min="1" max="${totalPages}" value="${state.currentPage}" ${totalPages <= 1 ? "disabled" : ""}> 页</label>
        <button data-page="jump" ${totalPages <= 1 ? "disabled" : ""}>跳转</button>
        <button data-page="next" ${state.currentPage === totalPages ? "disabled" : ""}>下一页</button>
        <button data-page="last" ${state.currentPage === totalPages ? "disabled" : ""}>末页</button>
        <div class="page-size-picker">
            <select class="page-size page-size-native" aria-label="每页数量" tabindex="-1">
                <option value="20" ${state.pageSize === 20 ? "selected" : ""}>20/页</option>
                <option value="50" ${state.pageSize === 50 ? "selected" : ""}>50/页</option>
                <option value="100" ${state.pageSize === 100 ? "selected" : ""}>100/页</option>
            </select>
            <button class="page-size-button" type="button" data-page-size-toggle aria-haspopup="listbox" aria-expanded="false">
                <span>${state.pageSize}/页</span>
                <span class="page-size-arrow" aria-hidden="true">⌄</span>
            </button>
            <div class="page-size-menu" role="listbox" aria-label="每页数量">
                ${pageSizeOptions}
            </div>
        </div>
        <noscript><select class="page-size" aria-label="每页数量">
            <option value="20" ${state.pageSize === 20 ? "selected" : ""}>20/页</option>
            <option value="50" ${state.pageSize === 50 ? "selected" : ""}>50/页</option>
            <option value="100" ${state.pageSize === 100 ? "selected" : ""}>100/页</option>
        </select></noscript>
    `;
    document.querySelectorAll(".pagination").forEach(nav => {
        nav.innerHTML = html;
        nav.onclick = handlePaginationClick;
        nav.onchange = handlePaginationChange;
        nav.onkeydown = handlePaginationKeydown;
    });
}

function handlePaginationClick(event) {
    const pageSizeToggle = event.target.closest("[data-page-size-toggle]");
    if (pageSizeToggle) {
        const picker = pageSizeToggle.closest(".page-size-picker");
        const open = !picker.classList.contains("open");
        document.querySelectorAll(".page-size-picker.open").forEach(item => {
            if (item !== picker) {
                item.classList.remove("open");
                item.querySelector("[data-page-size-toggle]")?.setAttribute("aria-expanded", "false");
            }
        });
        picker.classList.toggle("open", open);
        pageSizeToggle.setAttribute("aria-expanded", open ? "true" : "false");
        return;
    }

    const pageSizeOption = event.target.closest("[data-page-size]");
    if (pageSizeOption) {
        const nextPageSize = parseInt(pageSizeOption.dataset.pageSize, 10) || 20;
        setPageSize(nextPageSize);
        return;
    }

    const action = event.target.closest("button")?.dataset.page;
    if (!action) return;
    const totalPages = totalPagesForCurrentFilter();
    if (action === "first") state.currentPage = 1;
    if (action === "prev") state.currentPage -= 1;
    if (action === "next") state.currentPage += 1;
    if (action === "last") state.currentPage = totalPages;
    if (action === "jump") {
        const input = event.currentTarget.querySelector(".page-jump-input");
        state.currentPage = clampPage(input.value);
    }
    state.currentPage = Math.max(1, Math.min(state.currentPage, totalPages));
    state.pageByCategory[state.currentCategory] = state.currentPage;
    applyFilter();
    window.scrollTo({ top: 0, behavior: "smooth" });
    saveUiState();
}

function setPageSize(pageSize) {
    if (![20, 50, 100].includes(pageSize)) return;
    state.pageSize = pageSize;
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    document.querySelectorAll(".page-size-picker.open").forEach(item => item.classList.remove("open"));
    applyFilter();
    saveUiState();
}

function handlePaginationChange(event) {
    if (event.target.classList.contains("page-size")) {
        setPageSize(parseInt(event.target.value, 10) || 20);
    }
    if (event.target.classList.contains("page-jump-input")) {
        event.target.value = clampPage(event.target.value);
    }
}

function handlePaginationKeydown(event) {
    if (!event.target.classList.contains("page-jump-input")) return;
    if (event.key === "Enter") {
        state.currentPage = clampPage(event.target.value);
        state.pageByCategory[state.currentCategory] = state.currentPage;
        applyFilter();
        window.scrollTo({ top: 0, behavior: "smooth" });
        saveUiState();
    }
    if (event.key === "Escape") {
        event.target.value = state.currentPage;
        event.target.blur();
    }
}

function clampPage(value) {
    const totalPages = totalPagesForCurrentFilter();
    const page = parseInt(value, 10);
    if (!Number.isFinite(page)) return state.currentPage;
    return Math.max(1, Math.min(page, totalPages));
}

function renderCurrentPage() {
    const products = currentPageProducts();
    if (state.currentView === "cards") {
        $("#cardsView").innerHTML = products.map(renderCard).join("");
    } else {
        $("#tableBody").innerHTML = products.map(renderTableRow).join("");
    }
    scheduleCurrentPageImagePreload(products);
}

function renderCard(product, pageIndex = 0) {
    const images = rawImages(product, "card");
    const firstImage = imageForDisplay(images[0], product.categoryId, "card");
    const favActive = state.favorites.has(product.sku);
    const favoriteFeedback = product.sku === state.lastFavoriteSku ? " fav-pop" : "";
    return `
        <article class="card-item" data-sku="${escapeHtml(product.sku)}" data-index="${product.index}" style="--item-index: ${pageIndex % 24}">
            <div class="card-img" data-open-image="${product.index}">
                <img src="${escapeHtml(firstImage)}" alt="${escapeHtml(product.name)}" loading="lazy" onerror="this.src='${PLACEHOLDER_IMAGE}'">
                <span class="card-img-count">${images.length} 图</span>
            </div>
            <div class="card-info">
                <div class="sku" data-copy="${escapeHtml(product.sku)}">${escapeHtml(product.sku)}</div>
                <a class="card-name" href="${escapeHtml(productUrl(product))}" target="_blank" rel="noopener">${escapeHtml(product.name)}</a>
                <div class="card-footer">
                    <span class="status ${statusClass(product.status)}">${escapeHtml(product.status || "Released")}</span>
                    <button class="fav-btn ${favActive ? "active" : ""}${favoriteFeedback}" data-fav="${escapeHtml(product.sku)}" title="收藏">${favActive ? "⭐" : "☆"}</button>
                </div>
            </div>
        </article>
    `;
}

function renderTableRow(product) {
    const images = rawImages(product, "card");
    const firstImage = imageForDisplay(images[0], product.categoryId, "card");
    const favActive = state.favorites.has(product.sku);
    const favoriteFeedback = product.sku === state.lastFavoriteSku ? " fav-pop" : "";
    return `
        <tr data-sku="${escapeHtml(product.sku)}" data-index="${product.index}">
            <td>${product.index}</td>
            <td><span class="sku" data-copy="${escapeHtml(product.sku)}">${escapeHtml(product.sku)}</span></td>
            <td><a class="card-name" href="${escapeHtml(productUrl(product))}" target="_blank" rel="noopener">${escapeHtml(product.name)}</a></td>
            <td><span class="status ${statusClass(product.status)}">${escapeHtml(product.status || "Released")}</span></td>
            <td><div class="table-images"><img class="thumb-img" src="${escapeHtml(firstImage)}" alt="${escapeHtml(product.name)}" data-open-image="${product.index}" onerror="this.src='${PLACEHOLDER_IMAGE}'"><span>${images.length} 图</span></div></td>
            <td><button class="fav-btn ${favActive ? "active" : ""}${favoriteFeedback}" data-fav="${escapeHtml(product.sku)}" title="收藏">${favActive ? "⭐" : "☆"}</button></td>
        </tr>
    `;
}

function productByIndex(index) {
    const currentProduct = state.currentPageProductsList.find(item => item.index === index);
    if (currentProduct) return currentProduct;
    for (const products of state.productsByCategory.values()) {
        const product = products.find(item => item.index === index);
        if (product) return product;
    }
    return null;
}

function handleProductClick(event) {
    const imageTarget = event.target.closest("[data-open-image]");
    if (imageTarget) {
        const product = productByIndex(parseInt(imageTarget.dataset.openImage, 10));
        if (product) openModal(product, 0);
        return;
    }

    const favoriteTarget = event.target.closest("[data-fav]");
    if (favoriteTarget) {
        toggleFavorite(favoriteTarget.dataset.fav);
        return;
    }

    const copyTarget = event.target.closest("[data-copy]");
    if (copyTarget) {
        copyToClipboard(copyTarget.dataset.copy);
    }
}

function toggleFavorite(sku) {
    if (!sku) return;
    state.lastFavoriteSku = sku;
    if (state.favorites.has(sku)) {
        state.favorites.delete(sku);
        showToast("已取消收藏");
    } else {
        state.favorites.add(sku);
        showToast("已收藏");
    }
    saveFavorites();
    syncFavoriteSlideshowButton();
    applyFilter();
    setTimeout(() => {
        if (state.lastFavoriteSku === sku) state.lastFavoriteSku = "";
    }, 360);
}

function syncFavoriteSlideshowButton() {
    const button = $("#favoriteSlideshowBtn");
    if (!button) return;
    const count = state.favorites.size;
    button.disabled = count === 0;
    button.classList.toggle("control-hidden", count === 0);
    button.title = count ? `播放 ${count} 个收藏产品` : "暂无收藏产品";
}

function scheduleFavoriteSlideshowAutoOpen() {
    if (!state.favorites.size) return;
    if (sessionStorage.getItem(FAVORITE_SLIDESHOW_DISMISSED_KEY) === "1") return;
    setTimeout(() => openFavoriteSlideshow({ manual: false }), 650);
}

async function fetchFavoriteSlideshowItems() {
    const skus = favoriteSkus();
    if (!skus.length) return [];
    const response = await fetch("/api/favorites-slideshow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skus }),
    });
    if (!response.ok) throw new Error(`favorites slideshow HTTP ${response.status}`);
    const data = await response.json();
    return (data.products || []).map(item => {
        const src = item.image || item.images?.[0] || PLACEHOLDER_IMAGE;
        return {
            ...item,
            displayImage: imageForDisplay(src, item.categoryId, "modal"),
        };
    }).filter(item => item.displayImage && item.displayImage !== PLACEHOLDER_IMAGE);
}

async function openFavoriteSlideshow({ manual = false } = {}) {
    if (!state.favorites.size) {
        if (manual) showToast("暂无收藏产品");
        return;
    }
    if (!manual && sessionStorage.getItem(FAVORITE_SLIDESHOW_DISMISSED_KEY) === "1") return;

    try {
        const items = await fetchFavoriteSlideshowItems();
        if (!items.length) {
            if (manual) showToast("收藏产品暂无可播放图片");
            return;
        }
        state.slideshowItems = items;
        state.slideshowIndex = 0;
        state.slideshowPlaying = true;
        state.slideshowFailedUrls = new Set();
        $("#favoriteSlideshowOverlay").classList.add("active");
        document.body.style.overflow = "hidden";
        preloadFavoriteSlideshowImages();
        updateFavoriteSlide(true);
        startFavoriteSlideshowTimer();
    } catch (error) {
        console.error(error);
        if (manual) showStatusPanel("⚠️ 无法读取收藏轮播数据", "error", 4000);
    }
}

function favoriteSlideshowActive() {
    return $("#favoriteSlideshowOverlay")?.classList.contains("active");
}

function startFavoriteSlideshowTimer() {
    stopFavoriteSlideshowTimer();
    if (!state.slideshowPlaying || state.slideshowItems.length <= 1) return;
    state.slideshowTimer = setInterval(() => showNextFavoriteSlide(false), FAVORITE_SLIDESHOW_INTERVAL);
}

function stopFavoriteSlideshowTimer() {
    clearInterval(state.slideshowTimer);
    state.slideshowTimer = null;
}

function preloadFavoriteSlideshowImages() {
    const urls = state.slideshowItems.map(item => item.displayImage);
    const current = urls[state.slideshowIndex];
    const next = urls[(state.slideshowIndex + 1) % urls.length];
    uniqueUrls([current, next]).forEach(src => preloadImage(src, "high").catch(() => {}));
    preloadInBatches(urls, { firstBatch: 4, batchSize: 6 });
}

function setFavoriteSlideIndex(index) {
    const total = state.slideshowItems.length;
    if (!total) return;
    let nextIndex = (index + total) % total;
    for (let attempts = 0; attempts < total; attempts += 1) {
        const item = state.slideshowItems[nextIndex];
        if (!state.slideshowFailedUrls.has(item.displayImage)) break;
        nextIndex = (nextIndex + (index >= state.slideshowIndex ? 1 : -1) + total) % total;
    }
    state.slideshowIndex = nextIndex;
    updateFavoriteSlide();
    if (state.slideshowPlaying) startFavoriteSlideshowTimer();
}

function showNextFavoriteSlide(userAction = false) {
    setFavoriteSlideIndex(state.slideshowIndex + 1);
    if (userAction) showToast("下一张收藏图");
}

function showPreviousFavoriteSlide(userAction = false) {
    setFavoriteSlideIndex(state.slideshowIndex - 1);
    if (userAction) showToast("上一张收藏图");
}

function updateFavoriteSlide(forceBlank = false) {
    const item = state.slideshowItems[state.slideshowIndex];
    if (!item) return;

    const overlay = $("#favoriteSlideshowOverlay");
    const img = $("#slideshowImg");
    const token = ++state.slideshowToken;
    overlay.classList.remove("loading");
    img.classList.add("switching-out");
    if (forceBlank) img.style.opacity = "0";

    $("#slideshowSku").textContent = item.sku || "";
    $("#slideshowName").textContent = item.name || "收藏产品";
    $("#slideshowStatus").textContent = item.status || "Released";
    $("#slideshowStatus").className = `slideshow-status ${statusClass(item.status)}`;
    $("#slideshowCounter").textContent = `${state.slideshowIndex + 1} / ${state.slideshowItems.length}`;
    $("#slideshowToggle").textContent = state.slideshowPlaying ? "⏸ 暂停" : "▶ 播放";

    preloadImage(item.displayImage, "high").then(() => {
        if (token !== state.slideshowToken) return;
        setTimeout(() => {
            if (token !== state.slideshowToken) return;
            img.src = item.displayImage;
            img.alt = item.name || item.sku || "收藏产品";
            img.style.opacity = "1";
            img.classList.remove("switching-out");
            img.classList.add("zoom-in");
            requestAnimationFrame(() => {
                requestAnimationFrame(() => img.classList.remove("zoom-in"));
            });
            preloadFavoriteSlideshowImages();
        }, 150);
    }).catch(() => {
        if (token !== state.slideshowToken) return;
        state.slideshowFailedUrls.add(item.displayImage);
        overlay.classList.remove("loading");
        const available = state.slideshowItems.some(slide => !state.slideshowFailedUrls.has(slide.displayImage));
        if (available) {
            showNextFavoriteSlide(false);
        } else {
            img.src = PLACEHOLDER_IMAGE;
            img.alt = "收藏产品图片加载失败";
            img.style.opacity = "1";
            img.classList.remove("switching-out", "switching-in");
            $("#slideshowName").textContent = "收藏产品图片加载失败";
            stopFavoriteSlideshowTimer();
        }
    });
}

function toggleFavoriteSlideshowPlayback() {
    state.slideshowPlaying = !state.slideshowPlaying;
    $("#slideshowToggle").textContent = state.slideshowPlaying ? "⏸ 暂停" : "▶ 播放";
    if (state.slideshowPlaying) {
        startFavoriteSlideshowTimer();
    } else {
        stopFavoriteSlideshowTimer();
    }
}

function closeFavoriteSlideshow() {
    sessionStorage.setItem(FAVORITE_SLIDESHOW_DISMISSED_KEY, "1");
    stopFavoriteSlideshowTimer();
    $("#favoriteSlideshowOverlay").classList.remove("active", "loading");
    document.body.style.overflow = $("#modalOverlay").classList.contains("active") ? "hidden" : "";
}

function copyToClipboard(text) {
    navigator.clipboard?.writeText(text).then(
        () => showToast(`已复制: ${text}`),
        () => {
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            textarea.remove();
            showToast(`已复制: ${text}`);
        },
    );
}

function openModal(product, index) {
    state.modalImages = modalImages(product);
    state.modalIndex = Math.max(0, Math.min(index, state.modalImages.length - 1));
    state.modalName = product.name || "产品图片";
    $("#modalOverlay").classList.add("active");
    document.body.style.overflow = "hidden";
    preloadModalImages();
    updateModalImage(true);
}

function preloadModalImages() {
    const total = state.modalImages.length;
    if (!total) return;

    const current = state.modalImages[state.modalIndex];
    const next = state.modalImages[(state.modalIndex + 1) % total];
    const prev = state.modalImages[(state.modalIndex - 1 + total) % total];
    uniqueUrls([current, next, prev]).forEach(src => preloadImage(src, "high").catch(() => {}));

    const remaining = state.modalImages.filter(src => ![current, next, prev].includes(src));
    preloadInBatches(remaining, { firstBatch: 0, batchSize: 4 });
}

function updateModalImage(forceBlank = false) {
    const src = state.modalImages[state.modalIndex];
    const img = $("#modalImg");
    const content = img.closest(".modal-content");
    const token = ++state.modalToken;
    if (!src) return;

    content.classList.add("loading");
    $("#modalCaption").textContent = state.modalName;
    $("#modalCounter").textContent = `${state.modalIndex + 1} / ${state.modalImages.length}`;
    if (forceBlank) img.style.opacity = "0";

    preloadImage(src, "high").then(() => {
        if (token !== state.modalToken) return;
        img.src = src;
        img.alt = state.modalName;
        img.style.opacity = "1";
        content.classList.remove("loading");
        preloadModalImages();
    }).catch(() => {
        if (token !== state.modalToken) return;
        img.src = PLACEHOLDER_IMAGE;
        img.alt = "图片加载失败";
        img.style.opacity = "1";
        $("#modalCaption").textContent = "图片加载失败";
        content.classList.remove("loading");
    });
}

function previousModalImage() {
    if (!state.modalImages.length) return;
    state.modalIndex = (state.modalIndex - 1 + state.modalImages.length) % state.modalImages.length;
    updateModalImage();
}

function nextModalImage() {
    if (!state.modalImages.length) return;
    state.modalIndex = (state.modalIndex + 1) % state.modalImages.length;
    updateModalImage();
}

function closeModal() {
    $("#modalOverlay").classList.remove("active");
    document.body.style.overflow = "";
}

function handleKeydown(event) {
    if (favoriteSlideshowActive()) {
        if (event.key === "Escape") closeFavoriteSlideshow();
        if (event.key === "ArrowLeft") showPreviousFavoriteSlide(true);
        if (event.key === "ArrowRight") showNextFavoriteSlide(true);
        if (event.key === " " || event.key === "Spacebar") {
            event.preventDefault();
            toggleFavoriteSlideshowPlayback();
        }
        return;
    }
    if (!$("#modalOverlay").classList.contains("active")) return;
    if (event.key === "Escape") closeModal();
    if (event.key === "ArrowLeft") previousModalImage();
    if (event.key === "ArrowRight") nextModalImage();
}

function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 1600);
}

function applyTheme() {
    const storedTheme = localStorage.getItem(THEME_KEY);
    const dark = storedTheme === "dark"
        || (storedTheme !== "light" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
    document.body.classList.toggle("dark", dark);
    $("#themeBtn").textContent = dark ? "☀️" : "🌙";
}

function toggleTheme() {
    document.body.classList.toggle("dark");
    const dark = document.body.classList.contains("dark");
    $("#themeBtn").textContent = dark ? "☀️" : "🌙";
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
}

function watchSystemTheme() {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!media) return;
    media.addEventListener("change", () => {
        if (!localStorage.getItem(THEME_KEY)) applyTheme();
    });
}

function formatIssueLine(label, count, examples = []) {
    if (!count) return "";
    const sample = examples.length ? `，样本：${examples.slice(0, 8).join("、")}` : "";
    return `${label}：${count}${sample}`;
}

function issueGroups(category) {
    return [
        ["重复唯一键", category.duplicateKeyCount, category.examples?.duplicateKeys || []],
        ["缺唯一键", category.missingKeyCount, category.examples?.missingKeys || []],
        ["缺 SKU", category.missingSkuCount, category.examples?.missingSkus || []],
        ["缺名称", category.missingNameCount, category.examples?.missingNames || []],
        ["缺图", category.missingImageCount, category.examples?.missingImages || []],
        ["异常状态", category.invalidStatusCount, category.examples?.invalidStatuses || []],
        ["图片超限", category.overImageLimitCount, category.examples?.overImageLimit || []],
    ].filter(([, count]) => count > 0);
}

function healthSampleButtons(category, examples = []) {
    return examples.slice(0, 8).map(example => `
        <button class="health-chip" type="button" data-health-locate="${escapeHtml(category.id)}" data-health-query="${escapeHtml(example)}">${escapeHtml(example)}</button>
    `).join("");
}

function healthIssueFilterButton(category) {
    if (!category.issueKeys?.length) return "";
    return `
        <button class="health-filter-btn" type="button" data-health-filter="${escapeHtml(category.id)}">
            只看问题产品（${escapeHtml(category.issueKeys.length)}）
        </button>
    `;
}

function healthMetric(label, value, tone = "") {
    return `
        <div class="health-metric${tone ? ` ${tone}` : ""}">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
        </div>
    `;
}

function formatHealthSummaryText(health) {
    const totalLine = health.totalOk
        ? `总数正常：${health.metaTotal} / ${health.computedTotal}`
        : `总数异常：meta ${health.metaTotal}，实际 ${health.computedTotal}`;
    const categoryLines = (health.categories || [])
        .filter(category => category.issueCount > 0)
        .map(category => {
            const lines = issueGroups(category).map(([label, count, examples]) => formatIssueLine(label, count, examples));
            return `- ${category.name || category.id}：${category.issueCount} 个问题\n  ${lines.join("\n  ")}`;
        })
        .filter(Boolean);

    if (health.ok) {
        return `✅ 数据健康检查通过\n${totalLine}\n分类数量：${health.categoryCount}`;
    }

    return [
        "⚠️ 数据健康检查发现问题",
        totalLine,
        `问题总数：${health.issueCount}`,
        `分类数量：${health.categoryCount}`,
        "",
        ...categoryLines,
    ].join("\n");
}

function formatHealthSummaryHtml(health) {
    const totalLine = health.totalOk
        ? `总数正常：${health.metaTotal} / ${health.computedTotal}`
        : `总数异常：meta ${health.metaTotal}，实际 ${health.computedTotal}`;
    const categories = (health.categories || []).filter(category => category.issueCount > 0);
    const statusText = health.ok ? "数据健康检查通过" : "数据健康检查发现问题";
    const statusIcon = health.ok ? "✅" : "⚠️";
    const metrics = [
        healthMetric("总数", `${health.metaTotal} / ${health.computedTotal}`, health.totalOk ? "success" : "warning"),
        healthMetric("问题总数", health.issueCount, health.ok ? "success" : "warning"),
        healthMetric("分类数量", health.categoryCount),
    ].join("");

    if (health.ok) {
        return `
            <div class="health-summary">
                <div class="health-head">
                    <div class="health-title">${statusIcon} ${escapeHtml(statusText)}</div>
                    <div class="health-subtitle">${escapeHtml(totalLine)}</div>
                </div>
                <div class="health-metrics">${metrics}</div>
            </div>
        `;
    }

    const categoryHtml = categories.map(category => {
        const lines = issueGroups(category).map(([label, count, examples]) => `
            <div class="health-issue-line">
                <div class="health-issue-main">
                    <span class="health-issue-label">${escapeHtml(label)}</span>
                    <strong>${escapeHtml(count)}</strong>
                </div>
                ${examples.length ? `<div class="health-chip-list">${healthSampleButtons(category, examples)}</div>` : ""}
            </div>
        `).join("");
        const reasonLines = Object.entries(category.missingImageReasons || {}).map(([reason, detail]) => `
            <div class="health-issue-line">
                <div class="health-issue-main">
                    <span class="health-issue-label">缺图原因：${escapeHtml(reason)}</span>
                    <strong>${escapeHtml(detail.count)}</strong>
                </div>
                ${detail.examples?.length ? `<div class="health-chip-list">${healthSampleButtons(category, detail.examples)}</div>` : ""}
            </div>
        `).join("");
        return `
            <div class="health-category">
                <div class="health-category-head">
                    <strong>${escapeHtml(category.name || category.id)}</strong>
                    <span>${escapeHtml(category.issueCount)} 个问题</span>
                </div>
                ${lines}
                ${reasonLines}
                ${healthIssueFilterButton(category)}
            </div>
        `;
    }).join("");

    return `
        <div class="health-summary">
            <div class="health-head">
                <div class="health-title">${statusIcon} ${escapeHtml(statusText)}</div>
                <div class="health-subtitle">${escapeHtml(totalLine)}</div>
            </div>
            <div class="health-metrics">${metrics}</div>
            ${categoryHtml}
        </div>
    `;
}

function updateHealthBadge(health) {
    const badge = $("#healthBadge");
    if (!badge) return;
    const count = Number(health?.issueCount || 0);
    badge.textContent = count ? String(count) : "";
    badge.classList.toggle("hidden", count === 0);
    $("#healthBtn").title = count ? `数据健康：${count} 个问题` : "数据健康：无问题";
}

function refreshHealthBadge() {
    fetch("/api/catalog-health")
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(health => {
            state.health = health;
            updateHealthBadge(health);
        })
        .catch(error => {
            console.warn("数据健康角标加载失败", error);
        });
}

function showCatalogHealth() {
    showStatusPanel("正在检查数据健康...");
    fetch("/api/catalog-health")
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(health => {
            state.health = health;
            updateHealthBadge(health);
            showStatusHtmlPanel(formatHealthSummaryHtml(health), health.ok ? "success" : "warning");
        })
        .catch(error => {
            console.error(error);
            showStatusPanel("⚠️ 无法读取数据健康结果，请确认本地服务器正在运行", "error");
        });
}

function exportHealthIssues() {
    window.location.href = "/api/catalog-health.csv";
}

function formatHistorySummary(summary = {}) {
    const parts = [];
    if (summary.fetched_count !== undefined) parts.push(`抓取 ${summary.fetched_count}`);
    if (summary.added_count !== undefined) parts.push(`新增 ${summary.added_count}`);
    if (summary.updated_count !== undefined) parts.push(`更新 ${summary.updated_count}`);
    if (summary.preserved_count !== undefined) parts.push(`保留 ${summary.preserved_count}`);
    if (summary.missing_image_count !== undefined) parts.push(`缺图 ${summary.missing_image_count}`);
    if (summary.total_products !== undefined) parts.push(`总数 ${summary.total_products}`);
    return parts.join("，") || "无结构化摘要";
}

function formatUpdateHistoryHtml(history) {
    if (!history.length) {
        return `
            <div class="health-summary">
                <div class="health-title">🕘 更新历史</div>
                <div>暂无更新记录。</div>
                <div class="health-subtitle">此提示将在 8 秒后自动关闭。</div>
            </div>
        `;
    }

    const rows = history.map(item => `
        <div class="history-item ${item.status === "failed" ? "failed" : ""}">
            <strong>${escapeHtml(item.status === "failed" ? "❌" : "✅")} ${escapeHtml(item.brandName || item.brandId || "未知品牌")}</strong>
            <div>${escapeHtml(item.startedAt || "")} → ${escapeHtml(item.endedAt || "")}</div>
            <div>${escapeHtml(formatHistorySummary(item.summary || {}))}</div>
            ${item.error ? `<div>错误：${escapeHtml(item.error)}</div>` : ""}
        </div>
    `).join("");

    return `
        <div class="health-summary">
            <div class="health-title">🕘 最近更新历史</div>
            ${rows}
            <div class="health-subtitle">此提示将在 8 秒后自动关闭。</div>
        </div>
    `;
}

function showUpdateHistory() {
    showStatusPanel("正在读取更新历史...", "", 4000);
    fetch("/api/update-history?limit=10")
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            showStatusHtmlPanel(formatUpdateHistoryHtml(data.history || []), "success", 8000);
        })
        .catch(error => {
            console.error(error);
            showStatusPanel("⚠️ 无法读取更新历史", "error", 4000);
        });
}

function locateHealthIssue(categoryId, query) {
    if (!categoryId || !query) return;
    if (categoryId !== state.currentCategory) {
        switchCategory(categoryId);
    }
    $("#search").value = query;
    state.currentFilter = "";
    state.filterByCategory[state.currentCategory] = "";
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    syncSearchClear();
    syncFilterButtons();
    applyFilter();
    saveUiState();
    document.querySelector(".pagination-top")?.scrollIntoView({ behavior: "smooth", block: "start" });
    showToast(`已定位: ${query}`);
}

function showHealthIssueProducts(categoryId) {
    const category = state.health?.categories?.find(item => item.id === categoryId);
    if (!category?.issueKeys?.length) return;
    if (categoryId !== state.currentCategory) {
        switchCategory(categoryId);
    }
    state.healthIssueFilter = {
        categoryId,
        keys: new Set(category.issueKeys.map(String)),
    };
    $("#search").value = "";
    state.currentFilter = "";
    state.filterByCategory[state.currentCategory] = "";
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    syncSearchClear();
    syncFilterButtons();
    applyFilter();
    saveUiState();
    document.querySelector(".pagination-top")?.scrollIntoView({ behavior: "smooth", block: "start" });
    showToast(`已筛选 ${category.name || categoryId} 问题产品`);
}

function handleStatusPanelClick(event) {
    const locateButton = event.target.closest("[data-health-locate]");
    if (locateButton) {
        locateHealthIssue(locateButton.dataset.healthLocate, locateButton.dataset.healthQuery);
        return;
    }

    const filterButton = event.target.closest("[data-health-filter]");
    if (filterButton) {
        showHealthIssueProducts(filterButton.dataset.healthFilter);
    }
}

function closeStatusPanel() {
    clearTimeout(state.statusAutoCloseTimer);
    state.statusAutoCloseTimer = null;
    const panel = $("#statusPanel");
    panel.className = "status-panel";
    panel.innerHTML = "";
    panel.setAttribute("aria-hidden", "true");
}

function scheduleStatusPanelAutoClose(autoCloseMs = 0) {
    clearTimeout(state.statusAutoCloseTimer);
    state.statusAutoCloseTimer = null;
    if (!autoCloseMs) return;
    state.statusAutoCloseTimer = setTimeout(closeStatusPanel, autoCloseMs);
}

function showStatusPanel(message, stateName = "", autoCloseMs = 0) {
    const panel = $("#statusPanel");
    panel.className = `status-panel visible${stateName ? ` ${stateName}` : ""}`;
    panel.innerHTML = `<div class="status-panel-content">${escapeHtml(message)}</div><button class="status-close" type="button" aria-label="关闭">×</button>`;
    panel.setAttribute("aria-hidden", "false");
    panel.querySelector(".status-close").onclick = closeStatusPanel;
    scheduleStatusPanelAutoClose(autoCloseMs);
}

function showStatusHtmlPanel(html, stateName = "", autoCloseMs = 0) {
    const panel = $("#statusPanel");
    panel.className = `status-panel visible${stateName ? ` ${stateName}` : ""}`;
    panel.innerHTML = `<div class="status-panel-content">${html}</div><button class="status-close" type="button" aria-label="关闭">×</button>`;
    panel.setAttribute("aria-hidden", "false");
    panel.querySelector(".status-close").onclick = closeStatusPanel;
    scheduleStatusPanelAutoClose(autoCloseMs);
}

function updateProgressFromMessage(message = "") {
    const match = String(message).match(/(\d+)\s*\/\s*(\d+)/);
    if (!match) {
        return {
            current: 0,
            total: 0,
            percent: 36,
            indeterminate: true,
        };
    }
    const current = Number(match[1]);
    const total = Math.max(1, Number(match[2]));
    return {
        current,
        total,
        percent: Math.max(8, Math.min(100, Math.round((current / total) * 100))),
        indeterminate: false,
    };
}

function updateProgressTitle() {
    const config = updateButtonConfig(state.activeUpdateType);
    if (!config) return "产品更新中";
    return config.runningText || `${config.label.replace(/^更新\s*/, "")}更新中...`;
}

function showUpdateProgressPanel(message = "正在更新中...", status = null) {
    const progress = status?.totalSteps
        ? {
            current: status.step || 0,
            total: status.totalSteps,
            percent: Math.max(8, Math.min(100, status.progress || 0)),
            indeterminate: false,
        }
        : updateProgressFromMessage(message);
    const progressText = progress.total ? `${progress.current} / ${progress.total}` : "正在准备";
    const progressClass = progress.indeterminate ? " indeterminate" : "";
    const stepText = status?.stepLabel || message;
    showStatusHtmlPanel(`
        <div class="update-progress-card">
            <div class="update-progress-head">
                <span class="update-progress-icon" aria-hidden="true">⏳</span>
                <div>
                    <div class="update-progress-title">${escapeHtml(updateProgressTitle())}</div>
                    <div class="update-progress-step">${escapeHtml(stepText)}</div>
                </div>
                <strong>${escapeHtml(progressText)}</strong>
            </div>
            <div class="update-progress-track${progressClass}" aria-label="更新进度">
                <span style="width: ${progress.percent}%"></span>
            </div>
            <div class="update-progress-note">更新期间可以继续浏览当前数据，完成后页面会自动刷新。</div>
        </div>
    `, "updating");
}

function setUpdateButtonsDisabled(disabled, activeType = "") {
    document.querySelectorAll(".update-btn").forEach(button => {
        button.disabled = disabled;
        const type = button.dataset.update;
        const config = updateButtonConfig(type);
        if (!config) return;
        button.textContent = disabled && type === activeType ? config.runningText : config.label;
    });
}

function triggerUpdate(type) {
    const config = updateButtonConfig(type);
    if (!config) return;
    state.activeUpdateType = type;
    setUpdateButtonsDisabled(true, type);
    showUpdateProgressPanel("正在执行更新前预检...");

    fetch(config.preflightEndpoint || `/api/update-preflight/${encodeURIComponent(type)}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(preflight => {
            if (!preflight.ok) {
                const issues = preflight.issues?.length ? `\n${preflight.issues.join("\n")}` : "";
                throw new Error(`${preflight.message || "预检失败"}${issues}`);
            }
            showUpdateProgressPanel("预检通过，正在启动更新...");
            return fetch(config.endpoint, { method: config.method || "POST" });
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            showUpdateProgressPanel(data.status === "running" ? "已有更新在进行中..." : config.startText);
            startStatusCheck();
        })
        .catch(error => {
            console.error(error);
            showStatusPanel(`⚠️ 无法触发更新：${error.message}`, "error");
            setUpdateButtonsDisabled(false);
            state.activeUpdateType = "";
        });
}

function startStatusCheck() {
    if (state.statusTimer) return;
    state.statusTimer = setInterval(() => {
        fetch("/api/status")
            .then(response => response.json())
            .then(data => {
                if (data.running) {
                    showUpdateProgressPanel(data.log || "正在更新中...", data);
                    return;
                }
                clearInterval(state.statusTimer);
                state.statusTimer = null;
                if (data.log?.includes("✅")) {
                    refreshCatalogDataAfterUpdate()
                        .then(() => {
                            showStatusPanel(`${data.log}\n\n✓ 页面数据已自动刷新`, "success");
                            setUpdateButtonsDisabled(false);
                            state.activeUpdateType = "";
                        })
                        .catch(error => {
                            console.error(error);
                            showStatusPanel(`${data.log}\n\n⚠️ 更新完成，但自动刷新页面数据失败，请手动刷新。`, "warning");
                            setUpdateButtonsDisabled(false);
                            state.activeUpdateType = "";
                        });
                    return;
                }
                if (data.log?.includes("❌")) showStatusPanel(data.log, "error");
                else showStatusPanel("✓ 准备就绪", "success");
                setUpdateButtonsDisabled(false);
                state.activeUpdateType = "";
            })
            .catch(error => {
                console.error(error);
                clearInterval(state.statusTimer);
                state.statusTimer = null;
                showStatusPanel("⚠️ 无法读取更新状态，请检查本地服务器", "error");
                setUpdateButtonsDisabled(false);
                state.activeUpdateType = "";
            });
    }, 2000);
}

document.addEventListener("DOMContentLoaded", () => {
    watchSystemTheme();
    loadCatalog()
        .then(initializeUI)
        .catch(error => {
            console.error(error);
            $("#loadingState").textContent = "数据加载失败，请检查 /api/catalog-data。";
        });
});
