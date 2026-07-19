(() => {
  "use strict";

  const app = document.getElementById("search-app");
  if (!app) return;

  const elements = {
    resultsColumn: app.querySelector(".results-column"),
    list: document.getElementById("results-list"),
    pagination: document.getElementById("pagination"),
    heading: document.getElementById("result-heading"),
    kicker: document.getElementById("result-kicker"),
    status: document.getElementById("search-status"),
    context: document.getElementById("search-context"),
    activeFilters: document.getElementById("active-filters"),
    activeFilterCount: document.getElementById("active-filter-count"),
    ranker: document.getElementById("ranker-select"),
    maxTime: document.getElementById("max-time"),
    difficulties: document.getElementById("difficulty-filters"),
    categories: document.getElementById("category-filters"),
    methods: document.getElementById("method-filters"),
    clearFilters: document.getElementById("clear-filters"),
    filterPanel: document.getElementById("filter-panel"),
    filterBackdrop: document.getElementById("filter-backdrop"),
    openFilters: document.getElementById("open-filters"),
    closeFilters: document.getElementById("close-filters"),
  };

  const PAGE_SIZE = 6;
  const fieldLabels = {
    title: "Tiêu đề",
    description: "Mô tả",
    ingredients: "Nguyên liệu",
    instructions: "Cách làm",
    categories: "Danh mục",
    cooking_method: "Cách nấu",
  };
  const suggestedQueries = ["gà nướng", "canh chua", "món chay", "hải sản"];
  let controller = null;

  function readState() {
    const params = new URLSearchParams(window.location.search);
    return {
      query: (params.get("q") || app.dataset.query || "").trim(),
      ranker: params.get("ranker") === "tfidf" ? "tfidf" : "bm25f",
      page: positiveInteger(params.get("page"), 1),
      maxTime: params.get("max_time") || "",
      difficulty: params.get("difficulty") || "",
      categories: new Set(params.getAll("category")),
      methods: new Set(params.getAll("method")),
    };
  }

  function positiveInteger(value, fallback) {
    const parsed = Number.parseInt(value || "", 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
  }

  let state = readState();

  function requestParameters() {
    const params = new URLSearchParams({
      q: state.query,
      ranker: state.ranker,
      page: String(state.page),
      page_size: String(PAGE_SIZE),
    });
    if (state.maxTime) params.set("max_time", state.maxTime);
    if (state.difficulty) params.set("difficulty", state.difficulty);
    state.categories.forEach((value) => params.append("category", value));
    state.methods.forEach((value) => params.append("method", value));
    return params;
  }

  function syncAddressBar() {
    const params = requestParameters();
    params.delete("page_size");
    if (state.page === 1) params.delete("page");
    if (state.ranker === "bm25f") params.delete("ranker");
    const url = `${app.dataset.searchUrl}?${params.toString()}`;
    window.history.replaceState({}, "", url);
  }

  function syncControls() {
    elements.ranker.value = state.ranker;
    elements.maxTime.value = state.maxTime;
  }

  async function runSearch({ updateAddress = true, scroll = false } = {}) {
    if (!state.query) {
      renderNoQuery();
      return;
    }

    if (controller) controller.abort();
    controller = new AbortController();

    if (updateAddress) syncAddressBar();
    syncControls();
    renderLoading();

    try {
      const url = `${app.dataset.apiUrl}?${requestParameters().toString()}`;
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error?.message || "Không thể thực hiện tìm kiếm.");
      }
      renderPayload(payload);
      if (scroll) {
        document.querySelector(".search-strip")?.scrollIntoView({ behavior: "smooth" });
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      renderError(error.message);
    }
  }

  function renderLoading() {
    elements.resultsColumn.setAttribute("aria-busy", "true");
    elements.kicker.textContent = "Đang tìm trong chỉ mục";
    elements.heading.textContent = `Kết quả cho “${state.query}”`;
    elements.context.hidden = true;
    elements.activeFilters.replaceChildren();
    elements.pagination.replaceChildren();
    elements.list.replaceChildren(...Array.from({ length: 3 }, createSkeleton));
    elements.status.textContent = `Đang tìm kiếm ${state.query}`;
  }

  function createSkeleton() {
    const card = document.createElement("div");
    card.className = "skeleton-card";
    card.setAttribute("aria-hidden", "true");

    const image = document.createElement("div");
    image.className = "skeleton-image";
    const copy = document.createElement("div");
    copy.className = "skeleton-copy";
    ["short", "title", "medium", "long", "long"].forEach((name) => {
      const line = document.createElement("div");
      line.className = `skeleton-line ${name}`;
      copy.append(line);
    });
    card.append(image, copy);
    return card;
  }

  function renderPayload(payload) {
    const pagination = payload.pagination;
    elements.resultsColumn.setAttribute("aria-busy", "false");
    elements.kicker.textContent = `${formatNumber(pagination.total_results)} kết quả · ${formatMilliseconds(payload.took_ms)}`;
    elements.heading.textContent = `Kết quả cho “${payload.query.text}”`;
    document.title = `${payload.query.text} — Bếp Tìm`;
    renderSearchContext(payload.query);
    renderActiveFilters();
    renderFacets(payload.facets || {});

    if (!payload.results.length) {
      renderEmpty();
      elements.pagination.replaceChildren();
    } else {
      elements.list.replaceChildren(...payload.results.map(createResultCard));
      renderPagination(pagination);
    }

    const announcement = pagination.total_results
      ? `Đã tìm thấy ${pagination.total_results} kết quả cho ${payload.query.text}`
      : `Không tìm thấy kết quả cho ${payload.query.text}`;
    elements.status.textContent = announcement;
  }

  function renderSearchContext(query) {
    const expanded = query.expanded_terms || [];
    if (!expanded.length) {
      elements.context.hidden = true;
      elements.context.replaceChildren();
      return;
    }
    const label = document.createElement("span");
    label.textContent = "BM25F đã mở rộng truy vấn với: ";
    const terms = document.createElement("strong");
    terms.textContent = expanded.map(displayTerm).join(", ");
    elements.context.replaceChildren(label, terms);
    elements.context.hidden = false;
  }

  function createResultCard(result) {
    const article = document.createElement("article");
    article.className = "result-card";

    const rank = document.createElement("span");
    rank.className = "result-rank";
    rank.textContent = `#${result.rank}`;

    const imageWrap = document.createElement("div");
    imageWrap.className = "result-image";
    const imageUrl = safeUrl(result.image_url);
    if (imageUrl) {
      const image = document.createElement("img");
      image.src = imageUrl;
      image.alt = `Hình minh họa ${result.title}`;
      image.loading = "lazy";
      image.addEventListener("error", () => image.remove());
      imageWrap.append(image);
    }

    const body = document.createElement("div");
    body.className = "result-body";

    const metaRow = document.createElement("div");
    metaRow.className = "result-meta-row";
    const source = document.createElement("span");
    source.className = "source-label";
    source.textContent = cleanSource(result.source || result.url);
    const score = document.createElement("span");
    score.className = "score-label";
    score.textContent = `Điểm ${Number(result.score).toFixed(4)}`;
    metaRow.append(source, score);

    const title = document.createElement("a");
    title.className = "result-title";
    title.href = safeUrl(result.url) || "#";
    title.target = "_blank";
    title.rel = "noopener noreferrer";
    title.textContent = result.title;
    title.append(createExternalIcon());

    const facts = document.createElement("div");
    facts.className = "recipe-facts";
    const totalTime = result.total_time_minutes ?? result.cook_time_minutes;
    if (totalTime !== null && totalTime !== undefined) {
      facts.append(createFact("clock", `${totalTime} phút`));
    }
    if (result.difficulty) facts.append(createFact("level", result.difficulty));
    if (result.servings) facts.append(createFact("servings", result.servings));

    const snippet = document.createElement("p");
    snippet.className = "result-snippet";
    appendHighlightedText(snippet, result.snippet?.text || "", result.snippet?.highlights || []);

    body.append(metaRow, title);
    if (facts.childElementCount) body.append(facts);
    body.append(snippet);

    const categories = (result.categories || []).slice(0, 4);
    if (categories.length) {
      const categoryWrap = document.createElement("div");
      categoryWrap.className = "result-categories";
      categories.forEach((value) => {
        const tag = document.createElement("span");
        tag.className = "category-tag";
        tag.textContent = value;
        categoryWrap.append(tag);
      });
      body.append(categoryWrap);
    }

    body.append(createExplanation(result));
    article.append(rank, imageWrap, body);
    return article;
  }

  function createExternalIcon() {
    const namespace = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(namespace, "svg");
    svg.classList.add("external-icon");
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS(namespace, "path");
    path.setAttribute("d", "M6 3H3.8A1.8 1.8 0 0 0 2 4.8v7.4A1.8 1.8 0 0 0 3.8 14h7.4a1.8 1.8 0 0 0 1.8-1.8V10M9 2h5v5m0-5L7.5 8.5");
    svg.append(path);
    return svg;
  }

  function createFact(type, value) {
    const item = document.createElement("span");
    item.className = "fact";
    item.append(createFactIcon(type));
    const text = document.createElement("span");
    text.textContent = value;
    item.append(text);
    return item;
  }

  function createFactIcon(type) {
    const namespace = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(namespace, "svg");
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS(namespace, "path");
    const paths = {
      clock: "M8 2a6 6 0 1 0 0 12A6 6 0 0 0 8 2Zm0 3v3.4l2.2 1.3",
      level: "M3 12V9m5 3V6m5 6V3",
      servings: "M5.5 7.2a2.2 2.2 0 1 0 0-4.4 2.2 2.2 0 0 0 0 4.4ZM1.8 13c.3-2.4 1.6-3.7 3.7-3.7S8.9 10.6 9.2 13m1.3-5.5a1.8 1.8 0 1 0 0-3.6M10.8 9.5c1.9.1 3 1.3 3.3 3.5",
    };
    path.setAttribute("d", paths[type]);
    svg.append(path);
    return svg;
  }

  function createExplanation(result) {
    const details = document.createElement("details");
    details.className = "explanation";
    const summary = document.createElement("summary");
    summary.textContent = "Vì sao kết quả này xuất hiện?";
    const content = document.createElement("div");
    content.className = "explanation-content";
    const explanation = result.explanation || {};

    const matchedFields = (explanation.matched_fields || [])
      .map((field) => fieldLabels[field] || field)
      .join(", ");
    const matchedTerms = (explanation.matched_terms || []).map(displayTerm).join(", ");
    const fieldScores = Object.entries(explanation.field_scores || {})
      .sort((first, second) => second[1] - first[1])
      .map(([field, value]) => `${fieldLabels[field] || field}: ${Number(value).toFixed(3)}`)
      .join(" · ");

    content.append(
      createExplanationItem("Từ khóa khớp", matchedTerms || "Không có"),
      createExplanationItem("Trường dữ liệu", matchedFields || "Không có"),
      createExplanationItem("Điểm theo trường", fieldScores || "Không có"),
      createExplanationItem("Thuật toán", state.ranker.toUpperCase()),
    );
    details.append(summary, content);
    return details;
  }

  function createExplanationItem(label, value) {
    const item = document.createElement("div");
    item.className = "explanation-item";
    const caption = document.createElement("span");
    caption.textContent = label;
    const text = document.createElement("strong");
    text.textContent = value;
    item.append(caption, text);
    return item;
  }

  function appendHighlightedText(container, text, rawRanges) {
    const ranges = rawRanges
      .map((range) => ({
        start: Math.max(0, Number(range.start)),
        end: Math.min(text.length, Number(range.end)),
      }))
      .filter((range) => Number.isFinite(range.start) && range.end > range.start)
      .sort((first, second) => first.start - second.start || first.end - second.end);

    let cursor = 0;
    ranges.forEach((range) => {
      if (range.start < cursor) return;
      container.append(document.createTextNode(text.slice(cursor, range.start)));
      const mark = document.createElement("mark");
      mark.textContent = text.slice(range.start, range.end);
      container.append(mark);
      cursor = range.end;
    });
    container.append(document.createTextNode(text.slice(cursor)));
  }

  function renderFacets(facets) {
    renderFacetGroup(
      elements.difficulties,
      facets.difficulties || [],
      state.difficulty ? [state.difficulty] : [],
      "difficulty",
      false,
    );
    renderFacetGroup(
      elements.categories,
      facets.categories || [],
      [...state.categories],
      "category",
      true,
    );
    renderFacetGroup(
      elements.methods,
      facets.cooking_methods || [],
      [...state.methods],
      "method",
      true,
    );
  }

  function renderFacetGroup(container, facets, selectedValues, kind, multiple) {
    const byValue = new Map(facets.map((item) => [item.value, item.count]));
    selectedValues.forEach((value) => {
      if (!byValue.has(value)) byValue.set(value, 0);
    });

    if (!byValue.size) {
      const empty = document.createElement("span");
      empty.className = "filter-placeholder";
      empty.textContent = "Không có lựa chọn";
      container.replaceChildren(empty);
      return;
    }

    const selected = new Set(selectedValues);
    const options = [...byValue.entries()].slice(0, kind === "category" ? 16 : 10).map(([value, count]) => {
      const label = document.createElement("label");
      label.className = "filter-option";
      label.title = value;
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = selected.has(value);
      input.dataset.kind = kind;
      input.value = value;
      input.setAttribute("aria-label", `${value}, ${count} kết quả`);
      input.dataset.multiple = multiple ? "true" : "false";
      const text = document.createElement("span");
      text.className = "option-label";
      text.textContent = value;
      const counter = document.createElement("span");
      counter.className = "option-count";
      counter.textContent = String(count);
      label.append(input, text, counter);
      return label;
    });
    container.replaceChildren(...options);
  }

  function renderActiveFilters() {
    const filters = [];
    if (state.maxTime) filters.push({ kind: "max_time", value: state.maxTime, label: `Tối đa ${state.maxTime} phút` });
    if (state.difficulty) filters.push({ kind: "difficulty", value: state.difficulty, label: state.difficulty });
    state.categories.forEach((value) => filters.push({ kind: "category", value, label: value }));
    state.methods.forEach((value) => filters.push({ kind: "method", value, label: value }));

    const chips = filters.map((filter) => {
      const chip = document.createElement("span");
      chip.className = "filter-chip";
      const label = document.createElement("span");
      label.textContent = filter.label;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.dataset.kind = filter.kind;
      remove.dataset.value = filter.value;
      remove.setAttribute("aria-label", `Xóa bộ lọc ${filter.label}`);
      remove.textContent = "×";
      chip.append(label, remove);
      return chip;
    });
    elements.activeFilters.replaceChildren(...chips);

    elements.activeFilterCount.textContent = String(filters.length);
    elements.activeFilterCount.hidden = filters.length === 0;
  }

  function renderPagination(pagination) {
    const total = pagination.total_pages;
    if (total <= 1) {
      elements.pagination.replaceChildren();
      return;
    }

    const controls = [];
    controls.push(createPageButton("←", pagination.page - 1, !pagination.has_previous, "Trang trước"));
    pageWindow(pagination.page, total).forEach((page) => {
      if (page === null) {
        const ellipsis = document.createElement("span");
        ellipsis.className = "page-ellipsis";
        ellipsis.textContent = "…";
        controls.push(ellipsis);
      } else {
        controls.push(createPageButton(String(page), page, false, `Trang ${page}`, page === pagination.page));
      }
    });
    controls.push(createPageButton("→", pagination.page + 1, !pagination.has_next, "Trang sau"));
    elements.pagination.replaceChildren(...controls);
  }

  function pageWindow(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
    const values = [1];
    if (current > 4) values.push(null);
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let page = start; page <= end; page += 1) values.push(page);
    if (current < total - 3) values.push(null);
    values.push(total);
    return values;
  }

  function createPageButton(label, page, disabled, ariaLabel, current = false) {
    const button = document.createElement("button");
    button.className = `page-button${current ? " current" : ""}`;
    button.type = "button";
    button.textContent = label;
    button.disabled = disabled;
    button.dataset.page = String(page);
    button.setAttribute("aria-label", ariaLabel);
    if (current) button.setAttribute("aria-current", "page");
    return button;
  }

  function renderEmpty() {
    elements.list.replaceChildren(createStatePanel(
      "empty",
      "Chưa tìm thấy món phù hợp",
      "Thử dùng tên nguyên liệu ngắn hơn, bỏ bớt bộ lọc hoặc chọn một gợi ý bên dưới.",
      true,
    ));
  }

  function renderNoQuery() {
    elements.resultsColumn.setAttribute("aria-busy", "false");
    elements.kicker.textContent = "Máy tìm kiếm công thức Việt";
    elements.heading.textContent = "Bạn muốn nấu món gì?";
    elements.list.replaceChildren(createStatePanel(
      "search",
      "Hãy nhập một món ăn hoặc nguyên liệu",
      "Ví dụ: gà nướng, canh chua, món chay hoặc hải sản.",
      true,
    ));
    elements.pagination.replaceChildren();
    elements.context.hidden = true;
    elements.activeFilters.replaceChildren();
    elements.resultsColumn.setAttribute("aria-busy", "false");
  }

  function renderError(message) {
    elements.resultsColumn.setAttribute("aria-busy", "false");
    elements.kicker.textContent = "Không thể tải kết quả";
    elements.list.replaceChildren(createStatePanel(
      "error",
      "Đã có lỗi kết nối",
      message || "Vui lòng kiểm tra server và thử lại.",
      false,
    ));
    const retry = document.createElement("button");
    retry.className = "button button-light";
    retry.type = "button";
    retry.textContent = "Thử lại";
    retry.addEventListener("click", () => runSearch());
    elements.list.firstElementChild.append(retry);
    elements.pagination.replaceChildren();
    elements.status.textContent = "Tìm kiếm gặp lỗi";
  }

  function createStatePanel(type, title, description, suggestions) {
    const panel = document.createElement("div");
    panel.className = "state-panel";
    const icon = document.createElement("div");
    icon.className = "state-icon";
    icon.append(createStateIcon(type));
    const heading = document.createElement("h2");
    heading.textContent = title;
    const text = document.createElement("p");
    text.textContent = description;
    panel.append(icon, heading, text);
    if (suggestions) {
      const links = document.createElement("div");
      links.className = "state-suggestions";
      suggestedQueries.forEach((query) => {
        const link = document.createElement("a");
        link.href = `${app.dataset.searchUrl}?q=${encodeURIComponent(query)}`;
        link.textContent = query;
        links.append(link);
      });
      panel.append(links);
    }
    return panel;
  }

  function createStateIcon(type) {
    const namespace = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(namespace, "svg");
    svg.setAttribute("viewBox", "0 0 40 40");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS(namespace, "path");
    const paths = {
      empty: "M18 7a11 11 0 1 0 0 22 11 11 0 0 0 0-22Zm8 19 8 8M14 16h.1M22 16h.1M14 23c2-2 6-2 8 0",
      search: "M17 6a11 11 0 1 0 0 22 11 11 0 0 0 0-22Zm8 19 9 9",
      error: "M20 5 36 33H4L20 5Zm0 9v9m0 5h.1",
    };
    path.setAttribute("d", paths[type]);
    svg.append(path);
    return svg;
  }

  function handleFacetChange(event) {
    const input = event.target.closest("input[data-kind]");
    if (!input) return;
    const kind = input.dataset.kind;
    const value = input.value;
    if (kind === "difficulty") {
      state.difficulty = input.checked ? value : "";
    } else {
      const target = kind === "category" ? state.categories : state.methods;
      if (input.checked) target.add(value);
      else target.delete(value);
    }
    state.page = 1;
    runSearch();
  }

  function removeFilter(kind, value) {
    if (kind === "max_time") state.maxTime = "";
    if (kind === "difficulty") state.difficulty = "";
    if (kind === "category") state.categories.delete(value);
    if (kind === "method") state.methods.delete(value);
    state.page = 1;
    runSearch();
  }

  function clearFilters() {
    state.maxTime = "";
    state.difficulty = "";
    state.categories.clear();
    state.methods.clear();
    state.page = 1;
    closeFilterDrawer();
    runSearch();
  }

  function openFilterDrawer() {
    elements.filterPanel.classList.add("open");
    elements.filterBackdrop.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeFilterDrawer() {
    elements.filterPanel.classList.remove("open");
    elements.filterBackdrop.classList.remove("open");
    document.body.style.overflow = "";
  }

  function cleanSource(value) {
    try {
      return new URL(value).hostname.replace(/^www\./, "");
    } catch (_error) {
      return String(value || "Nguồn công thức").replace(/^www\./, "");
    }
  }

  function safeUrl(value) {
    if (!value) return null;
    try {
      const url = new URL(value, window.location.origin);
      return ["http:", "https:"].includes(url.protocol) ? url.href : null;
    } catch (_error) {
      return null;
    }
  }

  function displayTerm(value) {
    return String(value).replaceAll("_", " ");
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("vi-VN").format(Number(value));
  }

  function formatMilliseconds(value) {
    const numeric = Number(value);
    if (numeric < 1) return "< 1 ms";
    return `${numeric.toLocaleString("vi-VN", { maximumFractionDigits: 2 })} ms`;
  }

  elements.ranker.addEventListener("change", () => {
    state.ranker = elements.ranker.value;
    state.page = 1;
    runSearch();
  });
  elements.maxTime.addEventListener("change", () => {
    state.maxTime = elements.maxTime.value;
    state.page = 1;
    runSearch();
  });
  elements.difficulties.addEventListener("change", handleFacetChange);
  elements.categories.addEventListener("change", handleFacetChange);
  elements.methods.addEventListener("change", handleFacetChange);
  elements.clearFilters.addEventListener("click", clearFilters);
  elements.activeFilters.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-kind]");
    if (button) removeFilter(button.dataset.kind, button.dataset.value);
  });
  elements.pagination.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-page]");
    if (!button || button.disabled) return;
    state.page = positiveInteger(button.dataset.page, 1);
    runSearch({ scroll: true });
  });
  elements.openFilters?.addEventListener("click", openFilterDrawer);
  elements.closeFilters?.addEventListener("click", closeFilterDrawer);
  elements.filterBackdrop?.addEventListener("click", closeFilterDrawer);
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeFilterDrawer();
  });
  window.addEventListener("popstate", () => {
    state = readState();
    runSearch({ updateAddress: false });
  });

  syncControls();
  runSearch();
})();
