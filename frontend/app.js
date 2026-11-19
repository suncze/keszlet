"use strict";

const ICONS = {
  box:'<path d="m12 3 9 5v9l-9 5-9-5V8l9-5Z"/><path d="m3 8 9 5 9-5M12 13v9M7.5 5.5l9 5"/>',
  warehouse:'<path d="m3 9 9-6 9 6v12H3V9Z"/><path d="M7 21V11h10v10M7 15h10M7 18h10"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  cart:'<path d="M3 3h2l2.5 12h11l3-8H6"/><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/>',
  activity:'<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  shield:'<path d="m12 3 8 3v6c0 5-8 10-8 10S4 17 4 12V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  edit:'<path d="m16 3 5 5-12 12H4v-5L16 3ZM13 6l5 5"/>',
  swap:'<path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4"/>',
  in:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  out:'<path d="M12 15V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
  alert:'<path d="m10.2 4-8 14a2 2 0 0 0 1.7 3h16.2a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.6 0ZM12 9v4M12 17h.01"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/>',
  calculator:'<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M8 6h8M8 11h1m6 0h1M8 15h1m6 0h1M8 19h1m6 0h1"/>',
  sort:'<path d="M8 4v16m-4-4 4 4 4-4M16 20V4m-4 4 4-4 4 4"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
};
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.box}</svg>`;
const fmt = number => new Intl.NumberFormat("hu-HU").format(number);
const fullDate = value => new Intl.DateTimeFormat("hu-HU", {year:"numeric", month:"short", day:"numeric", hour:"2-digit", minute:"2-digit", timeZone:"Europe/Budapest"}).format(new Date(value));
const shortTime = value => new Intl.DateTimeFormat("hu-HU", {month:"short", day:"numeric",hour:"2-digit", minute:"2-digit",timeZone:"Europe/Budapest"}).format(new Date(value));
const normalized = value => String(value).toLocaleLowerCase("hu").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const state = { products: [], recent: [], totalMovements: 0, loaded: false, view: "inventory", query: "", category: "", status: "", sort: "name", descending: false, page: 1, pageSize: 8, log: {q:"",type:"",from:"",to:"",page:1,limit:12}, logData: null, logRequest: 0, editor: null, busy: false };
const viewInfo = {
  inventory: ["Készletáttekintés", "Minden termék, minden változás. Tisztán és egy helyen."],
  reorder: ["Utánrendelési javaslatok", "Tervezd meg a beszerzést a készlet és a várható fogyás alapján."],
  movements: ["Készletmozgások", "A raktár teljes története. Visszakereshető, megőrzött előzmények."],
};

function hydrateIcons(root = document) { $$('[data-icon]', root).forEach(el => { el.innerHTML = icon(el.dataset.icon); }); }

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${window.APP_CONFIG.apiBase}${path}`, { ...options, signal:controller.signal, headers:{...(options.body ? {"Content-Type":"application/json"} : {}), ...options.headers}});
    let data;
    try { data = await response.json(); } catch { throw new Error("A kiszolgáló érvénytelen választ küldött."); }
    if (!response.ok) { const error = new Error(data.error || "A művelet nem sikerült."); error.field = data.field; error.status = response.status; throw error; }
    return data;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("A kiszolgáló nem válaszolt időben. Próbáld újra a műveletet.");
    if (error instanceof TypeError) throw new Error("Nem érhető el a kiszolgáló. Ellenőrizd, hogy fut-e a backend.");
    throw error;
  } finally { clearTimeout(timer); }
}

function toast(message, isError = false) {
  const el = document.createElement("div");
  el.className = `toast${isError ? " error" : ""}`;
  el.innerHTML = `${icon(isError ? "alert" : "check")}<span>${esc(message)}</span>`;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), 6500);
}

