# 微信小程序迁移规划（WeChat Mini Program）

## 背景与决策

产品定位调整：将超级管家以**微信小程序**方式呈现（原 HTML 移动端作为临时演示保留，D8 已确认）。
- AppID：`wxf99e99ee5bc9eaf1`
- AppSecret：仅存服务器 `.env`（0600），绝不进代码/仓库/日志（与 DeepSeek key 同级保密）。

## 认证差异（核心）

| 维度 | HTML 移动端 | 微信小程序 |
|------|------------|-----------|
| 身份 | 手机号 + 短信验证码 | `openid`（`wx.login()` 的 code → 后端 `jscode2session`） |
| 登录接口 | `POST /auth/sms/login` | `POST /auth/wechat/login`（code → openid → find-or-create user → issue token） |
| 用户主键 | `phone`（unique，非空） | 仍用 `phone` 列，微信用户生成合成手机号 + `openid`（unique，可空） |

微信用户首次登录：`bootstrap_wechat_user(openid)` 创建用户（`phone` = `9`+md5(openid)[:16] 合成、`phone_masked` = "微信用户"、`openid` = openid）+ 默认家庭 + 默认库存/分类，后续 `is_new_user=False`。

## 关键约束

1. **HTTPS 要求**：生产环境 `wx.request` 强制 HTTPS + 已备案/配置的「request 合法域名」。当前 staging 是明文 HTTP（`http://agint.sonmuu.com:8000`），**开发/演示阶段**在微信开发者工具勾选「不校验合法域名、TLS 版本及 HTTPS 证书」即可直连；**上线前必须**改为 HTTPS 并在小程序后台配置 request 域名。
2. **tabBar 图标**：小程序 tabBar 需要 `iconPath`/`selectedIconPath` PNG（81×81，≤40KB），五个方向各一对。
3. **AppSecret 机密**：`code2session` 在服务端完成，客户端只传 code，不接触 secret。
4. **本地/测试模式**：`WECHAT_MOCK=1`（或无 AppID/Secret）时 `exchange_code` 返回 `mock-`+sha256(code)[:40] 确定性 openid，使 demo 脚本/测试无需真机即可跑通闭环。

## 里程碑

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| W1 | 后端微信登录（openid 列 + `code2session` 服务 + `/auth/wechat/login` + 测试） | ✅ part 85 |
| W2 | 小程序骨架（project.config.json / app.json tabBar 五方向 / app.js 登录 / utils/api.js / 首页 + 占位页） | ✅ part 86 |
| W3 | 生活方向（库存/采购/家庭/提醒）迁入小程序页面 | 待做 |
| W4 | 工作/关系/职业/成长 迁入小程序页面 | 待做 |
| W5 | 微信手机号绑定（`getPhoneNumber`，需企业认证）+ HTTPS 域名 + 提审发布 | 待做 |

## 部署与验证

- 小程序源码为纯客户端工程（`apps/miniprogram/`），无需部署到 ECS；后端 API 照常部署。
- 真机/开发者工具验证登录：`wx.login()` 拿 code → 后端换 openid → 返回 access_token → 存 storage → 后续 `wx.request` 带 `Authorization: Bearer <token>` + `X-Request-Id`/`Idempotency-Key`/`X-App-Version`。
