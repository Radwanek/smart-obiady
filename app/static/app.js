let activeTab = 'meals';
let filterStore = 'Wszystkie';
let filterCategory = 'Wszystkie';
let filterSearch = '';
let dealsSearchTimer = null;
let activePlanData = null;
let pollTimer = null;
let currentZoom = 1.0;

document.addEventListener('DOMContentLoaded', () => {
  fetchStatus();
  loadMealPlan();
  loadPromotions();
  
  // Status check every 8 seconds
  setInterval(fetchStatus, 8000);

  // Close lightbox on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLightbox();
  });
});

function switchTab(tabId, btnElement) {
  activeTab = tabId;
  document.querySelectorAll('.segment-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  
  if (btnElement) {
    btnElement.classList.add('active');
  } else {
    const tabMap = { 'meals': 0, 'assistant': 1, 'deals': 2, 'shopping': 3 };
    const idx = tabMap[tabId] ?? 0;
    const btns = document.querySelectorAll('.segment-btn');
    if (btns[idx]) btns[idx].classList.add('active');
  }
  
  const pane = document.getElementById(`tab-${tabId}`);
  if (pane) pane.classList.add('active');
  
  if (tabId === 'shopping' && activePlanData) {
    renderShoppingList(activePlanData);
  }
  if (tabId === 'assistant') {
    const input = document.getElementById('assistantInput');
    if (input) setTimeout(() => input.focus(), 150);
  }
}

async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    const btn = document.getElementById('refreshBtn');
    const btnLabel = document.getElementById('btnLabel');
    const btnIcon = document.getElementById('btnIcon');
    const btnSpinner = document.getElementById('btnSpinner');
    
    if (data.is_syncing) {
      dot.className = 'pulse-indicator syncing';
      text.innerText = 'Przeszukiwanie gazetek & analiza czystego składu...';
      btn.disabled = true;
      btnLabel.innerText = 'AI układa menu...';
      btnIcon.classList.add('hidden');
      btnSpinner.classList.remove('hidden');
    } else {
      dot.className = 'pulse-indicator';
      btn.disabled = false;
      btnLabel.innerText = 'Nowy Plan';
      btnIcon.classList.remove('hidden');
      btnSpinner.classList.add('hidden');
      
      if (data.last_sync) {
        const timeStr = data.last_sync.timestamp ? new Date(data.last_sync.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
        text.innerText = `Aktualizacja: ${timeStr} • Baza: ${data.last_sync.deals_count} produktów`;
      } else {
        text.innerText = 'Baza gotowa. Kliknij, aby wygenerować pierwsze menu.';
      }
    }
  } catch (err) {
    console.error('Error fetching status:', err);
  }
}

async function triggerRefresh() {
  const btn = document.getElementById('refreshBtn');
  btn.disabled = true;
  document.getElementById('btnLabel').innerText = 'Start...';
  
  try {
    const res = await fetch('/api/refresh', { method: 'POST' });
    const data = await res.json();
    console.log('Refresh trigger:', data);
    
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      const sres = await fetch('/api/status');
      const sdata = await sres.json();
      if (!sdata.is_syncing) {
        clearInterval(pollTimer);
        pollTimer = null;
        fetchStatus();
        loadMealPlan();
        loadPromotions();
      }
    }, 2500);
    
    fetchStatus();
  } catch (err) {
    console.error('Error triggering refresh:', err);
    btn.disabled = false;
  }
}

/* ============================================================
   MEALS RENDERING
   ============================================================ */
