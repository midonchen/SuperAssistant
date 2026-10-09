const api = require('./utils/api');

App({
  globalData: { token: '', profile: null, loginPromise: null },

  onLaunch() {
    const token = wx.getStorageSync('sa_token');
    if (token) {
      this.globalData.token = token;
      this.globalData.profile = wx.getStorageSync('sa_profile') || null;
    }
  },

  ensureLogin() {
    if (this.globalData.token) return Promise.resolve(this.globalData.token);
    if (this.globalData.loginPromise) return this.globalData.loginPromise;
    this.globalData.loginPromise = new Promise((resolve, reject) => {
      wx.login({
        success: (res) => {
          if (!res.code) {
            this.globalData.loginPromise = null;
            return reject(new Error('wx.login 未返回 code'));
          }
          api.post('/auth/wechat/login', { code: res.code, device_id: 'wx-mp' })
            .then((data) => {
              this.globalData.token = data.access_token;
              this.globalData.profile = data.user_profile;
              wx.setStorageSync('sa_token', data.access_token);
              wx.setStorageSync('sa_profile', data.user_profile);
              resolve(data.access_token);
            })
            .catch((err) => { this.globalData.loginPromise = null; reject(err); });
        },
        fail: (err) => { this.globalData.loginPromise = null; reject(err); }
      });
    });
    return this.globalData.loginPromise;
  }
});
