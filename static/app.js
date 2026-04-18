const CATEGORIES = ["all", "新規受託", "受託中止", "内容変更", "実施料", "容器変更", "業務日程", "その他"];
const CATEGORY_LABELS = { all: "すべて" };

let currentCategory = "all";
let debounceTimer = null;

function buildChips() {
  const wrap = document.getElementById("filterChips");
  CATEGORIES.forEach(cat => {
    const btn = document.createElement("button");
    btn.className = "chip" + (cat === "all" ? " active" : "");
    btn.textContent = CATEGORY_LABELS[cat] || cat;
    btn.dataset.cat = cat;
    btn.addEventListener("click", () => {
      currentCategory = cat;
      wrap.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      doSearch();
    });
    wrap.appendChild(btn);
  });
}

function highlight(text, keywords) {
  if (!keywords.length || !text) return text;
  const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.replace(re, "<mark>$1</mark>");
}

function renderCards(items, keywords) {
  const container = document.getElementById("results");
  if (!items.length) {
    container.innerHTML = '<div class="no-result">該当するインフォメーションが見つかりませんでした。<br>別のキーワードでお試しください。</div>';
    return;
  }
  container.innerHTML = items.map(item => {
    const tagCls = "tag-" + (item.category || "その他");
    const hl = t => highlight(t || "", keywords);
    const isHighlight = item.highlight ? " highlight" : "";
    const updateTag = item.highlight ? '<span class="tag tag-update">★ 更新</span>' : "";
    return `
      <div class="card${isHighlight}">
        <div class="card-meta">
          <div class="card-date">${hl(item.date)}</div>
          <div class="card-no">${hl(item.no)}</div>
        </div>
        <div class="card-body">
          <div class="card-title">${hl(item.title)}</div>
          <div class="card-summary">${hl(item.summary)}</div>
          <div class="card-tags">
            <span class="tag ${tagCls}">${item.category || "その他"}</span>
            ${updateTag}
          </div>
        </div>
        <div class="card-action">
          <a class="pdf-btn" href="${item.pdf}" target="_blank" rel="noopener">PDF 開く</a>
        </div>
      </div>`;
  }).join("");
}

function doSearch() {
  const q = document.getElementById("searchInput").value.trim();
  const clearBtn = document.getElementById("clearBtn");
  clearBtn.classList.toggle("visible", q.length > 0);

  const params = new URLSearchParams({ q, category: currentCategory });
  fetch("/api/search?" + params)
    .then(r => r.json())
    .then(data => {
      const keywords = q.toLowerCase().split(/\s+/).filter(Boolean);
      document.getElementById("resultCount").textContent =
        `${data.total} 件ヒット` + (q ? `（「${q}」）` : "");
      renderCards(data.results, keywords);
    })
    .catch(() => {
      document.getElementById("results").innerHTML =
        '<div class="no-result">データの取得に失敗しました。サーバーが起動しているか確認してください。</div>';
    });
}

function clearSearch() {
  document.getElementById("searchInput").value = "";
  document.getElementById("clearBtn").classList.remove("visible");
  doSearch();
}

// init
buildChips();
doSearch();

document.getElementById("searchInput").addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(doSearch, 180);
});