async function load() {
  const errorBox = $("#global-error");
  errorBox.hidden = true;
  if (!state.loaded) $("#view").innerHTML = '<div class="panel loading"><div><div class="loader"></div>Készletadatok betöltése…</div></div>';
  try {
    const [products, recent] = await Promise.all([api("/api/products"), api("/api/movements?limit=4")]);
    state.products = products.items;
    state.recent = recent.items;
    state.totalMovements = recent.total;
    state.loaded = true;
    $("#connection").className = "connection";
    $("#connection").innerHTML = "<i></i>Kapcsolódva";
    $("#updated-at").textContent = `Frissítve: ${new Intl.DateTimeFormat("hu-HU", {hour:"2-digit",minute:"2-digit",timeZone:"Europe/Budapest"}).format(new Date())}`;
    renderStats();
    renderView();
  } catch (error) {
    $("#connection").className = "connection offline";
    $("#connection").innerHTML = "<i></i>Nincs kapcsolat";
    errorBox.innerHTML = `${esc(error.message)} <button type="button" id="retry-load">Újrapróbálkozás</button>`;
    errorBox.hidden = false;
    $("#retry-load").addEventListener("click", load);
    if (!state.loaded) $("#view").innerHTML = emptyState("Nem sikerült betölteni az adatokat", "Indítsd el a kiszolgálót, majd próbáld újra a betöltést.", "warehouse");
  }
}

function renderStats() {
  const products = state.products;
  const low = products.filter(p => p.is_low).length;
  const reorder = products.filter(p => p.reorder_quantity > 0);
  const sum = products.reduce((n, p) => n + p.stock, 0);
  const stats = [
    {title:"Nyilvántartott termék", value:products.length, note:`${new Set(products.map(p => p.category).filter(Boolean)).size} kategóriában`, icon:"box"},
    {title:"Összes készlet", value:sum, unit:"db", note:"A központi raktárban", icon:"layers"},
    {title:"Alacsony készletszint", value:low, note:low ? "A minimumon vagy az alatt" : "Minden készletszint rendben", icon:"alert", className:low ? "alert" : ""},
    {title:"Utánrendelendő termék", value:reorder.length, note:`${fmt(reorder.reduce((n, p) => n + p.reorder_quantity, 0))} db javasolt beszerzés`, icon:"cart", className:"accent"},
  ];
  $("#stats").innerHTML = stats.map(s => `<article class="stat ${s.className || ""}"><div class="stat-top"><span class="stat-title">${s.title}</span><span class="stat-icon">${icon(s.icon)}</span></div><div class="stat-value">${fmt(s.value)}${s.unit ? `<small>${s.unit}</small>` : ""}</div><div class="stat-note">${s.note}</div></article>`).join("");
  $("#reorder-count").textContent = fmt(reorder.length);
}

function emptyState(title, description, symbol = "box", button = "") {
  return `<div class="empty-state"><div class="empty-icon">${icon(symbol)}</div><h3>${esc(title)}</h3><p>${esc(description)}</p>${button}</div>`;
}

function productCell(p) {
  return `<div class="product-cell"><span class="product-symbol tone-${p.id % 4}">${icon("box")}</span><div><strong>${esc(p.name)}</strong><small>${esc(p.sku)}</small></div></div>`;
}

function badge(p) {
  if (!p.stock) return '<span class="badge empty">Elfogyott</span>';
  return p.is_low ? '<span class="badge low">Alacsony készlet</span>' : '<span class="badge">Rendben</span>';
}

function stockCell(p) {
  const denominator = Math.max(1, p.minimum_stock * 3, p.daily_usage * p.lead_time + p.safety_stock);
  const width = Math.min(100, p.stock / denominator * 100);
  return `<span class="stock-number">${fmt(p.stock)} <small>db</small></span><div class="stock-meter ${p.stock ? (p.is_low ? "low" : "") : "empty"}" aria-hidden="true"><span style="width:${width}%"></span></div>`;
}

function categories() {
  return [...new Set(state.products.map(p => p.category).filter(Boolean))].sort((a,b) => a.localeCompare(b,"hu"));
}

function filteredProducts(reorder = false) {
  let products = state.products.filter(p => (!reorder || p.reorder_quantity > 0) && (!state.category || p.category === state.category) && (!state.query || normalized(`${p.name} ${p.sku} ${p.category}`).includes(normalized(state.query))) && (!state.status || (state.status === "low" ? p.is_low : state.status === "empty" ? p.stock === 0 : !p.is_low)));
  return products.sort((a,b) => {
    let result = state.sort === "name" ? a.name.localeCompare(b.name,"hu") : a[state.sort] - b[state.sort];
    return (state.descending ? -result : result) || a.id-b.id;
  });
}

function pagination(page, pages, prefix) {
  return `<div class="pagination"><button type="button" data-page="${prefix}:prev" ${page <= 1 ? "disabled" : ""}>Előző</button><span>${page} / ${Math.max(1,pages)}</span><button type="button" data-page="${prefix}:next" ${page >= pages ? "disabled" : ""}>Következő</button></div>`;
}

