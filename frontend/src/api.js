// Envoltorio sobre la conexión WebSocket de Home Assistant.
export class Api {
  constructor() {
    this.hass = null;
    // identifica esta pestaña: el servidor lo devuelve como `origin` en los eventos
    this.clientId = (crypto.randomUUID?.() ?? String(Math.random()).slice(2));
  }

  call(type, payload = {}) {
    return this.hass.callWS({ type: `weekly_shopper/${type}`, client_id: this.clientId, ...payload });
  }

  subscribe(week, callback) {
    return this.hass.connection.subscribeMessage(callback, {
      type: 'weekly_shopper/subscribe', week, client_id: this.clientId,
    });
  }

  async upload(file) {
    const body = new FormData();
    body.append('file', file, file.name);
    const response = await this.hass.fetchWithAuth(
      `/api/weekly_shopper/import?client_id=${encodeURIComponent(this.clientId)}`, { method: 'POST', body });
    const result = await response.json();
    if (!response.ok) throw Object.assign(new Error(result.message), { code: result.code });
    return result;
  }
}
