const api = require('../../utils/api');

Page({
  data: { contacts: [], stale: [] },

  onShow() { this.load(); },

  load() {
    const app = getApp();
    app.ensureLogin().then((token) => api.get('/contacts', token))
      .then((d) => this.setData({ contacts: d.contacts }))
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },

  onName(e) { this._name = e.detail.value; },
  onRel(e) { this._rel = e.detail.value; },
  onBirthday(e) { this._birthday = e.detail.value; },
  addContact() {
    const name = (this._name || '').trim();
    const relationship = (this._rel || '').trim();
    const birthday = (this._birthday || '').trim();
    if (!name) return wx.showToast({ title: '请输入姓名', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/contacts', { name, relationship: relationship || null, birthday: birthday || null }, token))
      .then(() => { this._name = ''; this._rel = ''; this._birthday = ''; this.load(); });
  },
  delContact(e) {
    const id = e.currentTarget.dataset.id;
    const app = getApp();
    app.ensureLogin().then((token) => api.del('/contacts/' + id, token)).then(() => this.load());
  },
  recordInteraction(e) {
    const { id, name } = e.currentTarget.dataset;
    const app = getApp();
    wx.showModal({
      title: '与「' + name + '」互动', editable: true, placeholderText: '渠道（微信/电话/见面）',
      success: (res) => {
        if (!res.confirm) return;
        const channel = res.content || '微信';
        app.ensureLogin().then((token) => api.post('/contacts/' + id + '/interactions', { channel, note: null }, token))
          .then(() => wx.showToast({ title: '已记录互动', icon: 'success' }));
      },
    });
  },
  suggestGift(e) {
    const id = e.currentTarget.dataset.id;
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/contacts/' + id + '/gifts', {}, token))
      .then((d) => wx.showModal({ title: '礼物建议', content: d.suggestion.content, showCancel: false }));
  },
  loadStale() {
    const app = getApp();
    app.ensureLogin().then((token) => api.get('/contacts/stale?days=30', token))
      .then((d) => this.setData({ stale: d.contacts }))
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },
});
