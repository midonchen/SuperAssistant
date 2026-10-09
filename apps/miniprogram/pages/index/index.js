const api = require('../../utils/api');

Page({
  data: { items: [], loading: true, error: '' },
  onShow() { this.load(); },
  load() {
    const app = getApp();
    this.setData({ loading: true, error: '' });
    app.ensureLogin()
      .then((token) => api.get('/inventory/items', token))
      .then((data) => this.setData({ items: data.items, loading: false }))
      .catch((err) => this.setData({ error: err.message, loading: false }));
  }
});