function toolbar(reorder = false) {
  return `<div class="toolbar"><div class="toolbar-left"><label class="search">${icon("search")}<input type="search" id="product-search" placeholder="Keresés név vagy cikkszám alapján…" aria-label="Termékek keresése" value="${esc(state.query)}"></label><select id="category-filter" aria-label="Szűrés kategória szerint"><option value="">Minden kategória</option>${categories().map(c => `<option value="${esc(c)}" ${state.category === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>${!reorder ? `<select id="status-filter" aria-label="Szűrés készletállapot szerint"><option value="">Minden állapot</option><option value="low" ${state.status === "low" ? "selected" : ""}>Alacsony készlet</option><option value="empty" ${state.status === "empty" ? "selected" : ""}>Elfogyott</option><option value="ok" ${state.status === "ok" ? "selected" : ""}>Rendben</option></select>` : ""}</div><div class="toolbar-right"><button type="button" class="button tertiary" data-action="clear">Szűrők törlése</button><button type="button" class="icon-button" data-action="refresh" aria-label="Adatok frissítése" title="Adatok frissítése">${icon("refresh")}</button></div></div>`;
}

function renderView() {
  if (!state.loaded) return;
  if (state.view === "movements") return renderMovements();
  const reorder = state.view === "reorder";
  const low = state.products.filter(p => p.is_low).length;
  let intro = "";
  if (reorder) intro = `<section class="formula-panel"><span>${icon("calculator")}</span><div><h2>Adatokból javaslat. A döntés a tiéd.</h2><p>Javasolt mennyiség = max(0, napi fogyás × beszerzési idő + biztonsági készlet − aktuális készlet).<br>A lista nem hoz létre rendelést, és nem módosítja a készletet.</p></div></section>`;
  else if (low) intro = `<section class="insight"><span class="insight-icon">${icon("alert")}</span><div><strong>${fmt(low)} termék készlete figyelmet igényel</strong><p>Ellenőrizd az utánrendelési javaslatokat, és tervezd meg időben a beszerzést.</p></div><a class="button" href="#reorder">Javaslatok megtekintése</a></section>`;
  $("#view").innerHTML = `${intro}<section class="panel" aria-label="${reorder ? "Utánrendelési lista" : "Terméklista"}"><div class="panel-heading"><div><div class="panel-title"><h2>${reorder ? "Beszerzési lista" : "Termékek"}</h2><span class="counter" id="product-counter"></span></div>${reorder ? '<p class="panel-subtitle">Kizárólag a pozitív rendelési javaslattal rendelkező termékek.</p>' : ""}</div><button type="button" class="button secondary" data-action="export">${icon("download")}CSV export</button></div>${toolbar(reorder)}<div id="product-table"></div></section>${!reorder ? belowPanels() : ""}`;
  bindToolbar();
  renderProductTable();
}

function sortHeader(label, key) {
  return `<th scope="col" aria-sort="${state.sort === key ? (state.descending ? "descending" : "ascending") : "none"}"><button type="button" class="sort-button" data-sort="${key}">${label}${icon("sort")}</button></th>`;
}

function renderProductTable() {
  const reorder = state.view === "reorder";
  const products = filteredProducts(reorder);
  const pages = Math.ceil(products.length / state.pageSize);
  state.page = Math.max(1,Math.min(state.page, pages || 1));
  const start = (state.page - 1) * state.pageSize;
  const items = products.slice(start,start + state.pageSize);
  $("#product-counter").textContent = `${fmt(products.length)} termék`;
  if (!products.length) {
    const noProducts = state.products.length === 0;
    const hasFilters = Boolean(state.query || state.category || state.status);
    $("#product-table").innerHTML = emptyState(noProducts ? "Itt kezdődik az átlátható készlet" : hasFilters ? "Nincs a szűrésnek megfelelő termék" : "Most nincs szükség utánrendelésre", noProducts ? "Vedd fel az első terméket, állítsd be a készletszinteket, és kövesd a változásokat egy helyen." : hasFilters ? "Próbálj másik keresőkifejezést, vagy töröld a szűrőket." : "A megadott fogyási és beszerzési adatok alapján a jelenlegi készlet elegendő.", noProducts ? "box" : "check", noProducts ? '<button type="button" class="button primary" data-action="create">Első termék felvétele</button>' : hasFilters ? '<button type="button" class="button secondary" data-action="clear">Szűrők törlése</button>' : "");
    return;
  }
  const headers = reorder ? `${sortHeader("TERMÉK", "name")}<th scope="col">KÉSZLET</th><th scope="col">NAPI FOGYÁS</th><th scope="col">BESZERZÉSI IDŐ</th><th scope="col">BIZTONSÁGI KÉSZLET</th>${sortHeader("JAVASOLT RENDELÉS", "reorder_quantity")}` : `${sortHeader("TERMÉK", "name")}<th scope="col">KATEGÓRIA</th>${sortHeader("KÉSZLET", "stock")}<th scope="col">MIN. KÉSZLET</th><th scope="col">ÁLLAPOT</th><th scope="col">MŰVELETEK</th>`;
  const rows = items.map(p => reorder ? `<tr><td>${productCell(p)}</td><td class="numeric">${fmt(p.stock)} db</td><td class="numeric">${fmt(p.daily_usage)} db</td><td class="numeric">${fmt(p.lead_time)} nap</td><td class="numeric">${fmt(p.safety_stock)} db</td><td class="numeric"><span class="reorder-value">${fmt(p.reorder_quantity)}</span> db</td></tr>` : `<tr><td>${productCell(p)}</td><td class="category-text">${esc(p.category || "Nincs megadva")}</td><td>${stockCell(p)}</td><td class="numeric muted">${fmt(p.minimum_stock)} db</td><td>${badge(p)}</td><td><div class="row-actions"><button type="button" class="movement-button" data-move="${p.id}" aria-label="Készletmozgás: ${esc(p.name)}">${icon("swap")}Mozgás</button><button type="button" class="icon-button" data-edit="${p.id}" aria-label="${esc(p.name)} szerkesztése" title="Termék szerkesztése">${icon("edit")}</button><button type="button" class="icon-button" data-history="${p.id}" aria-label="${esc(p.name)} mozgásnaplója" title="Termék mozgásnaplója">${icon("clock")}</button></div></td></tr>`).join("");
  $("#product-table").innerHTML = `<div class="table-wrap"><table class="${reorder ? "reorder" : "inventory"}-table"><caption class="sr-only">${reorder ? "Számított utánrendelési javaslatok" : "Termékek és aktuális készletszintek"}</caption><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table></div><div class="table-footer"><span>${fmt(start + 1)}–${fmt(start + items.length)} / ${fmt(products.length)} termék</span>${pagination(state.page,pages,"products")}</div>`;
}

const typeLabels = {in:"Bevételezés", out:"Kiadás", opening:"Nyitókészlet"};
function belowPanels() {
  const recent = state.recent.map(m => `<div class="recent-row"><span class="direction-icon ${m.type}">${icon(m.type === "opening" ? "box" : m.type)}</span><div class="recent-detail"><strong>${esc(m.product_name)}</strong><small>${esc(typeLabels[m.type])} · ${esc(m.product_sku)}</small></div><div><div class="recent-quantity ${m.type}">${m.type === "out" ? "−" : "+"}${fmt(m.quantity)} db</div><div class="recent-time">${esc(shortTime(m.created_at))}</div></div></div>`).join("");
  return `<div class="below-grid"><section class="mini-panel"><div class="mini-heading"><h2>Legutóbbi készletmozgások</h2><a href="#movements">Teljes napló</a></div>${recent || '<p class="small-empty">Még nincs készletmozgás. Az első bevételezés vagy kiadás itt is megjelenik.</p>'}</section><section class="mini-panel planning-panel"><span class="planning-label">BESZERZÉS ELŐRELÁTÓAN</span><h2>A megfelelő készlet.<br>A megfelelő időben.</h2><p>A napi fogyás és a beszerzési idő alapján időben felismerheted a várható készlethiányt.</p><a class="button secondary" href="#reorder">Beszerzés megtervezése</a></section></div>`;
}

function bindToolbar() {
  $("#product-search").addEventListener("input", event => { state.query = event.target.value; state.page = 1; renderProductTable(); });
  $("#category-filter").addEventListener("change", event => { state.category = event.target.value; state.page = 1; renderProductTable(); });
  $("#status-filter")?.addEventListener("change", event => { state.status = event.target.value; state.page = 1; renderProductTable(); });
}

function renderMovements() {
  const log = state.log;
  $("#view").innerHTML = `<section class="panel"><div class="panel-heading"><div><div class="panel-title"><h2>Mozgásnapló</h2><span class="counter" id="log-counter">${fmt(state.totalMovements)} bejegyzés</span></div><p class="panel-subtitle">A rögzített mozgások utólag nem módosíthatók. Időzóna: Budapest.</p></div><button class="button secondary" type="button" data-action="new-movement">${icon("swap")}Új mozgás</button></div><div class="toolbar"><div class="toolbar-left"><label class="search">${icon("search")}<input id="log-search" type="search" placeholder="Termék, cikkszám vagy megjegyzés…" aria-label="Keresés a mozgásnaplóban" value="${esc(log.q)}"></label><select id="type-filter" aria-label="Mozgástípus"><option value="">Minden mozgás</option>${Object.entries(typeLabels).map(([key, label]) => `<option value="${key}" ${log.type === key ? "selected" : ""}>${label}</option>`).join("")}</select></div><div class="toolbar-right"><label class="filter-date">Ettől <input type="date" id="date-from" value="${esc(log.from)}"></label><label class="filter-date">Eddig <input type="date" id="date-to" value="${esc(log.to)}"></label><button type="button" class="button tertiary" data-action="clear-log">Törlés</button></div></div><div id="log-table"></div></section>`;
  if (log.product_id) {
    const product = state.products.find(p => p.id === Number(log.product_id));
    const hint = document.createElement("div");
    hint.className = "product-filter-hint";
    hint.innerHTML = `<span>Termékszűrés: <strong>${esc(product ? `${product.name} · ${product.sku}` : `#${log.product_id}`)}</strong></span><button type="button" class="button tertiary" data-action="clear-log">Szűrés törlése</button>`;
    $("#log-table").before(hint);
  }
  let timeout;
  $("#log-search").addEventListener("input", e => { state.log.q = e.target.value; state.log.page = 1; clearTimeout(timeout); timeout = setTimeout(fetchLog, 250); });
  for (const [id,key] of [["type-filter","type"],["date-from","from"],["date-to","to"]]) $("#" + id).addEventListener("change", e => { state.log[key] = e.target.value; state.log.page = 1; fetchLog(); });
  fetchLog();
}

async function fetchLog() {
  const request = ++state.logRequest;
  const target = $("#log-table");
  if (!target || state.view !== "movements") return;
  target.innerHTML = '<div class="loading"><div><div class="loader"></div>Napló betöltése…</div></div>';
  try {
    const data = await api(`/api/movements?${new URLSearchParams(Object.entries(state.log).filter(([,v]) => v !== ""))}`);
    if (request !== state.logRequest || state.view !== "movements") return;
    state.logData = data;
    $("#log-counter").textContent = `${fmt(data.total)} bejegyzés`;
    if (!data.items.length) { target.innerHTML = emptyState("Nincs megjeleníthető készletmozgás", "A bevételezések, kiadások és nyitókészletek itt jelennek meg. Ha szűrőt állítottál be, próbáld törölni.", "activity"); return; }
    const rows = data.items.map(m => `<tr><td><span class="numeric">${esc(fullDate(m.created_at))}</span><small class="log-id">#${m.id}</small></td><td>${productCell({id:m.product_id,name:m.product_name,sku:m.product_sku})}</td><td><span class="badge ${m.type === "out" ? "low" : m.type === "opening" ? "neutral" : ""}">${esc(typeLabels[m.type])}</span></td><td class="numeric"><strong class="${m.type === "out" ? "quantity-out" : "quantity-in"}">${m.type === "out" ? "−" : "+"}${fmt(m.quantity)}</strong> db</td><td class="numeric">${fmt(m.stock_after)} db</td><td class="note-cell">${esc(m.note || "—")}</td></tr>`).join("");
    target.innerHTML = `<div class="table-wrap"><table class="movement-table"><caption class="sr-only">Készletmozgások, legújabbak elöl</caption><thead><tr><th scope="col">IDŐPONT</th><th scope="col">TERMÉK</th><th scope="col">TÍPUS</th><th scope="col">MENNYISÉG</th><th scope="col">ÚJ KÉSZLET</th><th scope="col">MEGJEGYZÉS</th></tr></thead><tbody>${rows}</tbody></table></div><div class="table-footer"><span>${fmt(data.total)} rögzített mozgás · Legújabb elöl</span>${pagination(data.page,Math.ceil(data.total / data.limit),"log")}</div>`;
  } catch (error) { if (request === state.logRequest && state.view === "movements") target.innerHTML = `<div class="error-banner" role="alert">${esc(error.message)} <button type="button" data-action="retry-log">Újrapróbálkozás</button></div>`; }
}

