let activeTab = 'meals';
let filterStore = 'Wszystkie';
let filterCategory = 'Wszystkie';
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
    const btns = document.querySelectorAll('.segment-btn');
    if (tabId === 'meals') btns[0]?.classList.add('active');
    if (tabId === 'deals') btns[1]?.classList.add('active');
    if (tabId === 'shopping') btns[2]?.classList.add('active');
  }
  
  const pane = document.getElementById(`tab-${tabId}`);
  if (pane) pane.classList.add('active');
  
  if (tabId === 'shopping' && activePlanData) {
    renderShoppingList(activePlanData);
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
      summaryText.innerText = data.plan.weekly_summary || "Zdrowe, zbilansowane obiady z czystym składem bazujące na bieżących przecenach w dyskontach.";
      
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
          <span class="day-pill">${escapeHtml(meal.day)}</span>
          <span class="gear-pill ${gearClass}">${gearIcon} ${escapeHtml(meal.equipment)}</span>
        </div>

        <h3 class="dish-heading">${escapeHtml(meal.title)}</h3>

        <div class="time-row">
          ${meal.prep_time ? `<span class="prep-time">⏱️ ${escapeHtml(meal.prep_time)}</span>` : ''}
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
  
  try {
    const params = new URLSearchParams();
    if (filterStore !== 'Wszystkie') params.append('store', filterStore);
    if (filterCategory !== 'Wszystkie') params.append('category', filterCategory);
    
    const res = await fetch(`/api/promotions?${params.toString()}`);
    const data = await res.json();
    
    if (data.promotions && data.promotions.length > 0) {
      container.innerHTML = data.promotions.map(d => {
        const storeClass = `store-pill ${(d.store || '').toLowerCase()}`;
        const nutriHtml = renderNutriScoreHtml(d.nutri_score || 'A');
        const isClean = (d.clean_label || 'CLEAN') === 'CLEAN';
        const cleanClass = isClean ? 'clean' : 'processed';
        const cleanText = isClean ? '🌿 Czysty Skład' : '⚠️ Przetworzone';
        
        const hasImg = d.image_url && d.image_url.startsWith('http');
        const imgBtn = hasImg ? `
          <button class="flyer-thumb-btn" onclick="openLightbox('${escapeHtml(d.image_url)}', '${escapeHtml(d.store)} - Gazetka (strona ${d.page_number || '1'})', '${escapeHtml(d.name)}')">
            🔍 Gazetka
          </button>
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
                ${imgBtn}
              </div>
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
        <div style="grid-column: 1/-1; text-align: center; padding: 48px; background:#fff; border-radius:24px; color:var(--text-secondary)">
          Brak promocji spełniających wybrane kryteria.
        </div>
      `;
    }
  } catch (err) {
    console.error('Error loading promotions:', err);
  }
}

function setFilter(type, value) {
  if (type === 'store') {
    filterStore = value;
    document.querySelectorAll('#storeFilters .pill-item').forEach(b => {
      b.classList.toggle('active', b.innerText === value);
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
