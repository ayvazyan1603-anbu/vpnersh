// Telegram WebApp Initialization
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try {
    tg.setHeaderColor('#0a0d16');
    tg.setBackgroundColor('#0a0d16');
  } catch (e) {}
}

// Translations Data for Ersh VPN
const TRANSLATIONS = {
  en: {
    trial_pill: "⚡ INSTANT ACCESS",
    trial_title: "Free Trial Available",
    trial_desc: "High-speed VLESS Reality VPN. Zero logs, maximum privacy.",
    days: "days",
    devices: "devices",
    btn_activate: "Activate Free",
    tab_balance: "Balance",
    tab_referrals: "Referrals",
    sub_page_title: "Subscription",
    no_active_sub: "You don't have an active subscription",
    get_sub_title: "Get Subscription",
    get_sub_desc: "Choose a plan with CryptoBot or Balance",
    curr_balance: "Current Balance",
    promo_title: "Promo Code",
    enter_promo: "Enter promo code",
    btn_activate_promo: "Activate",
    topup_title: "Top Up Balance",
    ref_page_title: "Referral Program",
    total_refs: "Total Referrals",
    total_earnings: "Total Earnings",
    commission_rate: "First Bonus",
    your_ref_links: "Your Referral Link",
    btn_copy: "Copy Link",
    support_page_title: "Support",
    btn_new_ticket: "New Ticket",
    contact_support_title: "Contact Admin Directly",
    btn_contact: "Contact",
    your_tickets_title: "Your Tickets",
    no_tickets: "No tickets yet",
    nav_dash: "Dashboard",
    nav_sub: "Subscription",
    nav_balance: "Balance",
    nav_refs: "Referrals",
    nav_support: "Support",
    modal_tariffs_title: "Select Tariff Plan",
    tariff_1m: "1 Month",
    tariff_3m: "3 Months",
    tariff_6m: "6 Months",
    tariff_12m: "12 Months",
    popular_badge: "POPULAR",
    ticket_problem_lbl: "Describe your problem or question:",
    btn_submit_ticket: "Submit Ticket",
    toast_copied: "Referral link copied to clipboard!",
    toast_trial_success: "🎉 Free trial activated for 3 days!",
    toast_ticket_sent: "✅ Ticket submitted to admin!",
    toast_promo_success: "🎁 Promo code activated!",
    toast_promo_invalid: "❌ Invalid promo code"
  },
  ru: {
    trial_pill: "⚡ МГНОВЕННЫЙ ДОСТУП",
    trial_title: "Пробный период доступен",
    trial_desc: "Скоростной VLESS Reality VPN. Без логов и ограничений.",
    days: "дней",
    devices: "устройства",
    btn_activate: "Активировать бесплатно",
    tab_balance: "Баланс",
    tab_referrals: "Партнерка",
    sub_page_title: "Подписка",
    no_active_sub: "У вас нет активной подписки",
    get_sub_title: "Оформить подписку",
    get_sub_desc: "Выберите тариф (CryptoBot или Баланс)",
    curr_balance: "Текущий баланс",
    promo_title: "Промокод",
    enter_promo: "Введите промокод",
    btn_activate_promo: "Применить",
    topup_title: "Пополнить баланс",
    ref_page_title: "Реферальная программа",
    total_refs: "Всего рефералов",
    total_earnings: "Заработано всего",
    commission_rate: "Бонус за друга",
    your_ref_links: "Ваша реферальная ссылка",
    btn_copy: "Скопировать",
    support_page_title: "Поддержка",
    btn_new_ticket: "+ Создать тикет",
    contact_support_title: "Написать напрямую",
    btn_contact: "Написать",
    your_tickets_title: "Ваши тикеты",
    no_tickets: "Обращений пока нет",
    nav_dash: "Главная",
    nav_sub: "Подписка",
    nav_balance: "Баланс",
    nav_refs: "Партнерка",
    nav_support: "Поддержка",
    modal_tariffs_title: "Выберите тарифный план",
    tariff_1m: "1 Месяц",
    tariff_3m: "3 Месяца",
    tariff_6m: "6 Месяцев",
    tariff_12m: "12 Месяцев",
    popular_badge: "ХИТ",
    ticket_problem_lbl: "Опишите проблему или задайте вопрос:",
    btn_submit_ticket: "Отправить тикет",
    toast_copied: "Реферальная ссылка скопирована!",
    toast_trial_success: "🎉 Пробный период на 3 дня активирован!",
    toast_ticket_sent: "✅ Тикет успешно отправлен в поддержку!",
    toast_promo_success: "🎁 Промокод успешно активирован!",
    toast_promo_invalid: "❌ Неверный промокод"
  }
};