function field(name, label, value = "", options = {}) {
  const type = options.type || "text";
  return `<div class="field${options.full ? " full" : ""}"><label for="field-${name}">${esc(label)}${options.optional ? '<span class="optional">nem kötelező</span>' : ""}</label><input id="field-${name}" name="${name}" type="${type}" value="${esc(value)}" ${type === "number" ? `min="0" max="${name === "initial_stock" || name === "quantity" ? 1000000000 : 1000000}" step="1" inputmode="numeric"` : `maxlength="${options.maxlength || 160}"`} ${options.optional ? "" : "required"} aria-describedby="error-${name}${options.hint ? ` hint-${name}` : ""}" autocomplete="off">${options.hint ? `<span class="field-hint" id="hint-${name}">${esc(options.hint)}</span>` : ""}<span class="field-error" id="error-${name}"></span></div>`;
}

function openProduct(id) {
  const p = id ? state.products.find(p => p.id === id) : {name:"",sku:"",category:"",initial_stock:0,minimum_stock:0,daily_usage:0,lead_time:0,safety_stock:0};
  if (!p) return;
  state.editor = {kind:"product",id:id || null};
  $("#dialog-title").textContent = id ? "Termék szerkesztése" : "Új termék felvétele";
  $("#dialog-eyebrow").textContent = "TERMÉKADATOK";
  $("#save-button").textContent = id ? "Módosítások mentése" : "Termék mentése";
  $("#dialog-body").innerHTML = `${id ? `<p class="dialog-note">Aktuális készlet: <strong>${fmt(p.stock)} db</strong>. A készletet a Mozgás művelettel változtathatod meg.</p>` : ""}<div class="form-grid">${field("name","Terméknév",p.name,{full:true})}${field("sku","Egyedi cikkszám",p.sku,{maxlength:64,hint:"A kis- és nagybetűk nem különböznek."})}${field("category","Kategória",p.category,{optional:true,maxlength:80})}${!id ? field("initial_stock","Kezdőkészlet (db)",0,{type:"number",full:true,hint:"Nemnegatív egész darabszám. A nyitókészletet megőrizzük a naplóban."}) : ""}<div class="form-section">Készletszintek és beszerzés</div>${field("minimum_stock","Minimális készlet (db)",p.minimum_stock,{type:"number",hint:"Ezen az értéken és alatta figyelmeztetünk."})}${field("safety_stock","Biztonsági készlet (db)",p.safety_stock,{type:"number",hint:"Az utánrendeléshez számított tartalék."})}${field("daily_usage","Átlagos napi fogyás (db)",p.daily_usage,{type:"number"})}${field("lead_time","Beszerzési idő (nap)",p.lead_time,{type:"number"})}</div><div id="form-error" class="field-error" role="alert"></div>`;
  showDialog();
}

