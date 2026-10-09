const BASE = 'http://agint.sonmuu.com:8000/api/v1';

function request(path, { method = 'GET', data, token } = {}) {
  return new Promise((resolve, reject) => {
    const header = {
      'Content-Type': 'application/json',
      'X-Request-Id': 'wx-mp',
      'X-App-Version': '1.1.0',
      'X-Platform': 'weixin-mp'
    };
    if (token) header['Authorization'] = 'Bearer ' + token;
    if (method !== 'GET') {
      header['Idempotency-Key'] = 'wx-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
    }
    wx.request({
      url: BASE + path,
      method,
      header,
      data,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data.data);
        } else {
          const body = res.data || {};
          reject(new Error(body.message || body.code || ('HTTP ' + res.statusCode)));
        }
      },
      fail(err) {
        reject(new Error(err.errMsg || 'network error'));
      }
    });
  });
}

module.exports = {
  BASE,
  get(path, token) { return request(path, { method: 'GET', token }); },
  post(path, data, token) { return request(path, { method: 'POST', data, token }); },
  del(path, token) { return request(path, { method: 'DELETE', token }); }
};
