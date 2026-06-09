const PLACEHOLDER_IMAGE = "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20400%20300'%3E%3Crect%20width='400'%20height='300'%20fill='%23f2f4f8'/%3E%3Ctext%20x='200'%20y='158'%20font-family='Arial'%20font-size='24'%20fill='%23909aaa'%20text-anchor='middle'%3ENo%20image%3C/text%3E%3C/svg%3E";

const state = {
    data: null,
    updateConfigs: [],
    imagePolicies: {},
    health: null,
    productsByCategory: new Map(),
    stats: {},
    currentCategory: "",
    currentFilter: "",
    currentPage: 1,
    pageSize: 20,
    currentView: "cards",
    filteredProducts: [],
    filterByCategory: {},
    pageByCategory: {},
    searchTimer: null,
    statusTimer: null,
    favorites: loadFavorites(),
    imageCache: new Map(),
    pagePreloadTimer: null,
    modalImages: [],
    modalIndex: 0,
    modalName: "",
    modalToken: 0,
};

const categoryScopedFilters = {
    "mini-gt": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "topspeed": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "spark": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "spark64": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "inno": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
    "poprace": new Set(["", "Pre-Order", "Released", "Sold Out", "fav"]),
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
        fetch("/api/catalog-data"),
        fetch("/api/update-config"),
    ]);
    if (!catalogResponse.ok) throw new Error(`catalog HTTP ${catalogResponse.status}`);
    if (!updateConfigResponse.ok) throw new Error(`update-config HTTP ${updateConfigResponse.status}`);
    const data = await catalogResponse.json();
    const updateConfig = await updateConfigResponse.json();

    let index = 1;
    data.categories.forEach(category => {
        const products = (category.products || []).map(product => ({
            ...product,
            categoryId: category.id,
            index: index++,
        }));
        state.productsByCategory.set(category.id, products);
        state.filterByCategory[category.id] = "";
        state.pageByCategory[category.id] = 1;
    });

    state.data = data;
    state.updateConfigs = updateConfig.updates || [];
    state.imagePolicies = data.image_policies || {};
    state.stats = data.category_stats || {};
    state.currentCategory = data.categories[0]?.id || "";
}

function initializeUI() {
    applyTheme();
    renderCategoryOptions();
    renderUpdateButtons();
    bindEvents();
    syncScopedControls();
    applyFilter();
    refreshHealthBadge();
    $("#loadingState").classList.add("hidden");
}

function renderCategoryOptions() {
    const select = $("#categorySelect");
    select.innerHTML = state.data.categories.map(category => {
        const count = category.products?.length || 0;
        return `<option value="${escapeHtml(category.id)}">全部 · ${escapeHtml(category.name)} (${count})</option>`;
    }).join("");
    select.value = state.currentCategory;

    const total = state.data.meta?.total_products ?? state.data.meta?.computed_total_products ?? 0;
    $("#metaLine").textContent = `数据来源: minigt.tsm-models.com · 新版架构验证 · 共 ${total} 款`;
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

    document.querySelectorAll(".status-filter, .fav-filter").forEach(button => {
        button.addEventListener("click", () => setFilter(button.dataset.filter || ""));
    });

    document.querySelectorAll(".view-btn").forEach(button => {
        button.addEventListener("click", () => setView(button.dataset.view));
    });

    $("#themeBtn").addEventListener("click", toggleTheme);
    $("#healthBtn").addEventListener("click", showCatalogHealth);
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
}

function clearSearch() {
    $("#search").value = "";
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    syncSearchClear();
    applyFilter();
    $("#search").focus();
}

function switchCategory(categoryId) {
    if (!categoryId || categoryId === state.currentCategory) return;
    state.filterByCategory[state.currentCategory] = state.currentFilter;
    state.pageByCategory[state.currentCategory] = state.currentPage;
    state.currentCategory = categoryId;
    const allowed = categoryScopedFilters[categoryId] || new Set(["", "fav"]);
    state.currentFilter = allowed.has(state.filterByCategory[categoryId]) ? state.filterByCategory[categoryId] : "";
    state.currentPage = state.pageByCategory[categoryId] || 1;
    $("#categorySelect").value = categoryId;
    syncScopedControls();
    applyFilter();
}