function openMovement(id) {
  if (!state.products.length) { toast("Először vegyél fel egy terméket."); openProduct(); return; }
  state.editor = {kind:"movement", signature:null, requestId:null};
  $("#dialog-title").textContent = "Készletmozgás rögzítése";
  $("#dialog-eyebrow").textContent = "BEVÉTELEZÉS ÉS KIADÁS";
  $("#save-button").textContent = "Mozgás rögzítése";
  $("#dialog-body").innerHTML = `<div class="form-grid"><div class="type-toggle" role="group" aria-label="Mozgás típusa"><label class="type-option"><input type="radio" name="type" value="in" checked><span>${icon("in")}Bevételezés</span></label><label class="type-option"><input type="radio" name="type" value="out"><span>${icon("out")}Kiadás</span></label></div><div class="field full"><label for="field-product_id">Termék</label><select name="product_id" id="field-product_id">${state.products.map(p => `<option value="${p.id}" ${p.id === id ? "selected" : ""}>${esc(p.name)} · ${esc(p.sku)}</option>`).join("")}</select><span class="field-error" id="error-product_id"></span></div>${field("quantity","Mennyiség (db)",1,{type:"number",full:true,hint:"Pozitív egész darabszám. A készlet nem csökkenhet nulla alá."})}${field("note","Megjegyzés","",{full:true,optional:true,maxlength:500,hint:"Például szállítólevél száma vagy a kiadás célja."})}</div><div class="movement-preview" id="movement-preview" aria-live="polite"></div><div id="form-error" class="field-error" role="alert"></div>`;
  $("#field-quantity").min = "1";
  $("#dialog-body").addEventListener("input", previewMovement);
  showDialog();
  previewMovement();
}

