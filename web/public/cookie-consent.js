(() => {
  const STORAGE_KEY = 'diademissa_cookie_preferencias_v1';
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
    if (preferencia.analytics) carregarAnalytics();
    window.dispatchEvent(new CustomEvent('diademissa:cookie-preferencias', { detail: preferencia }));
    return preferencia;
  }

  function criarAviso() {
    if (lerPreferencia() || document.getElementById('dm-cookie-dialog')) return;
    const dialog = document.createElement('section');
    dialog.id = 'dm-cookie-dialog';
    dialog.className = 'dm-cookie-dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'dm-cookie-title');
    dialog.innerHTML = `
      <div class="dm-cookie-card">
        <strong id="dm-cookie-title">Privacidade e cookies</strong>
        <p>Usamos o armazenamento necessário para o funcionamento e suas preferências. Com sua autorização, usamos o Google Analytics para entender, de forma agregada, como o Dia de Missa é utilizado.</p>
        <div class="dm-cookie-actions">
          <button type="button" class="dm-cookie-reject">Recusar cookies estatísticos</button>
          <button type="button" class="dm-cookie-accept">Aceitar cookies estatísticos</button>
          <a class="dm-cookie-settings" href="/controle-de-cookies.html">Controlar cookies</a>
        </div>
      </div>`;
    dialog.querySelector('.dm-cookie-reject').addEventListener('click', () => { salvar(false); dialog.remove(); });
    dialog.querySelector('.dm-cookie-accept').addEventListener('click', () => { salvar(true); dialog.remove(); });
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
