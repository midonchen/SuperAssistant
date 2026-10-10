const api = require('../../utils/api');

Page({
  data: { reflections: [], skills: [], learning: [], ideas: [] },

  onShow() { this.load(); },

  load() {
    const app = getApp();
    app.ensureLogin()
      .then((token) => Promise.all([
        api.get('/work-reflections', token),
        api.get('/skills', token),
        api.get('/learning-items', token),
        api.get('/startup-ideas', token),
      ]))
      .then(([r, s, l, i]) => {
        this.setData({ reflections: r.reflections, skills: s.skills, learning: l.items, ideas: i.ideas });
      })
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },

  onReflTitle(e) { this._reflTitle = e.detail.value; },
  onReflContent(e) { this._reflContent = e.detail.value; },
  addReflection() {
    const title = (this._reflTitle || '').trim();
    const content = (this._reflContent || '').trim();
    if (!content) return wx.showToast({ title: '请输入心得内容', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/work-reflections', { title: title || null, content }, token))
      .then(() => { this._reflTitle = ''; this._reflContent = ''; this.load(); });
  },

  onSkillName(e) { this._skillName = e.detail.value; },
  onSkillLevel(e) { this._skillLevel = e.detail.value; },
  addSkill() {
    const name = (this._skillName || '').trim();
    if (!name) return wx.showToast({ title: '请输入技能名', icon: 'none' });
    const level = parseInt(this._skillLevel, 10) || 1;
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/skills', { name, level }, token))
      .then(() => { this._skillName = ''; this._skillLevel = ''; this.load(); });
  },

  onLearnTitle(e) { this._learnTitle = e.detail.value; },
  addLearning() {
    const title = (this._learnTitle || '').trim();
    if (!title) return wx.showToast({ title: '请输入学习内容', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/learning-items', { title, item_type: 'course' }, token))
      .then(() => { this._learnTitle = ''; this.load(); });
  },

  onIdeaTitle(e) { this._ideaTitle = e.detail.value; },
  onIdeaDesc(e) { this._ideaDesc = e.detail.value; },
  addIdea() {
    const title = (this._ideaTitle || '').trim();
    const description = (this._ideaDesc || '').trim();
    if (!title) return wx.showToast({ title: '请输入想法标题', icon: 'none' });
    const app = getApp();
    app.ensureLogin().then((token) => api.post('/startup-ideas', { title, description: description || null }, token))
      .then(() => { this._ideaTitle = ''; this._ideaDesc = ''; this.load(); });
  },
});