function previewMovement() {
  if (state.editor?.kind !== "movement") return;
  const p = state.products.find(p => p.id === Number($("#field-product_id").value));
  if (!p) return;
  const raw = $("#field-quantity").value;
  const q = /^\d+$/.test(raw) ? Number(raw) : NaN;
  const incoming = $('input[name="type"]:checked').value === "in";
  const after = p.stock + (incoming ? q : -q);
  const valid = Number.isSafeInteger(q) && q > 0 && q <= 1e9 && after >= 0 && after <= 1e9;
  $("#movement-preview").className = `movement-preview${valid ? "" : " invalid"}`;
  $("#movement-preview").innerHTML = `<span>Jelenlegi készlet: ${fmt(p.stock)} db<br><small>A művelet után várható készlet</small></span><strong>${valid ? `${fmt(after)} db` : "Érvénytelen"}</strong>`;
}

function showDialog() {
  hydrateIcons($("#form-dialog"));
  $("#form-dialog").showModal();
  const first = $("#dialog-body input:not([type=radio]), #dialog-body select");
  if (first) first.focus();
}

function closeDialog() { if (!state.busy) { $("#form-dialog").close(); state.editor = null; $("#dialog-body").removeEventListener("input", previewMovement); } }

function formError(name, message) {
  const input = $(`[name="${name}"]`, $("#editor"));
  if (input) input.setAttribute("aria-invalid","true");
  const target = $("#error-" + name) || $("#form-error");
  if (target) target.textContent = message;
}