function setFilter(filter) {
    const allowed = categoryScopedFilters[state.currentCategory] || new Set(["", "fav"]);
    state.currentFilter = allowed.has(filter) ? filter : "";
    state.filterByCategory[state.currentCategory] = state.currentFilter;
    state.currentPage = 1;
    state.pageByCategory[state.currentCategory] = 1;
    syncFilterButtons();
    applyFilter();
}

function setView(view) {
    state.currentView = view === "table" ? "table" : "cards";
    document.querySelectorAll(".view-btn").forEach(button => button.classList.toggle("active", button.dataset.view === state.currentView));
    $("#cardsView").classList.toggle("hidden", state.currentView !== "cards");
    $("#tableView").classList.toggle("hidden", state.currentView !== "table");
    renderCurrentPage();
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

function applyFilter() {
    const query = $("#search").value.trim().toLowerCase();
    const products = currentSourceProducts();
    state.filteredProducts = products.filter(product => {
        const sku = String(product.sku || "").toLowerCase();
        const name = String(product.name || "").toLowerCase();
        const detailId = String(product.detail_id || "").toLowerCase();
        const matchesSearch = !query || sku.includes(query) || name.includes(query) || detailId.includes(query);
        const matchesStatus = !state.currentFilter
            ? true
            : state.currentFilter === "fav"
                ? state.favorites.has(product.sku)
                : product.status === state.currentFilter;
        return matchesSearch && matchesStatus;
    });

    const totalPages = totalPagesForCurrentFilter();
    state.currentPage = Math.max(1, Math.min(state.currentPage, totalPages));
    state.pageByCategory[state.currentCategory] = state.currentPage;
    updateStats();
    renderPagination();
    renderCurrentPage();
}

function updateStats() {
    const category = getCategory();
    const totalForCategory = category?.products?.length || 0;
    const counts = { "Released": 0, "Pre-Order": 0, "Sold Out": 0 };
    state.filteredProducts.forEach(product => {
        if (counts[product.status] !== undefined) counts[product.status] += 1;
    });
    $("#statsGroup").innerHTML = `
        <span class="stat-badge">显示 ${state.filteredProducts.length} / 共 ${totalForCategory}</span>
        <span class="stat-badge released">✅ ${counts["Released"]}</span>
        <span class="stat-badge preorder">📦 ${counts["Pre-Order"]}</span>
        <span class="stat-badge soldout">❌ ${counts["Sold Out"]}</span>
    `;
}

function totalPagesForCurrentFilter() {
    return Math.max(1, Math.ceil(state.filteredProducts.length / state.pageSize));
}

function currentPageProducts() {
    const start = (state.currentPage - 1) * state.pageSize;
    return state.filteredProducts.slice(start, start + state.pageSize);
}

function renderPagination() {
    const totalPages = totalPagesForCurrentFilter();
    const html = `
        <button data-page="first" ${state.currentPage === 1 ? "disabled" : ""}>首页</button>
        <button data-page="prev" ${state.currentPage === 1 ? "disabled" : ""}>上一页</button>
        <span class="page-info">第 ${state.currentPage} 页 / 共 ${totalPages} 页</span>
        <label>跳至 <input class="page-jump-input" type="number" min="1" max="${totalPages}" value="${state.currentPage}" ${totalPages <= 1 ? "disabled" : ""}> 页</label>
        <button data-page="jump" ${totalPages <= 1 ? "disabled" : ""}>跳转</button>
        <button data-page="next" ${state.currentPage === totalPages ? "disabled" : ""}>下一页</button>
        <button data-page="last" ${state.currentPage === totalPages ? "disabled" : ""}>末页</button>
        <select class="page-size" aria-label="每页数量">
            <option value="20" ${state.pageSize === 20 ? "selected" : ""}>20/页</option>
            <option value="50" ${state.pageSize === 50 ? "selected" : ""}>50/页</option>
            <option value="100" ${state.pageSize === 100 ? "selected" : ""}>100/页</option>
        </select>
    `;
    document.querySelectorAll(".pagination").forEach(nav => {
        nav.innerHTML = html;
        nav.onclick = handlePaginationClick;
        nav.onchange = handlePaginationChange;
        nav.onkeydown = handlePaginationKeydown;
    });
}

function handlePaginationClick(event) {
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
    renderPagination();
    renderCurrentPage();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function handlePaginationChange(event) {
    if (event.target.classList.contains("page-size")) {
        state.pageSize = parseInt(event.target.value, 10) || 20;
        state.currentPage = 1;
        state.pageByCategory[state.currentCategory] = 1;
        renderPagination();
        renderCurrentPage();
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
        renderPagination();
        renderCurrentPage();
        window.scrollTo({ top: 0, behavior: "smooth" });
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

function renderCard(product) {
    const images = rawImages(product, "card");
    const firstImage = imageForDisplay(images[0], product.categoryId, "card");
    const favActive = state.favorites.has(product.sku);
    return `
        <article class="card-item" data-sku="${escapeHtml(product.sku)}" data-index="${product.index}">
            <div class="card-img" data-open-image="${product.index}">
                <img src="${escapeHtml(firstImage)}" alt="${escapeHtml(product.name)}" loading="lazy" onerror="this.src='${PLACEHOLDER_IMAGE}'">
                <span class="card-img-count">${images.length} 图</span>
            </div>
            <div class="card-info">
                <div class="sku" data-copy="${escapeHtml(product.sku)}">${escapeHtml(product.sku)}</div>
                <a class="card-name" href="${escapeHtml(productUrl(product))}" target="_blank" rel="noopener">${escapeHtml(product.name)}</a>
                <div class="card-footer">
                    <span class="status ${statusClass(product.status)}">${escapeHtml(product.status || "Released")}</span>
                    <button class="fav-btn ${favActive ? "active" : ""}" data-fav="${escapeHtml(product.sku)}" title="收藏">${favActive ? "⭐" : "☆"}</button>
                </div>
            </div>
        </article>
    `;
}

function renderTableRow(product) {
    const images = rawImages(product, "card");
    const firstImage = imageForDisplay(images[0], product.categoryId, "card");
    const favActive = state.favorites.has(product.sku);
    return `
        <tr data-sku="${escapeHtml(product.sku)}" data-index="${product.index}">
            <td>${product.index}</td>
            <td><span class="sku" data-copy="${escapeHtml(product.sku)}">${escapeHtml(product.sku)}</span></td>
            <td><a class="card-name" href="${escapeHtml(productUrl(product))}" target="_blank" rel="noopener">${escapeHtml(product.name)}</a></td>
            <td><span class="status ${statusClass(product.status)}">${escapeHtml(product.status || "Released")}</span></td>
            <td><div class="table-images"><img class="thumb-img" src="${escapeHtml(firstImage)}" alt="${escapeHtml(product.name)}" data-open-image="${product.index}" onerror="this.src='${PLACEHOLDER_IMAGE}'"><span>${images.length} 图</span></div></td>
            <td><button class="fav-btn ${favActive ? "active" : ""}" data-fav="${escapeHtml(product.sku)}" title="收藏">${favActive ? "⭐" : "☆"}</button></td>
        </tr>
    `;
}

function productByIndex(index) {
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
    if (state.favorites.has(sku)) {
        state.favorites.delete(sku);
        showToast("已取消收藏");
    } else {
        state.favorites.add(sku);
        showToast("已收藏");
    }
    saveFavorites();
    applyFilter();
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
    const dark = localStorage.getItem("minigtTheme") === "dark";
    document.body.classList.toggle("dark", dark);
    $("#themeBtn").textContent = dark ? "☀️" : "🌙";
}

function toggleTheme() {
    document.body.classList.toggle("dark");
    const dark = document.body.classList.contains("dark");
    $("#themeBtn").textContent = dark ? "☀️" : "🌙";
    localStorage.setItem("minigtTheme", dark ? "dark" : "light");
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

    if (health.ok) {
        return `
            <div class="health-summary">
                <div class="health-title">✅ 数据健康检查通过</div>
                <div>${escapeHtml(totalLine)}</div>
                <div>分类数量：${escapeHtml(health.categoryCount)}</div>
            </div>
        `;
    }

    const categoryHtml = categories.map(category => {
        const lines = issueGroups(category).map(([label, count, examples]) => `
            <div class="health-issue-line">
                ${escapeHtml(label)}：${escapeHtml(count)}
                ${examples.length ? `<span>，样本：</span>${healthSampleButtons(category, examples)}` : ""}
            </div>
        `).join("");
        return `
            <div class="health-category">
                <strong>${escapeHtml(category.name || category.id)}：${escapeHtml(category.issueCount)} 个问题</strong>
                ${lines}
            </div>
        `;
    }).join("");

    return `
        <div class="health-summary">
            <div class="health-title">⚠️ 数据健康检查发现问题</div>
            <div>${escapeHtml(totalLine)}</div>
            <div>问题总数：${escapeHtml(health.issueCount)}</div>
            <div>分类数量：${escapeHtml(health.categoryCount)}</div>
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
    document.querySelector(".pagination-top")?.scrollIntoView({ behavior: "smooth", block: "start" });
    showToast(`已定位: ${query}`);
}

function handleStatusPanelClick(event) {
    const locateButton = event.target.closest("[data-health-locate]");
    if (!locateButton) return;
    locateHealthIssue(locateButton.dataset.healthLocate, locateButton.dataset.healthQuery);
}

function showStatusPanel(message, stateName = "") {
    const panel = $("#statusPanel");
    panel.className = `status-panel visible${stateName ? ` ${stateName}` : ""}`;
    panel.innerHTML = `<div class="status-panel-content">${escapeHtml(message)}</div><button class="status-close" type="button" aria-label="关闭">×</button>`;
    panel.querySelector("button").onclick = () => {
        panel.className = "status-panel";
        panel.innerHTML = "";
    };
}

function showStatusHtmlPanel(html, stateName = "") {
    const panel = $("#statusPanel");
    panel.className = `status-panel visible${stateName ? ` ${stateName}` : ""}`;
    panel.innerHTML = `<div class="status-panel-content">${html}</div><button class="status-close" type="button" aria-label="关闭">×</button>`;
    panel.querySelector("button").onclick = () => {
        panel.className = "status-panel";
        panel.innerHTML = "";
    };
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
    setUpdateButtonsDisabled(true, type);
    showStatusPanel("正在连接服务器...");

    fetch(config.endpoint)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            showStatusPanel(data.status === "running" ? "⏳ 已有更新在进行中..." : config.startText);
            startStatusCheck();
        })
        .catch(error => {
            console.error(error);
            showStatusPanel("⚠️ 无法触发更新，请确认本地服务器正在运行", "error");
            setUpdateButtonsDisabled(false);
        });
}

function startStatusCheck() {
    if (state.statusTimer) return;
    state.statusTimer = setInterval(() => {
        fetch("/api/status")
            .then(response => response.json())
            .then(data => {
                if (data.running) {
                    showStatusPanel(data.log || "⏳ 正在更新中...");
                    return;
                }
                clearInterval(state.statusTimer);
                state.statusTimer = null;
                if (data.log?.includes("✅")) showStatusPanel(data.log, "success");
                else if (data.log?.includes("❌")) showStatusPanel(data.log, "error");
                else showStatusPanel("✓ 准备就绪", "success");
                setUpdateButtonsDisabled(false);
            })
            .catch(error => {
                console.error(error);
                clearInterval(state.statusTimer);
                state.statusTimer = null;
                showStatusPanel("⚠️ 无法读取更新状态，请检查本地服务器", "error");
                setUpdateButtonsDisabled(false);
            });
    }, 2000);
}

document.addEventListener("DOMContentLoaded", () => {
    loadCatalog()
        .then(initializeUI)
        .catch(error => {
            console.error(error);
            $("#loadingState").textContent = "数据加载失败，请检查 /api/catalog-data。";
        });
});
