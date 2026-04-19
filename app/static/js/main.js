// ═══════════════════════════════════════════════════════════════
//  TEMPEST — Main JS
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

  // ── 1. Navbar scroll tint ──────────────────────────────────
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.style.background = window.scrollY > 40
        ? 'rgba(0,0,0,0.98)'
        : 'rgba(0,0,0,0.9)';
    }, { passive: true });
  }

  // ── 2. User dropdown — click-based, not :hover ─────────────
  const userMenuBtn  = document.getElementById('userMenuBtn');
  const userDropdown = document.getElementById('userDropdown');
  const userChevron  = document.getElementById('userChevron');

  if (userMenuBtn && userDropdown) {
    // Toggle on button click
    userMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = userDropdown.classList.toggle('open');
      userMenuBtn.setAttribute('aria-expanded', String(open));
      if (userChevron) userChevron.style.transform = open ? 'rotate(180deg)' : '';
    });

    // Allow click inside dropdown without closing
    userDropdown.addEventListener('click', (e) => e.stopPropagation());

    // Close on outside click
    document.addEventListener('click', () => {
      userDropdown.classList.remove('open');
      userMenuBtn.setAttribute('aria-expanded', 'false');
      if (userChevron) userChevron.style.transform = '';
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        userDropdown.classList.remove('open');
        userMenuBtn.setAttribute('aria-expanded', 'false');
        if (userChevron) userChevron.style.transform = '';
      }
    });
  }

  // ── 3. Mobile hamburger ────────────────────────────────────
  const hamburger = document.getElementById('hamburger');
  const navLinks  = document.querySelector('.nav-links');
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      const visible = navLinks.style.display === 'flex';
      Object.assign(navLinks.style, {
        display:       visible ? 'none' : 'flex',
        flexDirection: 'column',
        position:      'absolute',
        top:           '64px',
        left:          '0',
        right:         '0',
        background:    '#0a0a0a',
        padding:       '20px 24px',
        borderBottom:  '1px solid rgba(255,255,255,0.08)',
        zIndex:        '999',
      });
    });
  }

  // ── 4. Flash auto-dismiss ─────────────────────────────────
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => el.remove(), 5000);
  });

  // ── 5. Size selector ──────────────────────────────────────
  document.querySelectorAll('.size-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.size-grid')
         .querySelectorAll('.size-btn')
         .forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      const hidden  = document.getElementById('selected-size');
      const display = document.getElementById('size-display');
      if (hidden)  hidden.value      = btn.dataset.size;
      if (display) display.textContent = btn.dataset.size;
    });
  });

  // ── 6. Cart quantity buttons ──────────────────────────────
  document.querySelectorAll('.qty-up').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.cart-qty').querySelector('.qty-input');
      input.value = parseInt(input.value, 10) + 1;
      input.closest('form').submit();
    });
  });
  document.querySelectorAll('.qty-down').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.cart-qty').querySelector('.qty-input');
      const next  = parseInt(input.value, 10) - 1;
      if (next >= 0) { input.value = next; input.closest('form').submit(); }
    });
  });

  // ── 7. Admin tabs ─────────────────────────────────────────
  document.querySelectorAll('.admin-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.admin-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.panel)?.classList.add('active');
    });
  });

  // ── 8. Demo user autofill (login page) ────────────────────
  document.querySelectorAll('.demo-card').forEach(card => {
    card.addEventListener('click', () => {
      const emailInput = document.getElementById('email');
      const passInput  = document.getElementById('password');
      if (emailInput) emailInput.value = card.dataset.email;
      if (passInput)  passInput.value  = card.dataset.pass;
    });
  });

  // ── 9. Dynamic payment fields (checkout) ─────────────────
  function showPaymentFields(method) {
    document.querySelectorAll('.payment-fields')
            .forEach(el => { el.style.display = 'none'; });
    const target = document.getElementById('fields-' + method);
    if (target) target.style.display = 'block';
  }

  const radios = document.querySelectorAll('input[name="payment"]');
  if (radios.length) {
    radios.forEach(r => r.addEventListener('change', () => showPaymentFields(r.value)));
    const checked = document.querySelector('input[name="payment"]:checked');
    if (checked) showPaymentFields(checked.value);
  }

  // ── 10. Checkout client-side validation ───────────────────
  const checkoutForm = document.querySelector('.checkout-form');
  if (checkoutForm) {
    checkoutForm.addEventListener('submit', (e) => {
      const payment = (document.querySelector('input[name="payment"]:checked') || {}).value;
      const errors  = [];

      const val = name => (document.querySelector(`[name="${name}"]`)?.value || '').trim();

      if (!val('name'))    errors.push('El nombre es obligatorio.');
      if (!val('phone'))   errors.push('El teléfono es obligatorio.');
      if (!val('address')) errors.push('La dirección es obligatoria.');
      if (!val('city'))    errors.push('La ciudad es obligatoria.');

      if (payment === 'tarjeta') {
        if (!val('card_number')) errors.push('Número de tarjeta obligatorio.');
        if (!val('card_name'))   errors.push('Nombre del titular obligatorio.');
        if (!val('card_expiry')) errors.push('Fecha de expiración obligatoria.');
        if (!val('card_cvv'))    errors.push('CVV obligatorio.');
      } else if (payment === 'nequi') {
        if (!val('nequi_phone')) errors.push('Número Nequi obligatorio.');
      } else if (payment === 'pse') {
        if (!val('pse_bank'))    errors.push('Banco PSE obligatorio.');
        if (!val('pse_account')) errors.push('Tipo de cuenta PSE obligatorio.');
      }

      if (errors.length) {
        e.preventDefault();
        let box = document.getElementById('js-errors');
        if (!box) {
          box = document.createElement('div');
          box.id = 'js-errors';
          box.style.cssText = [
            'background:rgba(220,50,50,.12)',
            'border:1px solid rgba(220,50,50,.4)',
            'border-radius:4px',
            'padding:16px',
            'margin-bottom:24px',
          ].join(';');
          checkoutForm.prepend(box);
        }
        box.innerHTML =
          '<p style="font-family:\'Barlow Condensed\',sans-serif;font-weight:700;' +
          'font-size:.8rem;letter-spacing:.15em;color:#ff5555;margin-bottom:8px;">' +
          'CORRIGE LOS SIGUIENTES ERRORES:</p>' +
          errors.map(err =>
            `<p style="font-size:.82rem;color:#ff7777;margin:4px 0;">— ${err}</p>`
          ).join('');
        box.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  }

  // ── 11. Scroll reveal ────────────────────────────────────
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity   = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.product-card, .exp-card, .value-card').forEach(el => {
    el.style.opacity    = '0';
    el.style.transform  = 'translateY(20px)';
    el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    observer.observe(el);
  });

});