async function submit(event) {
  event.preventDefault();
  if (state.busy || !state.editor) return;
  $$(".field-error", $("#editor")).forEach(el => { el.textContent = ""; });
  $$('[aria-invalid]', $("#editor")).forEach(el => el.removeAttribute("aria-invalid"));
  const values = Object.fromEntries(new FormData($("#editor")));
  let valid = true;
  for (const input of $$("#editor input[type=number]")) {
    const raw = input.value.trim();
    const value = Number(raw);
    if (!/^\d+$/.test(raw) || !Number.isSafeInteger(value) || value < Number(input.min) || value > Number(input.max)) {
      formError(input.name, Number(input.min) === 1 ? "Pozitív egész darabszámot adj meg (legfeljebb 1 milliárd)." : `0 és ${fmt(Number(input.max))} közötti egész számot adj meg.`); valid = false;
    } else values[input.name] = value;
  }
  if (state.editor.kind === "product") {
    for (const [name,label] of [["name","terméknevet"],["sku","cikkszámot"]]) {
      values[name] = values[name].trim();
      if (!values[name]) { formError(name,`Adj meg ${label}.`); valid = false; }
    }
    if (state.products.some(p => p.sku.toUpperCase() === values.sku.toUpperCase() && p.id !== state.editor.id)) { formError("sku","Ez a cikkszám már létezik."); valid = false; }
  } else {
    values.product_id = Number(values.product_id);
    const p = state.products.find(p => p.id === values.product_id);
    if (values.type === "out" && p && values.quantity > p.stock) { formError("quantity",`Nincs elegendő készlet. Elérhető: ${fmt(p.stock)} db.`); valid = false; }
    const signature = JSON.stringify(values);
    if (state.editor.signature !== signature) { state.editor.signature = signature; state.editor.requestId = crypto.randomUUID(); }
    values.request_id = state.editor.requestId;
  }
  if (!valid) { $('[aria-invalid="true"]', $("#editor"))?.focus(); return; }
  state.busy = true;
  const button = $("#save-button");
  const text = button.textContent;
  button.textContent = "Mentés…";
  $$("#editor button, #editor input, #editor select").forEach(el => { el.disabled = true; });
  try {
    const movement = state.editor.kind === "movement";
    const editing = state.editor.id;
    await api(movement ? "/api/movements" : editing ? `/api/products/${editing}` : "/api/products", {method:editing ? "PUT" : "POST", body:JSON.stringify(values)});
    state.busy = false;
    closeDialog();
    toast(movement ? "A készletmozgást rögzítettük." : editing ? "A termék adatait módosítottuk." : "Az új terméket felvettük.");
    await load();
  } catch (error) {
    if (error.field) formError(error.field, error.message);
    else $("#form-error").textContent = error.message;
  } finally {
    state.busy = false;
    button.textContent = text;
    $$("#editor button, #editor input, #editor select").forEach(el => { el.disabled = false; });
    $('[aria-invalid="true"]', $("#editor"))?.focus();
  }
}