let currentLang = 'ru';

// App State
const state = {
  balance: 0.00,
  hasActiveSub: false,
  subExpires: null,
  referrals: 0,
  refEarnings: 0.00,
  tickets: [],
  theme: 'dark',
  prices: {},
  pendingInvoiceId: null
};

// DOM Elements
// Haptic feedback helper
function triggerHaptic(type = 'light') {
  if (tg?.HapticFeedback) {
    try {
      if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
      else if (type === 'warning') tg.HapticFeedback.notificationOccurred('warning');
      else tg.HapticFeedback.impactOccurred(type);
    } catch (e) {}
  }
}

// Toast notification
function showToast(msg) {
  const toast = document.getElementById('toast');
  if (toast) {
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2800);
  }
}

// Switch Theme
window.toggleTheme = function() {
  triggerHaptic('light');
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', state.theme);
  try {
    const col = state.theme === 'dark' ? '#0a0d16' : '#f0f4f9';
    tg?.setHeaderColor(col);
    tg?.setBackgroundColor(col);
  } catch (e) {}
};

// Switch Bottom Tabs
window.switchTab = function(tabName) {
  triggerHaptic('selection');
  
  const views = {
    dashboard: document.getElementById('view-dashboard'),
    subscription: document.getElementById('view-subscription'),
    balance: document.getElementById('view-balance'),
    referrals: document.getElementById('view-referrals'),
    support: document.getElementById('view-support'),
  };
  
  Object.keys(views).forEach(k => {
    if (views[k]) {
      views[k].classList.remove('active');
    }
  });

  document.querySelectorAll('.nav-item').forEach(n => {
    if (n.getAttribute('data-tab') === tabName) {
      n.classList.add('active');
    } else {
      n.classList.remove('active');
    }
  });

  if (views[tabName]) {
    views[tabName].classList.add('active');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
  
  if (tabName === 'support') {
    loadTickets();
  }
};

// Modals
window.openModal = function(modalId) {
  triggerHaptic('medium');
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('open'), 10);
  }
};

window.closeModal = function(modalId) {
  triggerHaptic('light');
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
    setTimeout(() => modal.style.display = 'none', 250);
  }
};

// Setup Navigation Events
function initNavButtons() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const tab = btn.getAttribute('data-tab');
      if (tab) {
        window.switchTab(tab);
      }
    });
  });
}

// Language Selector
window.addEventListener('DOMContentLoaded', () => {
  initNavButtons();

  const langSelector = document.getElementById('langSelector');
  const langDropdown = document.getElementById('langDropdown');

  if (langSelector && langDropdown) {
    langSelector.addEventListener('click', (e) => {
      e.stopPropagation();
      langDropdown.classList.toggle('show');
    });

    document.addEventListener('click', () => {
      langDropdown.classList.remove('show');
    });

    document.querySelectorAll('.lang-option').forEach(opt => {
      opt.addEventListener('click', (e) => {
        e.stopPropagation();
        const lang = opt.dataset.lang;
        setLanguage(lang);
        langDropdown.classList.remove('show');
      });
    });
  }
});

function setLanguage(lang) {
  currentLang = lang;
  document.getElementById('currentLang').innerText = lang.toUpperCase();
  document.getElementById('currentFlag').innerText = lang === 'ru' ? '🇷🇺' : '🇬🇧';

  const dict = TRANSLATIONS[lang];
  document.querySelectorAll('[data-t]').forEach(el => {
    const key = el.dataset.t;
    if (dict[key]) el.innerText = dict[key];
  });
  document.querySelectorAll('[data-t-ph]').forEach(el => {
    const key = el.dataset.tPh;
    if (dict[key]) el.placeholder = dict[key];
  });
}

