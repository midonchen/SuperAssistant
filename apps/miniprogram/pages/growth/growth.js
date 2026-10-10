const api = require('../../utils/api');

const TABS = [['knowledge', '知识'], ['habits', '习惯'], ['finance', '财务'], ['reflect', '自省'], ['interests', '兴趣'], ['skills', '技能']];

Page({
  data: {
    tabs: TABS,
    activeTab: 'knowledge',
    models: [], principles: [],
    habits: [], workouts: [],
    assets: [], total: 0, investments: [],
    journal: [], goals: [],
    interests: [], lifeSkills: [],
  },

  onShow() { this.load(); },

  switchTab(e) {
    this.setData({ activeTab: e.currentTarget.dataset.key });
    this.load();
  },

  load() {
    const app = getApp();
    const t = this.data.activeTab;
    app.ensureLogin().then((token) => {
      if (t === 'knowledge') {
        return Promise.all([api.get('/thinking-models', token), api.get('/value-principles', token)])
          .then(([m, p]) => this.setData({ models: m.entries, principles: p.entries }));
      }
      if (t === 'habits') {
        return Promise.all([api.get('/habits', token), api.get('/workouts', token)])
          .then(([h, w]) => this.setData({ habits: h.habits, workouts: w.workouts }));
      }
      if (t === 'finance') {
        return Promise.all([api.get('/assets', token), api.get('/investments', token)])
          .then(([a, i]) => this.setData({ assets: a.assets, total: a.total, investments: i.investments }));
      }
      if (t === 'reflect') {
        return Promise.all([api.get('/journal', token), api.get('/life-goals', token)])
          .then(([j, g]) => this.setData({ journal: j.entries, goals: g.goals }));
      }
      if (t === 'interests') {
        return api.get('/interests', token).then((d) => this.setData({ interests: d.interests }));
      }
      if (t === 'skills') {
        return api.get('/life-skills', token).then((d) => this.setData({ lifeSkills: d.life_skills }));
      }
    }).catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },

  // 知识
  onTmName(e) { this._tmName = e.detail.value; },
  onTmDesc(e) { this._tmDesc = e.detail.value; },
  addModel() {
    const name = (this._tmName || '').trim();
    const description = (this._tmDesc || '').trim();
    if (!name || !description) return wx.showToast({ title: '请输入名称和说明', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/thinking-models', { name, description }, token))
      .then(() => { this._tmName = ''; this._tmDesc = ''; this.load(); });
  },
  onVpName(e) { this._vpName = e.detail.value; },
  onVpDesc(e) { this._vpDesc = e.detail.value; },
  addPrinciple() {
    const name = (this._vpName || '').trim();
    const description = (this._vpDesc || '').trim();
    if (!name || !description) return wx.showToast({ title: '请输入名称和说明', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/value-principles', { name, description }, token))
      .then(() => { this._vpName = ''; this._vpDesc = ''; this.load(); });
  },

  // 习惯
  onHbName(e) { this._hbName = e.detail.value; },
  addHabit() {
    const name = (this._hbName || '').trim();
    if (!name) return wx.showToast({ title: '请输入习惯名', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/habits', { name }, token))
      .then(() => { this._hbName = ''; this.load(); });
  },
  checkin(e) {
    const id = e.currentTarget.dataset.id;
    const today = new Date().toISOString().slice(0, 10);
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/habits/' + id + '/checkin', { checkin_date: today }, token))
      .then((d) => { wx.showToast({ title: '打卡成功 · 连续 ' + d.streak + ' 天', icon: 'success' }); this.load(); });
  },
  onWkType(e) { this._wkType = e.detail.value; },
  onWkMin(e) { this._wkMin = e.detail.value; },
  addWorkout() {
    const workout_type = this._wkType || 'run';
    const duration_minutes = parseInt(this._wkMin, 10) || 30;
    const workout_date = new Date().toISOString().slice(0, 10);
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/workouts', { workout_type, duration_minutes, workout_date }, token))
      .then(() => { this._wkMin = ''; this.load(); });
  },

  // 财务
  onAsName(e) { this._asName = e.detail.value; },
  onAsAmount(e) { this._asAmount = e.detail.value; },
  addAsset() {
    const name = (this._asName || '').trim();
    const amount = parseFloat(this._asAmount) || 0;
    if (!name || !amount) return wx.showToast({ title: '请输入资产名和金额', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/assets', { name, category: 'cash', amount }, token))
      .then(() => { this._asName = ''; this._asAmount = ''; this.load(); });
  },
  onIvName(e) { this._ivName = e.detail.value; },
  onIvAmount(e) { this._ivAmount = e.detail.value; },
  addInvestment() {
    const name = (this._ivName || '').trim();
    const amount = parseFloat(this._ivAmount) || 0;
    if (!name || !amount) return wx.showToast({ title: '请输入标的和金额', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/investments', { name, amount }, token))
      .then(() => { this._ivName = ''; this._ivAmount = ''; this.load(); });
  },

  // 自省
  onJnContent(e) { this._jnContent = e.detail.value; },
  addJournal() {
    const content = (this._jnContent || '').trim();
    if (!content) return wx.showToast({ title: '请输入感悟内容', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/journal', { content }, token))
      .then(() => { this._jnContent = ''; this.load(); });
  },
  onLgTitle(e) { this._lgTitle = e.detail.value; },
  addGoal() {
    const title = (this._lgTitle || '').trim();
    if (!title) return wx.showToast({ title: '请输入愿景', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/life-goals', { dimension: 'career', title }, token))
      .then(() => { this._lgTitle = ''; this.load(); });
  },

  // 兴趣 + 生活技能
  onInterestName(e) { this._interestName = e.detail.value; },
  addInterest() {
    const name = (this._interestName || '').trim();
    if (!name) return wx.showToast({ title: '请输入兴趣', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/interests', { name }, token))
      .then(() => { this._interestName = ''; this.load(); });
  },
  onSkillName(e) { this._skillName = e.detail.value; },
  onSkillLevel(e) { this._skillLevel = e.detail.value; },
  addLifeSkill() {
    const name = (this._skillName || '').trim();
    if (!name) return wx.showToast({ title: '请输入技能名', icon: 'none' });
    const level = parseInt(this._skillLevel, 10) || 1;
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/life-skills', { name, level }, token))
      .then(() => { this._skillName = ''; this._skillLevel = ''; this.load(); });
  },
});
