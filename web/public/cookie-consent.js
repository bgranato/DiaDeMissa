(() => {
  const STORAGE_KEY = 'diademissa_cookie_preferencias_v1';
  const DISMISS_KEY = 'diademissa_cookie_dialogo_fechado';
  const MEASUREMENT_ID = 'G-T4MBFSPFTC';

  function lerPreferencia() {
    try {
      const valor = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      return valor && typeof valor.analytics === 'boolean' ? valor : null;
    } catch { return null; }
  }

  function carregarAnalytics() {
    if (document.querySelector(`script[data-dia-de-missa-analytics="${MEASUREMENT_ID}"]`)) return;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag() { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', MEASUREMENT_ID);
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`;
    script.dataset.diaDeMissaAnalytics = MEASUREMENT_ID;
    document.head.appendChild(script);
  }

  function salvar(analytics) {
    const preferencia = { analytics: Boolean(analytics), atualizadoEm: new Date().toISOString() };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferencia));
    sessionStorage.removeItem(DISMISS_KEY);
    if (preferencia.analytics) carregarAnalytics();
    window.dispatchEvent(new CustomEvent('diademissa:cookie-preferencias', { detail: preferencia }));
    return preferencia;
  }

  function deveExibirAviso() {
    return window.location.hash === '#cookies' || (!lerPreferencia() && sessionStorage.getItem(DISMISS_KEY) !== 'true');
  }

  function criarAviso() {
    if (!deveExibirAviso() || document.getElementById('dm-cookie-dialog')) return;
    const dialog = document.createElement('section');
    dialog.id = 'dm-cookie-dialog';
    dialog.className = 'dm-cookie-dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'dm-cookie-title');
    dialog.innerHTML = `
      <div class="dm-cookie-card">
        <button type="button" class="dm-cookie-close" aria-label="Fechar preferências de cookies">×</button>
        <strong id="dm-cookie-title">Cookies</strong>
        <p>Usamos o armazenamento necessário para o funcionamento e suas preferências. Com sua autorização, usamos o Google Analytics para entender, de forma agregada, como o Dia de Missa é utilizado.</p>
        <div class="dm-cookie-actions">
          <button type="button" class="dm-cookie-reject">Recusar cookies estatísticos</button>
          <button type="button" class="dm-cookie-accept">Aceitar cookies estatísticos</button>
          <button type="button" class="dm-cookie-settings" aria-expanded="false">Personalizar</button>
        </div>
        <div class="dm-cookie-details" data-open="false">
          <label><input type="checkbox" class="dm-cookie-analytics" /> <span><strong>Cookies estatísticos</strong><br />Opcional: permite medir, de forma agregada, como o site é utilizado.</span></label>
          <div class="dm-cookie-actions"><button type="button" class="dm-cookie-save">Salvar preferência</button></div>
        </div>
      </div>`;
    dialog.querySelector('.dm-cookie-reject').addEventListener('click', () => { salvar(false); dialog.remove(); });
    dialog.querySelector('.dm-cookie-accept').addEventListener('click', () => { salvar(true); dialog.remove(); });
    dialog.querySelector('.dm-cookie-close').addEventListener('click', () => { sessionStorage.setItem(DISMISS_KEY, 'true'); dialog.remove(); });
    const details = dialog.querySelector('.dm-cookie-details');
    const settings = dialog.querySelector('.dm-cookie-settings');
    const analytics = dialog.querySelector('.dm-cookie-analytics');
    analytics.checked = Boolean(lerPreferencia()?.analytics);
    settings.addEventListener('click', () => {
      const aberto = details.dataset.open !== 'true';
      details.dataset.open = String(aberto);
      settings.setAttribute('aria-expanded', String(aberto));
    });
    dialog.querySelector('.dm-cookie-save').addEventListener('click', () => { salvar(analytics.checked); dialog.remove(); });
    document.body.appendChild(dialog);
  }

  window.DiaDeMissaCookies = {
    lerPreferencia,
    salvar,
    analyticsAtivo: () => Boolean(lerPreferencia()?.analytics),
  };

  if (lerPreferencia()?.analytics) carregarAnalytics();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', criarAviso, { once: true });
  else criarAviso();
})();