// --- API Helper ---
async function apiCall(method, endpoint, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  } else if (tg?.initDataUnsafe?.user?.id) {
    headers['X-User-Id'] = tg.initDataUnsafe.user.id.toString();
  }

  const options = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const res = await fetch(endpoint, options);
    const data = await res.json();
    if (!res.ok || !data.ok) {
      const errMsg = data.error || data.detail || 'Ошибка';
      console.warn('API error:', endpoint, errMsg);
      return { ok: false, error: errMsg };
    }
    return data;
  } catch (e) {
    console.error('API network error:', endpoint, e);
    return { ok: false, error: 'network_error' };
  }
}

// --- Data Loading ---
async function loadUserData() {
  try {
    const user = await apiCall('GET', '/api/user');
    if (!user.ok) return; // не удалось загрузить
    state.balance = user.balance || 0;
    state.hasActiveSub = user.has_active_sub || false;
    state.subExpires = user.sub_active_until || user.active_until;
    state.vpnKey = user.vpn_key || '';
    state.referrals = user.referral_count !== undefined ? user.referral_count : (user.referrals_count || 0);
    state.refEarnings = user.referral_earnings || 0;
    state.trialUsed = user.trial_used || false;

    updateBalanceDisplay();
    const refLinkInput = document.getElementById('refLinkInput');
    if (refLinkInput) refLinkInput.value = user.referral_link || '';
    
    const refTotalCount = document.getElementById('refTotalCount');
    if (refTotalCount) refTotalCount.innerText = state.referrals;
    
    const dashRefCount = document.getElementById('dashRefCount');
    if (dashRefCount) dashRefCount.innerText = state.referrals;
    
    const refEarnings = document.getElementById('refEarnings');
    if (refEarnings) refEarnings.innerText = `+${state.refEarnings.toFixed(2)} ₽`;
    
    const dashRefEarned = document.getElementById('dashRefEarned');
    if (dashRefEarned) dashRefEarned.innerText = `+${state.refEarnings.toFixed(2)} ₽`;

    const subBox = document.getElementById('subStatusBox');
    if (subBox) {
      if (state.hasActiveSub) {
        let expText = state.subExpires || '';
        try {
          const d = new Date(state.subExpires);
          if (!isNaN(d.getTime())) {
            expText = d.toLocaleDateString(currentLang === 'ru' ? 'ru-RU' : 'en-US', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
          }
        } catch (e) {}

        subBox.innerHTML = `
          <div style="width: 70px; height: 70px; background: rgba(6, 182, 212, 0.15); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 20px; display: flex; align-items: center; justify-content: center; margin-bottom: 12px;">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
          </div>
          <div style="font-size: 18px; font-weight: 800; margin-bottom: 4px;">${user.sub_plan || 'VLESS Reality'}</div>
          <div style="font-size: 13.5px; color: #06b6d4; font-weight: 700; margin-bottom: 12px;">${currentLang === 'ru' ? 'Активна до' : 'Valid until'} ${expText}</div>
          ${state.vpnKey ? `
            <div style="width: 100%; text-align: left; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 10px 12px; margin-top: 8px;">
              <div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px; font-weight: 600;">${currentLang === 'ru' ? 'КЛЮЧ ПОДКЛЮЧЕНИЯ:' : 'VPN KEY:'}</div>
              <div style="font-size: 11px; color: #38bdf8; font-family: monospace; word-break: break-all; max-height: 48px; overflow-y: auto; margin-bottom: 8px;">${state.vpnKey}</div>
              <button class="btn btn-sm btn-full" style="background: rgba(6, 182, 212, 0.2); color: #38bdf8; border: 1px solid rgba(6, 182, 212, 0.4); font-size: 12px; padding: 6px 10px;" onclick="copyVpnKey()">${currentLang === 'ru' ? '📋 Скопировать ключ' : '📋 Copy Key'}</button>
            </div>
          ` : ''}
        `;
      } else {
        subBox.innerHTML = `
            <div class="empty-box-icon">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <p class="sub-status-text" id="subStatusText" data-t="no_active_sub">${TRANSLATIONS[currentLang].no_active_sub}</p>
        `;
      }
    }

    const heroCard = document.querySelector('.hero-card');
    if (heroCard) {
      heroCard.style.display = 'block';

      if (state.hasActiveSub) {
        let expText = state.subExpires || '';
        try {
          const d = new Date(state.subExpires);
          if (!isNaN(d.getTime())) {
            expText = d.toLocaleDateString(currentLang === 'ru' ? 'ru-RU' : 'en-US', { day: '2-digit', month: '2-digit', year: 'numeric' });
          }
        } catch (e) {}

        heroCard.innerHTML = `
          <div class="hero-shine"></div>
          <div class="trial-pill-tag" style="background: rgba(6, 182, 212, 0.2); color: #38bdf8;">🛡️ ${currentLang === 'ru' ? 'ЗАЩИТА АКТИВНА' : 'VPN ACTIVE'}</div>
          <h2 class="hero-title">${user.sub_plan || 'VLESS Reality'}</h2>
          <p class="hero-subtitle">${currentLang === 'ru' ? 'Подписка активна до' : 'Active until'} <b>${expText}</b></p>
          <div class="hero-stats-grid">
            <div class="stat-box">
              <div class="stat-val">∞</div>
              <div class="stat-lbl">GB</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-box">
              <div class="stat-val">3</div>
              <div class="stat-lbl">${currentLang === 'ru' ? 'устройства' : 'devices'}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-box">
              <div class="stat-val">1</div>
              <div class="stat-lbl">Гбит/с</div>
            </div>
          </div>
          <button class="btn btn-glow-action btn-full" onclick="switchTab('subscription')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
            <span>${currentLang === 'ru' ? 'Мой ключ и статус' : 'My Key & Status'}</span>
          </button>
        `;
      } else if (state.trialUsed) {
        heroCard.innerHTML = `
          <div class="hero-shine"></div>
          <div class="trial-pill-tag" style="background: rgba(99, 102, 241, 0.2); color: #a5b4fc;">🚀 ${currentLang === 'ru' ? 'ПРЕМИУМ ДОСТУП' : 'PREMIUM ACCESS'}</div>
          <h2 class="hero-title">${currentLang === 'ru' ? 'Оформить подписку' : 'Get Subscription'}</h2>
          <p class="hero-subtitle">${currentLang === 'ru' ? 'Безлимитный VPN от 149 ₽/мес' : 'Unlimited VPN from 149 ₽/mo'}</p>
          <div class="hero-stats-grid">
            <div class="stat-box">
              <div class="stat-val">∞</div>
              <div class="stat-lbl">GB</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-box">
              <div class="stat-val">3</div>
              <div class="stat-lbl">${currentLang === 'ru' ? 'устройства' : 'devices'}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-box">
              <div class="stat-val">от 149</div>
              <div class="stat-lbl">₽/мес</div>
            </div>
          </div>
          <button class="btn btn-glow-action btn-full" onclick="openModal('tariffsModal')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>${currentLang === 'ru' ? 'Выбрать тариф' : 'Choose Plan'}</span>
          </button>
        `;
      } else {
        heroCard.innerHTML = `
          <div class="hero-shine"></div>
          <div class="trial-pill-tag">${TRANSLATIONS[currentLang].trial_pill}</div>
          <h2 class="hero-title">${TRANSLATIONS[currentLang].trial_title}</h2>
          <p class="hero-subtitle">${TRANSLATIONS[currentLang].trial_desc}</p>
          <div class="hero-stats-grid">
            <div class="stat-box">
              <div class="stat-val">3</div>
              <div class="stat-lbl">${TRANSLATIONS[currentLang].days}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-box">
              <div class="stat-val">∞</div>
              <div class="stat-lbl">GB</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-box">
              <div class="stat-val">3</div>
              <div class="stat-lbl">${TRANSLATIONS[currentLang].devices}</div>
            </div>
          </div>
          <button class="btn btn-glow-action btn-full" id="activateFreeBtn" onclick="activateFreeTrial()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>${TRANSLATIONS[currentLang].btn_activate}</span>
          </button>
        `;
      }
    }
  } catch (e) {
    console.error('loadUserData error:', e);
  }
}

window.copyVpnKey = function() {
  triggerHaptic('success');
  if (state.vpnKey) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(state.vpnKey);
    }
    showToast(currentLang === 'ru' ? '🔑 Ключ скопирован в буфер!' : '🔑 Key copied to clipboard!');
  }
};

