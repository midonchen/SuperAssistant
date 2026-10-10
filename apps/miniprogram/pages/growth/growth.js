const api = require('../../utils/api');

Page({
  data: { interests: [], lifeSkills: [] },

  onShow() { this.load(); },

  load() {
    const app = getApp();
    app.ensureLogin()
      .then((token) => Promise.all([
        api.get('/interests', token),
        api.get('/life-skills', token),
      ]))
      .then(([i, s]) => {
        this.setData({ interests: i.interests, lifeSkills: s.life_skills });
      })
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },

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
