const api = require('../../utils/api');

Page({
  data: {
    activeTab: 'inventory',
    tabs: [['inventory', '库存'], ['shop', '采购'], ['family', '家庭'], ['reminders', '提醒']],
    items: [], categories: [], meal: '',
    suggestion: null, report: null,
    household: null, inviteCode: '',
    healthReminders: [], billReminders: [],
  },

  onShow() { this.load(); },

  switchTab(e) {
    const k = e.currentTarget.dataset.key;
    this.setData({ activeTab: k });
    this.load();
  },

  load() {
    const map = { inventory: this.loadInventory, shop: this.loadShop, family: this.loadFamily, reminders: this.loadReminders };
    const fn = map[this.data.activeTab];
    if (fn) fn.call(this);
  },

  // ---- 库存 ----
  loadInventory() {
    const app = getApp();
    app.ensureLogin()
      .then((token) => Promise.all([api.get('/inventory/items', token), api.get('/categories', token)]))
      .then(([inv, cats]) => this.setData({ items: inv.items, categories: cats.categories }))
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },
  stockOp(e) {
    const { key, unit, op } = e.currentTarget.dataset;
    const title = op === 'ADD' ? '入库数量（' + unit + '）' : '出库数量（' + unit + '）';
    const app = getApp();
    wx.showModal({
      title, editable: true, placeholderText: '1',
      success: (res) => {
        if (!res.confirm) return;
        const value = parseFloat(res.content) || 1;
        app.ensureLogin()
          .then((token) => api.post('/inventory/operations/batch', { operations: [{ item_key: key, operation: op, value, unit, source: 'MANUAL' }] }, token))
          .then(() => this.loadInventory());
      },
    });
  },
  onCatName(e) { this._catName = e.detail.value; },
  onCatUnit(e) { this._catUnit = e.detail.value; },
  addCategory() {
    const name = (this._catName || '').trim();
    const unit = (this._catUnit || '').trim() || '个';
    if (!name) return wx.showToast({ title: '请输入品类名', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/categories', { name, icon: '📦', unit_type: unit }, token))
      .then(() => { this._catName = ''; this._catUnit = ''; this.loadInventory(); });
  },
  suggestMeal() {
    const app = getApp();
    this.setData({ meal: '生成中…' });
    app.ensureLogin().then((token) => api.post('/meals/suggest', {}, token))
      .then((d) => this.setData({ meal: d.suggestion }))
      .catch((e) => { this.setData({ meal: '' }); wx.showToast({ title: e.message, icon: 'none' }); });
  },

  // ---- 采购 ----
  loadShop() {
    const month = new Date().toISOString().slice(0, 7);
    const app = getApp();
    app.ensureLogin()
      .then((token) => Promise.all([
        api.get('/suggestions/latest', token).catch(() => null),
        api.get('/reports/consumption/monthly?month=' + month, token).catch(() => null),
      ]))
      .then(([sug, rep]) => this.setData({ suggestion: sug ? sug.suggestion : null, report: rep ? rep.report : null }))
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },
  genSuggestion() {
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/suggestions/generate', { mode: 'AUTO' }, token))
      .then(() => this.loadShop());
  },

  // ---- 家庭 ----
  loadFamily() {
    const app = getApp();
    app.ensureLogin()
      .then((token) => api.get('/households/me', token))
      .then((d) => this.setData({ household: d.household }))
      .catch(() => this.setData({ household: null }));
  },
  invite() {
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/households/invitations', { role: 'MEMBER' }, token))
      .then((d) => this.setData({ inviteCode: d.invitation.invite_code }));
  },
  onJoinCode(e) { this._joinCode = e.detail.value; },
  joinFamily() {
    const code = (this._joinCode || '').trim();
    if (!code) return wx.showToast({ title: '请输入邀请码', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/households/join', { invite_code: code }, token))
      .then(() => { this._joinCode = ''; this.loadFamily(); });
  },

  // ---- 提醒 ----
  loadReminders() {
    const app = getApp();
    app.ensureLogin()
      .then((token) => Promise.all([api.get('/health-reminders', token), api.get('/bill-reminders', token)]))
      .then(([h, b]) => this.setData({ healthReminders: h.reminders, billReminders: b.reminders }))
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },
  onHrMember(e) { this._hrMember = e.detail.value; },
  onHrTitle(e) { this._hrTitle = e.detail.value; },
  onHrDays(e) { this._hrDays = e.detail.value; },
  addHealthReminder() {
    const member_name = (this._hrMember || '').trim();
    const title = (this._hrTitle || '').trim();
    const period_days = parseInt(this._hrDays, 10) || 1;
    if (!member_name || !title) return wx.showToast({ title: '请输入成员和事项', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/health-reminders', { member_name, title, period_days }, token))
      .then(() => { this._hrMember = ''; this._hrTitle = ''; this._hrDays = ''; this.loadReminders(); });
  },
  delHealthReminder(e) {
    const id = e.currentTarget.dataset.id;
    const app = getApp();
    app.ensureLogin().then((token) => api.del('/health-reminders/' + id, token)).then(() => this.loadReminders());
  },
  onBrName(e) { this._brName = e.detail.value; },
  onBrAmount(e) { this._brAmount = e.detail.value; },
  onBrMonths(e) { this._brMonths = e.detail.value; },
  addBillReminder() {
    const name = (this._brName || '').trim();
    const amount = parseFloat(this._brAmount) || 0;
    const period_months = parseInt(this._brMonths, 10) || 1;
    if (!name) return wx.showToast({ title: '请输入账单名', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/bill-reminders', { name, amount, period_months }, token))
      .then(() => { this._brName = ''; this._brAmount = ''; this._brMonths = ''; this.loadReminders(); });
  },
  delBillReminder(e) {
    const id = e.currentTarget.dataset.id;
    const app = getApp();
    app.ensureLogin().then((token) => api.del('/bill-reminders/' + id, token)).then(() => this.loadReminders());
  },
});