async function loadPrices() {
  try {
    const data = await apiCall('GET', '/api/prices');
    if (!data.ok) return;
    state.prices = data.prices || {};
    
    // Update modal cards
    const cards = document.querySelectorAll('.tariffs-list .tariff-card');
    if (cards.length >= 4) {
      const p1 = cards[0].querySelector('.tariff-price');
      const p3 = cards[1].querySelector('.tariff-price');
      const p6 = cards[2].querySelector('.tariff-price');
      const p12 = cards[3].querySelector('.tariff-price');
      if (p1) p1.innerText = `${state.prices['1'] || 149} ₽`;
      if (p3) p3.innerText = `${state.prices['3'] || 399} ₽`;
      if (p6) p6.innerText = `${state.prices['6'] || 749} ₽`;
      if (p12) p12.innerText = `${state.prices['12'] || 1399} ₽`;
    }
  } catch (e) {
    console.error('loadPrices error:', e);
  }
}

// Open Tariffs
document.getElementById('openTariffsBtn')?.addEventListener('click', () => {
  // Reset tariffs modal to original state if we navigated to payment options
  const tariffsList = document.querySelector('.tariffs-list');
  tariffsList.style.display = 'block';
  let opts = document.getElementById('paymentOptionsView');
  if(opts) opts.remove();
  openModal('tariffsModal');
});