function exportCSV() {
  const reorder = state.view === "reorder";
  const products = filteredProducts(reorder);
  if (!products.length) return toast("Nincs exportálható termék.");
  const rows = [["Termék", "Cikkszám", "Kategória", "Készlet (db)", "Minimum (db)", "Napi fogyás (db)", "Beszerzési idő (nap)", "Biztonsági készlet (db)", "Javasolt rendelés (db)"], ...products.map(p => [p.name,p.sku,p.category,p.stock,p.minimum_stock,p.daily_usage,p.lead_time,p.safety_stock,p.reorder_quantity])];
  const safeCell = value => { let text = String(value); if (/^[=+\-@\t\r\n]/.test(text)) text = "'" + text; return '"' + text.replace(/"/g,'""') + '"'; };
  const csv = "\uFEFF" + rows.map(row => row.map(safeCell).join(";")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${reorder ? "utanrendeles" : "keszlet"}-${new Date().toISOString().slice(0,10)}.csv`;
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url),1000);
  toast(`${fmt(products.length)} termék exportálva.`);
}

function route() {
  const next = location.hash.slice(1) || "inventory";
  state.view = Object.hasOwn(viewInfo,next) ? next : "inventory";
  state.logRequest++;
  state.query = ""; state.category = ""; state.status = ""; state.page = 1; state.sort = state.view === "reorder" ? "reorder_quantity" : "name"; state.descending = state.view === "reorder";
  const [title, description] = viewInfo[state.view];
  $("#page-title").textContent = title;
  $("#page-description").textContent = description;
  $("#breadcrumb-current").textContent = state.view === "reorder" ? "Utánrendelés" : state.view === "movements" ? "Mozgásnapló" : title;
  document.title = `${title} — Készlet`;
  $$('[data-nav]').forEach(el => { el.classList.toggle("active",el.dataset.nav === state.view); if (el.dataset.nav === state.view) el.setAttribute("aria-current","page"); else el.removeAttribute("aria-current"); });
  renderView();
}

document.addEventListener("click", event => {
  const button = event.target.closest("button");
  if (!button || button.disabled) return;
  if (button.dataset.edit) return openProduct(Number(button.dataset.edit));
  if (button.dataset.move) return openMovement(Number(button.dataset.move));
  if (button.dataset.history) {
    state.log = {q:"",type:"",from:"",to:"",page:1,limit:12,product_id:Number(button.dataset.history)};
    location.hash = "movements";
    return;
  }
  if (button.dataset.sort) { const key = button.dataset.sort; state.descending = state.sort === key ? !state.descending : false; state.sort = key; renderProductTable(); return; }
  if (button.dataset.page) {
    const [scope,direction] = button.dataset.page.split(":");
    if (scope === "products") { state.page += direction === "next" ? 1 : -1; renderProductTable(); }
    else { state.log.page += direction === "next" ? 1 : -1; fetchLog(); }
    return;
  }
  switch (button.dataset.action) {
    case "create": openProduct(); break;
    case "new-movement": openMovement(); break;
    case "refresh": load(); break;
    case "clear": state.query = ""; state.category = ""; state.status = ""; state.page = 1; renderView(); break;
    case "clear-log": state.log = {q:"",type:"",from:"",to:"",page:1,limit:12}; renderMovements(); break;
    case "retry-log": fetchLog(); break;
    case "export": exportCSV(); break;
  }
});
$("#new-product").addEventListener("click", () => openProduct());
$("#close-dialog").addEventListener("click", closeDialog);
$("#cancel-dialog").addEventListener("click", closeDialog);
$("#form-dialog").addEventListener("cancel", event => { event.preventDefault(); closeDialog(); });
$("#editor").addEventListener("submit", submit);
window.addEventListener("hashchange",route);
$("#today").textContent = new Intl.DateTimeFormat("hu-HU",{year:"numeric",month:"long",day:"numeric",timeZone:"Europe/Budapest"}).format(new Date());
hydrateIcons();
route();
load();
