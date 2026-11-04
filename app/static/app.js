let activeTab = 'meals';
let filterStore = 'Wszystkie';
let filterCategory = 'Wszystkie';
let activePlanData = null;
let pollTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  fetchStatus();
  loadMealPlan();
  loadPromotions();
  
  // Periodic status poll every 10 seconds
  setInterval(fetchStatus, 10000);
});

function switchTab(tabId) {
  activeTab = tabId;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  
  const buttons = Array.from(document.querySelectorAll('.tab-btn'));
  if (tabId === 'meals') buttons[0]?.classList.add('active');
  if (tabId === 'deals') buttons[1]?.classList.add('active');
  if (tabId === 'shopping') buttons[2]?.classList.add('active');
  
  const target = document.getElementById(`tab-${tabId}`);
  if (target) target.classList.add('active');
  
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
    const refreshBtn = document.getElementById('refreshBtn');
    
    if (data.is_syncing) {
      dot.className = 'status-dot syncing';
      text.innerText = 'Trwa sprawdzanie gazetek i układanie menu...';
      refreshBtn.disabled = true;
      refreshBtn.querySelector('.btn-text').innerText = 'Przetwarzanie AI...';
    } else {
      dot.className = 'status-dot';
      refreshBtn.disabled = false;
      refreshBtn.querySelector('.btn-text').innerText = 'Generuj Nowy Plan';
      
      if (data.last_sync) {
        const timeStr = data.last_sync.timestamp ? new Date(data.last_sync.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
        text.innerText = `Ostatnia aktualizacja: ${timeStr} (${data.last_sync.deals_count} promocji w bazie)`;
      } else {
        text.innerText = 'Baza gotowa. Kliknij przycisk, aby wygenerować pierwsze menu.';
      }
    }
  } catch (err) {
    console.error('Error fetching status:', err);
  }
}