// Select Tariff
window.selectTariff = function(months, priceStr) {
  triggerHaptic('medium');
  const price = state.prices[months] || parseInt(priceStr) || 0;
  
  const tariffsList = document.querySelector('.tariffs-list');
  tariffsList.style.display = 'none';

  let opts = document.getElementById('paymentOptionsView');
  if (opts) opts.remove();

  opts = document.createElement('div');
  opts.id = 'paymentOptionsView';
  opts.className = 'payment-options';
  opts.style.padding = '16px';
  opts.style.textAlign = 'center';
  opts.innerHTML = `
    <h4 style="margin-bottom: 12px; font-family: 'Plus Jakarta Sans', sans-serif; color: #f8fafc; font-size: 16px;">Выберите способ оплаты:</h4>
    ${state.balance >= price 
      ? `<button class="btn btn-glow-action btn-full mb-10" id="payBalanceBtn">💰 Оплатить с баланса (${price} ₽)</button>` 
      : `<div style="color: #ef4444; font-size: 13px; margin-bottom: 10px;">Недостаточно средств на балансе (${state.balance.toFixed(2)} ₽)</div>`
    }
    <button class="btn btn-glow-action btn-full mb-10" id="payFkBtn" style="background: linear-gradient(135deg, #06b6d4, #3b82f6);">💳 Картой РФ / СБП (${price} ₽)</button>
    <button class="btn btn-neon btn-full mb-10" id="payCryptoBtn">⚡ CryptoBot (${price} ₽)</button>
    <button class="btn btn-full mt-6" style="background: rgba(255,255,255,0.05); color: #94a3b8;" onclick="backToTariffs()">Назад</button>
  `;
  document.querySelector('#tariffsModal .modal-sheet').appendChild(opts);

  if (state.balance >= price) {
    document.getElementById('payBalanceBtn')?.addEventListener('click', async () => {
      const res = await apiCall('POST', '/api/buy_with_balance', { period: months.toString() });
      if (res.ok) {
        triggerHaptic('success');
        showToast(currentLang === 'ru' ? '✅ Тариф успешно активирован!' : '✅ Tariff activated successfully!');
        closeModal('tariffsModal');
        await loadUserData();
      } else {
        triggerHaptic('warning');
        showToast(res.error === 'insufficient_balance' 
          ? (currentLang === 'ru' ? '❌ Недостаточно средств' : '❌ Insufficient balance') 
          : (res.error || 'Ошибка'));
      }
    });
  }

  document.getElementById('payFkBtn')?.addEventListener('click', async () => {
    const res = await apiCall('POST', '/api/buy_with_freekassa', { period: months.toString() });
    if (res.ok && res.pay_url) {
      triggerHaptic('success');
      window.open(res.pay_url, '_blank');
      
      opts.innerHTML = `
        <h4 style="margin-bottom: 12px; font-family: 'Plus Jakarta Sans', sans-serif; color: #f8fafc; font-size: 16px;">Ожидание оплаты картой...</h4>
        <button class="btn btn-glow-action btn-full mb-10" id="checkFkSubBtn">Проверить оплату</button>
        <button class="btn btn-full" style="background: rgba(255,255,255,0.05); color: #94a3b8;" onclick="closeModal('tariffsModal')">Закрыть</button>
      `;
      document.getElementById('checkFkSubBtn')?.addEventListener('click', async () => {
        const checkRes = await apiCall('POST', '/api/check_fk_invoice', { invoice_id: res.invoice_id });
        if (checkRes.ok) {
          triggerHaptic('success');
          showToast(currentLang === 'ru' ? '🎉 Оплата получена! Подписка активирована.' : '🎉 Payment received!');
          closeModal('tariffsModal');
          await loadUserData();
        } else {
          triggerHaptic('warning');
          showToast(currentLang === 'ru' ? '⏳ Оплата еще не поступила' : 'Payment not received yet');
        }
      });
    } else {
      triggerHaptic('warning');
      showToast(res.error || 'Ошибка создания счёта');
    }
  });

  document.getElementById('payCryptoBtn')?.addEventListener('click', async () => {
    const res = await apiCall('POST', '/api/buy_with_crypto', { period: months.toString() });
    if (res.ok && res.pay_url) {
      triggerHaptic('success');
      window.open(res.pay_url, '_blank');
      
      opts.innerHTML = `
        <h4 style="margin-bottom: 12px; font-family: 'Plus Jakarta Sans', sans-serif; color: #f8fafc; font-size: 16px;">Ожидание оплаты CryptoBot...</h4>
        <button class="btn btn-glow-action btn-full mb-10" id="checkCryptoSubBtn">Проверить оплату</button>
        <button class="btn btn-full" style="background: rgba(255,255,255,0.05); color: #94a3b8;" onclick="closeModal('tariffsModal')">Закрыть</button>
      `;
      document.getElementById('checkCryptoSubBtn')?.addEventListener('click', async () => {
        const checkRes = await apiCall('POST', '/api/check_invoice', { invoice_id: res.invoice_id });
        if (checkRes.ok) {
          triggerHaptic('success');
          showToast(currentLang === 'ru' ? '🎉 Оплата получена! Подписка активирована.' : '🎉 Payment received!');
          closeModal('tariffsModal');
          await loadUserData();
        } else {
          triggerHaptic('warning');
          showToast(currentLang === 'ru' ? '⏳ Оплата еще не поступила' : 'Payment not received yet');
        }
      });
    } else {
      triggerHaptic('warning');
      showToast(res.error || 'Ошибка создания счёта');
    }
  });
}