async function loadMealPlan() {
  const loader = document.getElementById('mealsLoading');
  const container = document.getElementById('mealsContainer');
  const soupsContainer = document.getElementById('soupsContainer');
  const summaryCard = document.getElementById('planSummaryCard');
  const summaryText = document.getElementById('planSummaryText');
  
  loader.classList.remove('hidden');
  
  try {
    const res = await fetch('/api/meal-plan');
    const data = await res.json();
    
    loader.classList.add('hidden');
    
    if (data.plan && data.plan.meals && data.plan.meals.length > 0) {
      activePlanData = data.plan;
      summaryCard.classList.remove('hidden');
      summaryText.innerText = data.plan.weekly_summary || "Zdrowe, zbilansowane obiady z czystym składem dla 2 osób bazujące na bieżących przecenach w dyskontach.";
      
      // Update budget tracker (600 zł / month -> 150 zł / week)
      const dinnersCost = data.plan.total_estimated_cost || "~84 zł";
      const budgetRem = data.plan.budget_remaining || "~66 zł (z puli 150 zł/tydz.)";
      
      const dinnersEl = document.getElementById('dinnersCostVal');
      const remEl = document.getElementById('budgetRemVal');
      const barEl = document.getElementById('budgetBarFill');
      
      if (dinnersEl) dinnersEl.innerText = dinnersCost;
      if (remEl) remEl.innerText = budgetRem;
      if (barEl) {
        const numMatch = dinnersCost.match(/(\d+)/);
        const spent = numMatch ? parseInt(numMatch[1], 10) : 84;
        const pct = Math.min(Math.round((spent / 150) * 100), 100);
        barEl.style.width = `${pct}%`;
      }
      
      const dinners = data.plan.meals.filter(m => m.type !== 'Zupa' && !m.day.toLowerCase().includes('zupa'));
      const soups = data.plan.meals.filter(m => m.type === 'Zupa' || m.day.toLowerCase().includes('zupa'));
      
      container.innerHTML = dinners.map(m => createMealCardHtml(m)).join('');
      soupsContainer.innerHTML = soups.map(m => createMealCardHtml(m)).join('');
      
      renderShoppingList(activePlanData);
    } else {
      summaryCard.classList.add('hidden');
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 48px; background:#fff; border-radius:24px; border:1px solid var(--border-subtle)">
          <p style="font-size: 1.1rem; font-weight:700; margin-bottom: 8px;">Brak wygenerowanego menu</p>
          <p style="color:var(--text-secondary); margin-bottom: 18px;">Kliknij przycisk, aby przeszukać gazetki i ułożyć zdrowe obiady.</p>
          <button class="ios-btn ios-btn-primary" onclick="triggerRefresh()">⚡ Generuj Plan Obiadów</button>
        </div>
      `;
      soupsContainer.innerHTML = '';
    }
  } catch (err) {
    console.error('Error loading meal plan:', err);
    loader.classList.add('hidden');
  }
}

function createMealCardHtml(meal) {
  const gear = (meal.equipment || 'Airfryer').toLowerCase();
  const gearClass = `gear-${gear}`;
  const gearIcon = {
    'airfryer': '⚡',
    'piekarnik': '🔥',
    'patelnia': '🍳',
    'garnek': '🍲'
  }[gear] || '🍳';

  const nutriHtml = renderNutriScoreHtml(meal.nutri_score || 'A');

  const promoItemsHtml = (meal.discounted_ingredients || []).map(ing => {
    const store = (ing.store || '').toLowerCase();
    const storeClass = `store-pill ${store}`;
    
    // Look up image for this ingredient from active promotions if available
    return `
      <div class="promo-ingredient-tile">
        <div class="ingredient-info">
          <span class="ingredient-name">${escapeHtml(ing.name)}</span>
          <div class="ingredient-meta">
            <span class="${storeClass}">${escapeHtml(ing.store)}</span>
            ${ing.price ? `<span class="ingredient-price">${escapeHtml(ing.price)}</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');

  const pantryText = (meal.pantry_ingredients || []).join(' • ');
  const stepsHtml = (meal.instructions || []).map(step => `<li>${escapeHtml(step)}</li>`).join('');

  return `
    <article class="meal-card-ios">
      <div>
        <div class="card-top-row">
          <div style="display:flex; align-items:center; gap:6px;">
            <span class="day-pill">${escapeHtml(meal.day)}</span>
            <span class="day-pill" style="background:#e0f2fe; color:#0369a1;">👥 2 porcje</span>
          </div>
          <span class="gear-pill ${gearClass}">${gearIcon} ${escapeHtml(meal.equipment)}</span>
        </div>

        <h3 class="dish-heading">${escapeHtml(meal.title)}</h3>

        <div class="time-row" style="flex-wrap:wrap; gap:8px;">
          ${meal.prep_time ? `<span class="prep-time">⏱️ ${escapeHtml(meal.prep_time)}</span>` : ''}
          ${meal.cost_for_two ? `<span class="cost-badge-ios">💰 ${escapeHtml(meal.cost_for_two)} <span style="font-weight:500; font-size:0.7rem; opacity:0.85;">(${escapeHtml(meal.cost_per_person || '')}/os.)</span></span>` : ''}
          ${nutriHtml}
        </div>
      </div>

      <div class="ingredients-cluster">
        <span class="cluster-label">Przecenione składniki z gazetki:</span>
        ${promoItemsHtml || '<span style="font-size:0.8rem; color:var(--text-tertiary)">Brak składników promocyjnych</span>'}
      </div>

      ${pantryText ? `
      <div>
        <span class="cluster-label">Dodatki z domu / przyprawy:</span>
        <div class="pantry-row">${escapeHtml(pantryText)}</div>
      </div>
      ` : ''}

      ${stepsHtml ? `
      <details class="recipe-accordion">
        <summary>👨‍🍳 Pokaż przepis krok po kroku</summary>
        <ol class="recipe-steps">
          ${stepsHtml}
        </ol>
      </details>
      ` : ''}
    </article>
  `;
}

/* ============================================================
   PROMOTIONS CATALOG RENDERING
   ============================================================ */
async function loadPromotions() {
  const container = document.getElementById('dealsContainer');
  const countLabel = document.getElementById('dealsCountLabel');
  
  try {
    const params = new URLSearchParams();
    if (filterStore !== 'Wszystkie') params.append('store', filterStore);
    if (filterCategory !== 'Wszystkie') params.append('category', filterCategory);
    if (filterSearch && filterSearch.trim()) params.append('search', filterSearch.trim());
    params.append('limit', '250');
    
    const res = await fetch(`/api/promotions?${params.toString()}`);
    const data = await res.json();
    
    if (countLabel) {
      const cnt = data.count || (data.promotions ? data.promotions.length : 0);
      countLabel.innerHTML = `Znaleziono: <strong>${cnt}</strong> ${filterSearch ? `dla „${escapeHtml(filterSearch)}”` : 'aktualnych okazji'}`;
    }
    
    if (data.promotions && data.promotions.length > 0) {
      container.innerHTML = data.promotions.map(d => {
        const storeClass = `store-pill ${(d.store || '').toLowerCase()}`;
        const nutriHtml = renderNutriScoreHtml(d.nutri_score || 'A');
        const isClean = (d.clean_label || 'CLEAN') === 'CLEAN';
        const cleanClass = isClean ? 'clean' : 'processed';
        const cleanText = isClean ? '🌿 Czysty Skład' : '⚠️ Przetworzone';
        
        const dateBadge = d.date_badge ? `
          <span class="date-badge ${d.is_urgent ? 'urgent' : ''}">⏰ ${escapeHtml(d.date_badge)}</span>
        ` : '';
        const appBadge = d.is_app_deal ? `
          <span class="app-deal-badge">📱 ${escapeHtml(d.app_badge || 'Z aplikacją')}</span>
        ` : '';

        const hasImg = d.image_url && d.image_url.startsWith('http');
        const imgBtn = hasImg ? `
          <button class="flyer-thumb-btn" onclick="openLightbox('${escapeHtml(d.image_url)}', '${escapeHtml(d.store)} - Gazetka (strona ${d.page_number || '1'})', '${escapeHtml(d.name)}')">
            🔍 Gazetka
          </button>
        ` : '';

        const tagsList = d.tags || [];
        const tagsHtml = tagsList.length > 0 ? `
          <div class="deal-tags-row">
            ${tagsList.slice(0, 3).map(t => `
              <span class="deal-tag-pill" onclick="searchTag('${escapeHtml(t)}', event)" title="Kliknij, aby wyszukać #${escapeHtml(t)}">#${escapeHtml(t)}</span>
            `).join('')}
          </div>
        ` : '';

        return `
          <div class="deal-item-ios">
            <div>
              <div class="deal-header-row">
                <span class="${storeClass}">${escapeHtml(d.store)}</span>
                ${nutriHtml}
              </div>
              <h4 class="deal-title">${escapeHtml(d.name)}</h4>
              
              <div class="deal-quality-row">
                <span class="clean-label-pill ${cleanClass}">${cleanText}</span>
                ${dateBadge}
                ${appBadge}
                ${imgBtn}
              </div>
              ${tagsHtml}
              ${d.clean_label_desc ? `<p class="clean-desc">${escapeHtml(d.clean_label_desc)}</p>` : ''}
            </div>

            <div class="deal-footer-row">
              <span class="deal-price-value">${escapeHtml(d.price)}</span>
              <span style="font-size:0.75rem; font-weight:600; color:var(--text-tertiary)">${escapeHtml(d.category)}</span>
            </div>
          </div>
        `;
      }).join('');
    } else {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 48px; background:#fff; border-radius:24px; color:var(--text-secondary); border: 1px solid var(--border-soft);">
          <p style="font-size:1.15rem; font-weight:700; margin-bottom:8px; color:#1e1b2e;">Brak promocji spełniających kryteria</p>
          <p style="color:var(--text-muted); margin-bottom:16px;">Spróbuj wpisać inne słowo kluczowe (np. <em>chipsy</em>, <em>kurczak</em>, <em>owoce</em>, <em>truskawki</em>, <em>napoje</em>) lub zresetuj filtry.</p>
          <button class="ios-btn ios-btn-secondary" onclick="clearDealsSearch()">Resetuj wyszukiwanie</button>
        </div>
      `;
    }
  } catch (err) {
    console.error('Error loading promotions:', err);
  }
}

function handleDealsSearchInput(val) {
  filterSearch = val;
  const clearBtn = document.getElementById('dealsSearchClear');
  if (clearBtn) {
    clearBtn.classList.toggle('hidden', !val || val.length === 0);
  }
  
  if (dealsSearchTimer) clearTimeout(dealsSearchTimer);
  dealsSearchTimer = setTimeout(() => {
    loadPromotions();
  }, 250);
}

function clearDealsSearch() {
  filterSearch = '';
  const input = document.getElementById('dealsSearchInput');
  if (input) input.value = '';
  const clearBtn = document.getElementById('dealsSearchClear');
  if (clearBtn) clearBtn.classList.add('hidden');
  
  document.querySelectorAll('#quickTagsBar .keyword-chip').forEach(b => {
    b.classList.toggle('active', b.innerText.includes('Wszystkie'));
  });
  loadPromotions();
}

function filterByKeyword(keyword, btnElement) {
  document.querySelectorAll('#quickTagsBar .keyword-chip').forEach(b => b.classList.remove('active'));
  if (btnElement) btnElement.classList.add('active');
  
  const input = document.getElementById('dealsSearchInput');
  const clearBtn = document.getElementById('dealsSearchClear');
  
  if (keyword === 'Wszystkie') {
    filterSearch = '';
    if (input) input.value = '';
    if (clearBtn) clearBtn.classList.add('hidden');
  } else {
    filterSearch = keyword;
    if (input) input.value = keyword;
    if (clearBtn) clearBtn.classList.remove('hidden');
  }
  
  loadPromotions();
}

function searchTag(tag, event) {
  if (event) event.stopPropagation();
  const input = document.getElementById('dealsSearchInput');
  const clearBtn = document.getElementById('dealsSearchClear');
  
  filterSearch = tag;
  if (input) {
    input.value = tag;
    input.focus();
  }
  if (clearBtn) clearBtn.classList.remove('hidden');
  
  document.querySelectorAll('#quickTagsBar .keyword-chip').forEach(b => {
    b.classList.toggle('active', b.innerText.toLowerCase().includes(tag.toLowerCase()));
  });
  
  loadPromotions();
  
  const searchWrap = document.querySelector('.deals-search-wrapper');
  if (searchWrap) searchWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setFilter(type, value) {
  if (type === 'store') {
    filterStore = value;
    document.querySelectorAll('#storeFilters .pill-item').forEach(b => {
      b.classList.toggle('active', b.innerText.includes(value));
    });
  } else if (type === 'category') {
    filterCategory = value;
    document.querySelectorAll('#categoryFilters .pill-item').forEach(b => {
      b.classList.toggle('active', b.innerText.includes(value));
    });
  }
  loadPromotions();
}

/* ============================================================
   NUTRI-SCORE COMPONENT GENERATOR
   ============================================================ */
function renderNutriScoreHtml(score) {
  const activeLetter = (score || 'A').toUpperCase();
  const letters = ['A', 'B', 'C', 'D', 'E'];
  
  const blocks = letters.map(l => {
    const isActive = l === activeLetter ? 'active' : '';
    const colorClass = `nutri-${l.toLowerCase()}`;
    return `<span class="nutri-letter ${colorClass} ${isActive}">${l}</span>`;
  }).join('');
  
  return `
    <div class="nutri-score-badge" title="Nutri-Score: ${activeLetter}">
      <span class="nutri-score-title">NUTRI-SCORE</span>
      ${blocks}
    </div>
  `;
}

/* ============================================================
   SHOPPING LIST
   ============================================================ */
function renderShoppingList(plan) {
  const container = document.getElementById('shoppingListContainer');
  if (!plan || !plan.meals) {
    container.innerHTML = '<p style="color:var(--text-secondary)">Brak wygenerowanego planu.</p>';
    return;
  }

  const storeMap = {
    'Lidl': new Set(),
    'Biedronka': new Set(),
    'Kaufland': new Set()
  };

  plan.meals.forEach(m => {
    (m.discounted_ingredients || []).forEach(item => {
      const store = item.store || 'Inne';
      const label = `${item.name}${item.price ? ` (${item.price})` : ''}`;
      if (!storeMap[store]) storeMap[store] = new Set();
      storeMap[store].add(label);
    });
  });

  const checkedItems = JSON.parse(localStorage.getItem('checked_shopping_items') || '[]');

  let html = '';
  for (const [store, itemsSet] of Object.entries(storeMap)) {
    if (itemsSet.size === 0) continue;
    const items = Array.from(itemsSet);
    const storeClass = `store-pill ${store.toLowerCase()}`;

    html += `
      <div class="shopping-store-column">
        <div class="column-head">
          <span class="column-name">${escapeHtml(store)}</span>
          <span class="${storeClass}">${items.length} pozycji</span>
        </div>
        <div class="shopping-items-flow">
          ${items.map(item => {
            const isChecked = checkedItems.includes(item);
            return `
              <label class="shopping-checkbox-row ${isChecked ? 'checked' : ''}">
                <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleShoppingItem('${escapeHtml(item)}', this)">
                <span>${escapeHtml(item)}</span>
              </label>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = html || '<p style="color:var(--text-secondary)">Brak pozycji na liście zakupów.</p>';
}

function toggleShoppingItem(item, checkbox) {
  let checkedItems = JSON.parse(localStorage.getItem('checked_shopping_items') || '[]');
  if (checkbox.checked) {
    if (!checkedItems.includes(item)) checkedItems.push(item);
    checkbox.closest('.shopping-checkbox-row').classList.add('checked');
  } else {
    checkedItems = checkedItems.filter(i => i !== item);
    checkbox.closest('.shopping-checkbox-row').classList.remove('checked');
  }
  localStorage.setItem('checked_shopping_items', JSON.stringify(checkedItems));
}

/* ============================================================
   LIGHTBOX / ZOOM MODAL
   ============================================================ */
function openLightbox(imageUrl, title, subtitle) {
  const modal = document.getElementById('imageLightbox');
  const img = document.getElementById('lightboxImg');
  const titleEl = document.getElementById('lightboxTitle');
  const subEl = document.getElementById('lightboxSub');
  
  img.src = imageUrl;
  titleEl.innerText = title || "Oryginalna strona gazetki";
  subEl.innerText = subtitle || "Powiększ, aby sprawdzić szczegóły oferty";
  
  currentZoom = 1.0;
  img.style.transform = `scale(${currentZoom})`;
  
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  const modal = document.getElementById('imageLightbox');
  modal.classList.add('hidden');
  document.body.style.overflow = '';
}

function handleLightboxClick(e) {
  if (e.target.classList.contains('lightbox-backdrop')) {
    closeLightbox();
  }
}

function zoomIn() {
  currentZoom = Math.min(currentZoom + 0.35, 3.0);
  applyZoom();
}

function zoomOut() {
  currentZoom = Math.max(currentZoom - 0.35, 0.7);
  applyZoom();
}

function resetZoom() {
  currentZoom = 1.0;
  applyZoom();
}

function toggleZoomDblClick() {
  currentZoom = currentZoom === 1.0 ? 2.0 : 1.0;
  applyZoom();
}

function applyZoom() {
  const img = document.getElementById('lightboxImg');
  img.style.transform = `scale(${currentZoom})`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/* ============================================================
   AI SHOPPING ASSISTANT
   ============================================================ */
async function handleAssistantSubmit(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('assistantInput');
  const query = input.value.trim();
  if (!query) return;
  
  input.value = '';
  await sendAssistantMessage(query);
}

function askQuickPrompt(text) {
  switchTab('assistant');
  const input = document.getElementById('assistantInput');
  if (input) input.value = text;
  sendAssistantMessage(text);
}

async function sendAssistantMessage(userText) {
  const chatBox = document.getElementById('assistantChatBox');
  const sendBtn = document.getElementById('assistantSendBtn');
  const sendIcon = document.getElementById('sendIcon');
  const sendSpinner = document.getElementById('sendSpinner');
  
  // 1. Append user bubble
  const userHtml = `
    <div class="chat-msg user-msg">
      <div class="msg-bubble">
        <p>${escapeHtml(userText)}</p>
      </div>
    </div>
  `;
  chatBox.insertAdjacentHTML('beforeend', userHtml);
  chatBox.scrollTop = chatBox.scrollHeight;
  
  // 2. Loading state & temporary bot bubble
  sendBtn.disabled = true;
  sendIcon.classList.add('hidden');
  sendSpinner.classList.remove('hidden');
  
  const loadingId = `typing_${Date.now()}`;
  const typingHtml = `
    <div class="chat-msg bot-msg" id="${loadingId}">
      <div class="bot-avatar">🤖</div>
      <div class="msg-bubble">
        <p style="color:var(--text-muted); font-style:italic;">
          Szukam w aktualnych gazetkach Lidla, Biedronki i Kauflandu... 🔍
        </p>
      </div>
    </div>
  `;
  chatBox.insertAdjacentHTML('beforeend', typingHtml);
  chatBox.scrollTop = chatBox.scrollHeight;
  
  try {
    const res = await fetch('/api/assistant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText })
    });
    const data = await res.json();
    
    // Remove typing bubble
    const typingEl = document.getElementById(loadingId);
    if (typingEl) typingEl.remove();
    
    // Format markdown
    let replyHtml = (data.reply || '')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/### (.*?)\n/g, '<h4 style="margin:10px 0 4px; font-size:1rem; font-weight:800; color:#1e1b2e;">$1</h4>')
      .replace(/## (.*?)\n/g, '<h3 style="margin:12px 0 6px; font-size:1.1rem; font-weight:800; color:#1e1b2e;">$1</h3>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n- /g, '<br>• ');
      
    // Render mini cards for matched deals
    let shelfHtml = '';
    if (data.matched_deals && data.matched_deals.length > 0) {
      shelfHtml = `
        <div class="matched-deals-shelf">
          <div class="shelf-title">Znalezione okazje w gazetkach:</div>
          <div class="mini-deals-list">
            ${data.matched_deals.map(d => {
              const storeClass = `store-pill ${(d.store || '').toLowerCase()}`;
              const clickFn = d.image_url ? `onclick="openLightbox('${escapeHtml(d.image_url)}', '${escapeHtml(d.store)} - Gazetka (strona ${d.page_number || '1'})', '${escapeHtml(d.name)}')"` : '';
              return `
                <div class="mini-deal-card" ${clickFn}>
                  ${d.image_url ? `<img src="${escapeHtml(d.image_url)}" class="mini-deal-img" alt="">` : ''}
                  <div class="mini-deal-body">
                    <div class="mini-deal-name">${escapeHtml(d.name)}</div>
                    <div class="mini-deal-meta">
                      <span class="${storeClass}" style="font-size:0.65rem; padding:2px 6px;">${escapeHtml(d.store)}</span>
                      <span class="mini-deal-price">${escapeHtml(d.price)}</span>
                    </div>
                    ${d.date_badge ? `<span style="font-size:0.68rem; color:#6b21a8; font-weight:700;">⏰ ${escapeHtml(d.date_badge)}</span>` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }
    
    const botResponseHtml = `
      <div class="chat-msg bot-msg">
        <div class="bot-avatar">🤖</div>
        <div class="msg-bubble">
          <p>${replyHtml}</p>
          ${shelfHtml}
        </div>
      </div>
    `;
    chatBox.insertAdjacentHTML('beforeend', botResponseHtml);
    chatBox.scrollTop = chatBox.scrollHeight;
    
  } catch (err) {
    console.error('Assistant error:', err);
    const typingEl = document.getElementById(loadingId);
    if (typingEl) typingEl.remove();
    
    chatBox.insertAdjacentHTML('beforeend', `
      <div class="chat-msg bot-msg">
        <div class="bot-avatar">🤖</div>
        <div class="msg-bubble" style="color:#b91c1c;">
          Wystąpił błąd podczas rozmowy z asystentem. Spróbuj ponownie za chwilę.
        </div>
      </div>
    `);
  } finally {
    sendBtn.disabled = false;
    sendIcon.classList.remove('hidden');
    sendSpinner.classList.add('hidden');
  }
}