async function triggerRefresh() {
  const refreshBtn = document.getElementById('refreshBtn');
  refreshBtn.disabled = true;
  refreshBtn.querySelector('.btn-text').innerText = 'Rozpoczynanie...';
  
  try {
    const res = await fetch('/api/refresh', { method: 'POST' });
    const data = await res.json();
    console.log('Refresh response:', data);
    
    // Poll for status
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
    }, 3000);
    
    fetchStatus();
  } catch (err) {
    console.error('Error triggering refresh:', err);
    refreshBtn.disabled = false;
  }
}

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
      summaryText.innerText = data.plan.weekly_summary || "Plan obiadów na bazie aktualnych promocji w Lidl, Biedronka i Kaufland.";
      
      const dinners = data.plan.meals.filter(m => m.type !== 'Zupa' && !m.day.toLowerCase().includes('zupa'));
      const soups = data.plan.meals.filter(m => m.type === 'Zupa' || m.day.toLowerCase().includes('zupa'));
      
      container.innerHTML = dinners.map(m => createMealCardHtml(m)).join('');
      soupsContainer.innerHTML = soups.map(m => createMealCardHtml(m)).join('');
      
      renderShoppingList(activePlanData);
    } else {
      summaryCard.classList.add('hidden');
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted)">
          <p style="font-size: 1.1rem; margin-bottom: 12px;">Nie masz jeszcze wygenerowanego planu na ten tydzień.</p>
          <button class="btn btn-primary" onclick="triggerRefresh()">⚡ Kliknij tutaj, aby pobrać promocje i stworzyć menu</button>
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
  const equipClass = `equip-${(meal.equipment || 'airfryer').toLowerCase()}`;
  const equipIcon = {
    'airfryer': '⚡',
    'piekarnik': '🔥',
    'patelnia': '🍳',
    'garnek': '🍲'
  }[(meal.equipment || '').toLowerCase()] || '🍳';

  const promoItemsHtml = (meal.discounted_ingredients || []).map(ing => {
    const storeClass = `store-${(ing.store || '').toLowerCase()}`;
    return `
      <div class="promo-tag">
        <span>${escapeHtml(ing.name)}</span>
        <div>
          <span class="store-badge ${storeClass}">${escapeHtml(ing.store)}</span>
          ${ing.price ? `<strong>${escapeHtml(ing.price)}</strong>` : ''}
        </div>
      </div>
    `;
  }).join('');

  const pantryText = (meal.pantry_ingredients || []).join(', ');

  const instructionsHtml = (meal.instructions || []).map(step => `<li>${escapeHtml(step)}</li>`).join('');

  return `
    <article class="meal-card">
      <div class="meal-header">
        <span class="day-badge">${escapeHtml(meal.day)}</span>
        <span class="equipment-badge ${equipClass}">${equipIcon} ${escapeHtml(meal.equipment)}</span>
      </div>

      <div>
        <h3 class="meal-title">${escapeHtml(meal.title)}</h3>
        ${meal.prep_time ? `<span class="meal-time">⏱️ Czas przygotowania: ${escapeHtml(meal.prep_time)}</span>` : ''}
      </div>

      <div class="ingredients-block">
        <span class="ing-title">Przecenione składniki ze sklepu:</span>
        <div class="promo-tags">
          ${promoItemsHtml || '<span style="font-size:0.8rem; color:var(--text-dim)">Standardowe składniki</span>'}
        </div>
      </div>

      ${pantryText ? `
      <div class="ingredients-block">
        <span class="ing-title">Ze spiżarni / domowe:</span>
        <div class="pantry-tags">${escapeHtml(pantryText)}</div>
      </div>
      ` : ''}

      ${instructionsHtml ? `
      <details class="instructions-details">
        <summary>📖 Pokaż przepis krok po kroku</summary>
        <ol class="instructions-list">
          ${instructionsHtml}
        </ol>
      </details>
      ` : ''}
    </article>
  `;
}

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
        const storeClass = `store-${(d.store || '').toLowerCase()}`;
        return `
          <div class="deal-card">
            <div class="deal-top">
              <span class="deal-name">${escapeHtml(d.name)}</span>
              <span class="store-badge ${storeClass}">${escapeHtml(d.store)}</span>
            </div>
            <div class="deal-bottom">
              <span class="deal-price">${escapeHtml(d.price)}</span>
              <span class="deal-dates">${d.category}</span>
            </div>
          </div>
        `;
      }).join('');
    } else {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted)">
          Brak promocji spełniających kryteria.
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
    document.querySelectorAll('#storeFilters .pill').forEach(b => {
      b.classList.toggle('active', b.innerText === value);
    });
  } else if (type === 'category') {
    filterCategory = value;
    document.querySelectorAll('#categoryFilters .pill').forEach(b => {
      b.classList.toggle('active', b.innerText.includes(value));
    });
  }
  loadPromotions();
}

function renderShoppingList(plan) {
  const container = document.getElementById('shoppingListContainer');
  if (!plan || !plan.meals) {
    container.innerHTML = '<p style="color:var(--text-muted)">Brak wygenerowanego planu.</p>';
    return;
  }

  // Group discounted items by store
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
    const storeClass = `store-${store.toLowerCase()}`;
    const items = Array.from(itemsSet);

    html += `
      <div class="store-column">
        <div class="store-column-header">
          <span class="store-column-title">${escapeHtml(store)}</span>
          <span class="store-badge ${storeClass}">${items.length} pozycji</span>
        </div>
        <div class="shopping-items-list">
          ${items.map(item => {
            const isChecked = checkedItems.includes(item);
            return `
              <label class="shopping-item ${isChecked ? 'checked' : ''}">
                <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleShoppingItem('${escapeHtml(item)}', this)">
                <span>${escapeHtml(item)}</span>
              </label>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = html || '<p style="color:var(--text-muted)">Brak przecenionych składników do kupienia.</p>';
}

function toggleShoppingItem(item, checkbox) {
  let checkedItems = JSON.parse(localStorage.getItem('checked_shopping_items') || '[]');
  if (checkbox.checked) {
    if (!checkedItems.includes(item)) checkedItems.push(item);
    checkbox.closest('.shopping-item').classList.add('checked');
  } else {
    checkedItems = checkedItems.filter(i => i !== item);
    checkbox.closest('.shopping-item').classList.remove('checked');
  }
  localStorage.setItem('checked_shopping_items', JSON.stringify(checkedItems));
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