window.backToTariffs = function() {
  const opts = document.getElementById('paymentOptionsView');
  if (opts) opts.remove();
  const tariffsList = document.querySelector('.tariffs-list');
  if (tariffsList) tariffsList.style.display = 'block';
}

// Promo Code
document.getElementById('applyPromoBtn')?.addEventListener('click', async () => {
  const input = document.getElementById('promoInput');
  const code = input?.value?.trim();
  if (code) {
    const res = await apiCall('POST', '/api/promo', { code });
    if (res.ok) {
      triggerHaptic('success');
      showToast(res.reward_desc || TRANSLATIONS[currentLang].toast_promo_success);
      input.value = '';
      if (res.new_balance !== undefined) {
        state.balance = res.new_balance;
        updateBalanceDisplay();
      }
      await loadUserData();
    } else {
      triggerHaptic('warning');
      showToast(res.error || TRANSLATIONS[currentLang].toast_promo_invalid);
    }
  }
});

function updateBalanceDisplay() {
  const dashBal = document.getElementById('dashBalance');
  const pageBal = document.getElementById('pageBalance');
  if (dashBal) dashBal.innerText = `${state.balance.toFixed(2)} ₽`;
  if (pageBal) pageBal.innerText = `${state.balance.toFixed(2)} ₽`;
}

// Copy Referral Link
document.getElementById('copyRefBtn')?.addEventListener('click', () => {
  triggerHaptic('success');
  const refLink = document.getElementById('refLinkInput')?.value;
  if (refLink && navigator.clipboard) {
    navigator.clipboard.writeText(refLink);
  }
  showToast(TRANSLATIONS[currentLang].toast_copied);
});

// Tickets
document.getElementById('newTicketBtn')?.addEventListener('click', () => {
  openModal('ticketModal');
});

document.getElementById('sendTicketBtn')?.addEventListener('click', async () => {
  const txt = document.getElementById('ticketTextInput')?.value?.trim();
  if (!txt) return;

  const res = await apiCall('POST', '/api/tickets', { text: txt });
  if (res.ok) {
    triggerHaptic('success');
    document.getElementById('ticketTextInput').value = '';
    closeModal('ticketModal');
    showToast(TRANSLATIONS[currentLang].toast_ticket_sent);
    await loadTickets();
  } else {
    triggerHaptic('warning');
    showToast(res.error || 'Ошибка');
  }
});

async function loadTickets() {
  try {
    const data = await apiCall('GET', '/api/tickets');
    state.tickets = data.tickets || [];
    renderTickets();
  } catch (e) {}
}

function renderTickets() {
  const container = document.getElementById('ticketsContainer');
  if (!container) return;
  if (state.tickets.length === 0) {
    container.innerHTML = `
      <div class="empty-icon-circle">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
      </div>
      <p class="empty-text">${TRANSLATIONS[currentLang].no_tickets}</p>
    `;
  } else {
    container.innerHTML = state.tickets.map(t => {
      const isAnswered = t.status === 'answered' || t.status === 'closed';
      const statusText = t.status === 'open' ? '⏳ В обработке' : (t.status === 'answered' ? '💬 Ответ получен' : '✅ Закрыт');
      const reply = t.admin_reply || t.answer;
      return `
        <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 12px 14px; margin-bottom: 8px; text-align: left; width: 100%;">
          <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-bottom: 4px;">
            <span>Тикет #${t.id || '-'}</span>
            <span>${statusText}</span>
          </div>
          <div style="font-size: 14px; font-weight: 600; color: #f8fafc;">${t.text}</div>
          ${reply ? `<div style="margin-top: 8px; font-size: 13px; color: #06b6d4; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.05);"><b>Ответ поддержки:</b><br>${reply}</div>` : ''}
        </div>
      `;
    }).join('');
  }
}

// Deposit Modal
document.getElementById('openDepositModal')?.addEventListener('click', () => {
  openModal('depositModal');
  // reset view just in case
  const def = document.getElementById('depositContentDefault');
  if (def) def.style.display = 'block';
  const checkView = document.getElementById('depositCheckView');
  if (checkView) checkView.style.display = 'none';
});

// Setup deposit DOM
window.addEventListener('DOMContentLoaded', () => {
  const depContent = document.querySelector('.deposit-content');
  if (depContent && !document.getElementById('depositContentDefault')) {
    depContent.innerHTML = `
      <div id="depositContentDefault">
        <label class="form-lbl">Выберите сумму:</label>
        <div class="amount-chips">
          <button class="chip" onclick="setDepositAmount(150)">150 ₽</button>
          <button class="chip active" onclick="setDepositAmount(300)">300 ₽</button>
          <button class="chip" onclick="setDepositAmount(500)">500 ₽</button>
          <button class="chip" onclick="setDepositAmount(1000)">1000 ₽</button>
        </div>
        <input type="number" id="depositAmountInput" class="input-field mt-12" value="300" placeholder="Произвольная сумма (₽)">
        <button class="btn btn-glow-action btn-full mt-16" id="proceedFkPayBtn" style="background: linear-gradient(135deg, #06b6d4, #3b82f6);">💳 Оплатить картой РФ / СБП</button>
        <button class="btn btn-neon btn-full mt-10" id="proceedCryptoPayBtn">⚡ Оплатить через CryptoBot</button>
      </div>
      <div id="depositCheckView" style="display:none; text-align:center; padding-top: 20px;">
        <h4 style="margin-bottom: 12px; font-family: 'Plus Jakarta Sans', sans-serif; color: #f8fafc; font-size: 16px;" id="depositCheckTitle">Ожидание оплаты...</h4>
        <button class="btn btn-glow-action btn-full mb-10" id="checkDepositBtn">Проверить оплату</button>
        <button class="btn btn-full" style="background: rgba(255,255,255,0.05); color: #94a3b8;" onclick="closeModal('depositModal')">Закрыть</button>
      </div>
    `;
    
    document.getElementById('proceedFkPayBtn')?.addEventListener('click', async () => {
      const amt = parseFloat(document.getElementById('depositAmountInput')?.value);
      if(!amt || amt <= 0) return;
      const res = await apiCall('POST', '/api/deposit_freekassa', { amount: amt });
      if (res.ok && res.pay_url) {
        triggerHaptic('success');
        window.open(res.pay_url, '_blank');
        state.pendingInvoiceId = res.invoice_id;
        state.pendingProvider = 'freekassa';
        
        document.getElementById('depositContentDefault').style.display = 'none';
        document.getElementById('depositCheckView').style.display = 'block';
        document.getElementById('depositCheckTitle').innerText = 'Ожидание оплаты картой...';
      } else {
        triggerHaptic('warning');
        showToast(res.error || 'Ошибка создания счёта');
      }
    });

    document.getElementById('proceedCryptoPayBtn')?.addEventListener('click', async () => {
      const amt = parseFloat(document.getElementById('depositAmountInput')?.value);
      if(!amt || amt <= 0) return;
      const res = await apiCall('POST', '/api/deposit', { amount: amt });
      if (res.ok && res.pay_url) {
        triggerHaptic('success');
        window.open(res.pay_url, '_blank');
        state.pendingInvoiceId = res.invoice_id;
        state.pendingProvider = 'cryptobot';
        
        document.getElementById('depositContentDefault').style.display = 'none';
        document.getElementById('depositCheckView').style.display = 'block';
        document.getElementById('depositCheckTitle').innerText = 'Ожидание оплаты CryptoBot...';
      } else {
        triggerHaptic('warning');
        showToast(res.error || 'Ошибка создания счёта');
      }
    });

    document.getElementById('checkDepositBtn')?.addEventListener('click', async () => {
      if(!state.pendingInvoiceId) return;
      const endpoint = state.pendingProvider === 'freekassa' ? '/api/check_fk_invoice' : '/api/check_invoice';
      const res = await apiCall('POST', endpoint, { invoice_id: state.pendingInvoiceId });
      if(res.ok) {
        triggerHaptic('success');
        showToast(currentLang === 'ru' ? '🎉 Баланс успешно пополнен!' : '🎉 Balance successfully topped up!');
        closeModal('depositModal');
        await loadUserData();
      } else {
        triggerHaptic('warning');
        showToast(currentLang === 'ru' ? '⏳ Оплата еще не поступила' : 'Payment not received yet');
      }
    });
  }
});

window.setDepositAmount = function(amount) {
  triggerHaptic('light');
  document.getElementById('depositAmountInput').value = amount;
  document.querySelectorAll('.amount-chips .chip').forEach(c => {
    c.classList.remove('active');
    if (c.innerText.includes(amount.toString())) {
      c.classList.add('active');
    }
  });
}

// Initialize
setLanguage('ru');
window.addEventListener('load', () => {
  loadUserData();
  loadPrices();
});
