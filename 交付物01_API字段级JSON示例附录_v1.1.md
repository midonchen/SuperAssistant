# SuperAssistant · 交付物 01
## API 字段级 JSON 示例附录 v1.1

> 适用文档：`SuperAssistant_PRD_v1.1.md` 第 11 章  
> 基础路径：`/api/v1`  
> 协议：HTTPS + TLS 1.3

---

## 1. 全局请求与响应约定

### 1.1 请求头（必填）

| Header | 示例 | 说明 |
|---|---|---|
| Authorization | `Bearer <access_token>` | 除登录相关接口外必填 |
| X-Request-Id | `f2c94b45-5cd1-4ec4-9f8e-2b33b0a90839` | 请求链路追踪 |
| X-App-Version | `1.1.0` | 客户端版本 |
| X-Platform | `ios` | `ios/android/web-admin` |
| Idempotency-Key | `op-20260331-0001` | 写接口必填，避免重复提交 |

### 1.2 成功响应模板

```json
{
  "code": "OK",
  "message": "success",
  "request_id": "f2c94b45-5cd1-4ec4-9f8e-2b33b0a90839",
  "timestamp": "2026-03-31T12:00:00Z",
  "data": {}
}
```

### 1.3 失败响应模板

```json
{
  "code": "VAL_400_INVALID_PARAM",
  "message": "invalid phone format",
  "request_id": "f2c94b45-5cd1-4ec4-9f8e-2b33b0a90839",
  "timestamp": "2026-03-31T12:00:00Z",
  "details": {
    "field": "phone"
  },
  "retriable": false
}
```

---

## 2. 核心对象定义（Schema）

### 2.1 `UserProfile`

```json
{
  "user_id": "0dd2e7c5-f0aa-4f2d-9478-d2f475abdf98",
  "phone_masked": "138****8888",
  "timezone": "Asia/Shanghai",
  "shopping_day": 6,
  "shopping_cycle": 7,
  "onboarded": true
}
```

### 2.2 `InventoryItem`

```json
{
  "item_key": "EGG",
  "item_name": "鸡蛋",
  "unit": "个",
  "current_stock": 12.0,
  "max_stock": 30.0,
  "warning_threshold": 6.0,
  "status": "WARNING",
  "daily_avg_rate": 2.1,
  "last_calibrated": "2026-03-29T14:02:00Z",
  "last_updated": "2026-03-31T00:05:00Z"
}
```

### 2.3 `ActivityLog`

```json
{
  "activity_id": "4e48b863-f764-4700-b870-587bcf847f79",
  "item_key": "MILK",
  "action_type": "VOICE",
  "operation": "SET",
  "delta_value": 1.5,
  "before_value": 2.0,
  "after_value": 1.5,
  "raw_text": "牛奶还有一升半",
  "confidence": 0.96,
  "timestamp": "2026-03-31T10:20:30Z"
}
```

### 2.4 `ParsedEntity`

```json
{
  "item_key": "PORK",
  "operation": "ADD",
  "value": 1.0,
  "unit": "斤",
  "normalized_value": 500.0,
  "normalized_unit": "g",
  "confidence": 0.89
}
```

### 2.5 `PurchaseSuggestion`

```json
{
  "suggestion_id": "d3493635-4072-4be9-a3ee-d6a76965cba6",
  "generated_at": "2026-03-31T12:30:00Z",
  "mode": "AUTO",
  "items": [
    {
      "item_key": "EGG",
      "suggested_qty": 20,
      "unit": "个",
      "reason": "预计7天消耗+20%安全余量"
    }
  ],
  "status": "PENDING"
}
```

---

## 3. 认证接口示例

## 3.1 发送验证码
`POST /auth/sms/send`

Request:
```json
{
  "phone": "13800138000",
  "purpose": "LOGIN"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "82a7e36f-afb8-4f44-b964-2bff6ed02f2f",
  "timestamp": "2026-03-31T12:00:00Z",
  "data": {
    "expire_in": 300,
    "retry_after": 60
  }
}
```

Error:
```json
{
  "code": "AUTH_429_SMS_RATE_LIMIT",
  "message": "send too frequently",
  "request_id": "82a7e36f-afb8-4f44-b964-2bff6ed02f2f",
  "timestamp": "2026-03-31T12:00:00Z",
  "details": {
    "retry_after": 48
  },
  "retriable": true
}
```

## 3.2 验证码登录
`POST /auth/sms/login`

Request:
```json
{
  "phone": "13800138000",
  "code": "263981",
  "device_id": "ios-9F31A86B-7CA4-4A31-8E33-EA8E6B9FA101"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "2df698f2-a98f-490f-b4d3-f35f6e6759ae",
  "timestamp": "2026-03-31T12:02:00Z",
  "data": {
    "access_token": "<jwt_access_token>",
    "refresh_token": "<refresh_token>",
    "expires_in": 7200,
    "user_profile": {
      "user_id": "0dd2e7c5-f0aa-4f2d-9478-d2f475abdf98",
      "phone_masked": "138****8888",
      "timezone": "Asia/Shanghai",
      "shopping_day": 6,
      "shopping_cycle": 7,
      "onboarded": true
    }
  }
}
```

## 3.3 刷新 Token
`POST /auth/token/refresh`

Request:
```json
{
  "refresh_token": "<refresh_token>",
  "device_id": "ios-9F31A86B-7CA4-4A31-8E33-EA8E6B9FA101"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "435b4fce-bb76-4342-8f93-80ca2a92781a",
  "timestamp": "2026-03-31T12:40:00Z",
  "data": {
    "access_token": "<new_jwt_access_token>",
    "refresh_token": "<new_refresh_token>",
    "expires_in": 7200
  }
}
```

## 3.4 登出
`POST /auth/logout`

Request:
```json
{
  "session_id": "f49f1ec3-e855-4d0c-adf6-2bde43dc128f"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "8fe5d2f2-c5af-42d0-9789-25f6ddf2731c",
  "timestamp": "2026-03-31T12:45:00Z",
  "data": {
    "success": true
  }
}
```

## 3.5 账号注销
`DELETE /auth/account`

Request:
```json
{
  "verify_code": "992761",
  "reason": "不再使用"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "5362c651-6261-4f8f-ba56-b812f8f98033",
  "timestamp": "2026-03-31T12:50:00Z",
  "data": {
    "cool_down_end_at": "2026-04-07T12:50:00Z"
  }
}
```

---

## 4. 库存与日志接口示例

## 4.1 获取库存列表
`GET /inventory/items?status=WARNING`

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "654e91f9-d4d4-4868-95d3-c1679ca9ccf8",
  "timestamp": "2026-03-31T13:00:00Z",
  "data": {
    "items": [
      {
        "item_key": "EGG",
        "item_name": "鸡蛋",
        "unit": "个",
        "current_stock": 5.0,
        "max_stock": 30.0,
        "warning_threshold": 6.0,
        "status": "CRITICAL",
        "daily_avg_rate": 2.1,
        "last_calibrated": "2026-03-29T14:02:00Z",
        "last_updated": "2026-03-31T00:05:00Z"
      }
    ]
  }
}
```

## 4.2 批量库存操作
`POST /inventory/operations/batch`

Request:
```json
{
  "operations": [
    {
      "item_key": "EGG",
      "operation": "ADD",
      "value": 10,
      "unit": "个",
      "source": "VOICE"
    },
    {
      "item_key": "MILK",
      "operation": "SET",
      "value": 2,
      "unit": "L",
      "source": "VOICE"
    }
  ]
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "45f81b57-c85f-4d2e-9520-d0fbf969befe",
  "timestamp": "2026-03-31T13:02:00Z",
  "data": {
    "updated_items": [
      {
        "item_key": "EGG",
        "current_stock": 18.0,
        "status": "WARNING"
      },
      {
        "item_key": "MILK",
        "current_stock": 2.0,
        "status": "PLENTY"
      }
    ],
    "activity_ids": [
      "97ec9130-6b89-48da-a2de-b0d84086f76f",
      "d6b117c0-f6b6-4d54-a247-ea94d26a180a"
    ]
  }
}
```

## 4.3 获取操作日志
`GET /inventory/logs?page=1&page_size=20&item_key=EGG`

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "8bc20f6c-f660-4306-8778-620f04ff07f1",
  "timestamp": "2026-03-31T13:05:00Z",
  "data": {
    "list": [
      {
        "activity_id": "4e48b863-f764-4700-b870-587bcf847f79",
        "item_key": "EGG",
        "action_type": "AUTO_DECAY",
        "operation": "SUBTRACT",
        "delta_value": -2.1,
        "before_value": 20.0,
        "after_value": 17.9,
        "timestamp": "2026-03-31T00:05:00Z"
      }
    ],
    "total": 124,
    "page": 1,
    "page_size": 20
  }
}
```

## 4.4 手动校准
`POST /inventory/items/{item_key}/calibrate`

Request:
```json
{
  "value": 3.0,
  "unit": "个"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "95ca82f8-a4f4-4b44-ae2a-7497f41dfde7",
  "timestamp": "2026-03-31T13:08:00Z",
  "data": {
    "item": {
      "item_key": "EGG",
      "current_stock": 3.0,
      "status": "CRITICAL",
      "last_calibrated": "2026-03-31T13:08:00Z"
    }
  }
}
```

---

## 5. AI 解析接口示例

## 5.1 语音解析
`POST /ai/voice/parse`

Request:
```json
{
  "audio_url": "https://cdn.example.com/audio/20260331_130900.m4a",
  "locale": "zh-CN"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "6dd60be0-a6f3-4530-8f5b-42c1a57f68a1",
  "timestamp": "2026-03-31T13:09:02Z",
  "data": {
    "session_id": "parse-v-20260331-001",
    "entities": [
      {
        "item_key": "EGG",
        "operation": "ADD",
        "value": 30,
        "unit": "个",
        "normalized_value": 30,
        "normalized_unit": "个",
        "confidence": 0.97
      },
      {
        "item_key": "MILK",
        "operation": "SET",
        "value": 1.5,
        "unit": "L",
        "normalized_value": 1.5,
        "normalized_unit": "L",
        "confidence": 0.95
      }
    ],
    "confidence": 0.96
  }
}
```

## 5.2 OCR 解析
`POST /ai/ocr/parse`

Request:
```json
{
  "image_urls": [
    "https://cdn.example.com/ocr/r1.jpg",
    "https://cdn.example.com/ocr/r2.jpg"
  ]
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "844d472b-b0cf-4a86-b53f-10635f56659d",
  "timestamp": "2026-03-31T13:11:30Z",
  "data": {
    "session_id": "parse-o-20260331-004",
    "entities": [
      {
        "item_key": "PORK",
        "operation": "ADD",
        "value": 1,
        "unit": "斤",
        "normalized_value": 500,
        "normalized_unit": "g",
        "confidence": 0.88
      }
    ],
    "unknown_items": [
      "酸奶"
    ]
  }
}
```

## 5.3 解析确认入库
`POST /ai/parse/confirm`

Request:
```json
{
  "session_id": "parse-v-20260331-001",
  "entities": [
    {
      "item_key": "EGG",
      "operation": "ADD",
      "normalized_value": 30,
      "normalized_unit": "个"
    }
  ]
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "ce2d534f-f7a3-42f6-a5f8-0f3cf2dfaf85",
  "timestamp": "2026-03-31T13:12:10Z",
  "data": {
    "inventory_snapshot": {
      "updated_count": 1,
      "items": [
        {
          "item_key": "EGG",
          "current_stock": 33.0,
          "status": "PLENTY"
        }
      ]
    }
  }
}
```

---

## 6. 采购建议与推送接口示例

## 6.1 生成采购建议
`POST /suggestions/generate`

Request:
```json
{
  "mode": "MANUAL"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "3f96212a-ff0c-4035-8cd1-7179bd496a46",
  "timestamp": "2026-03-31T13:15:00Z",
  "data": {
    "suggestion_id": "d3493635-4072-4be9-a3ee-d6a76965cba6",
    "items": [
      {
        "item_key": "EGG",
        "suggested_qty": 20,
        "unit": "个",
        "reason": "预计7天消耗+20%安全余量"
      }
    ]
  }
}
```

## 6.2 获取最新建议
`GET /suggestions/latest`

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "1f40f92a-b96e-47fb-b93b-fd35389f0f8a",
  "timestamp": "2026-03-31T13:16:00Z",
  "data": {
    "suggestion": {
      "suggestion_id": "d3493635-4072-4be9-a3ee-d6a76965cba6",
      "generated_at": "2026-03-31T13:15:00Z",
      "status": "PENDING",
      "items": [
        {
          "item_key": "EGG",
          "suggested_qty": 20,
          "unit": "个",
          "reason": "预计7天消耗+20%安全余量"
        }
      ]
    }
  }
}
```

## 6.3 注册推送设备
`POST /push/device/register`

Request:
```json
{
  "platform": "ios",
  "device_token": "fcm_apns_device_token"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "9f9e2b31-8ab8-4d3b-9f7c-42e17df76f70",
  "timestamp": "2026-03-31T13:18:00Z",
  "data": {
    "registered": true
  }
}
```

## 6.4 更新推送偏好
`PUT /push/preference`

Request:
```json
{
  "enabled": true,
  "notify_time": "20:00"
}
```

Success:
```json
{
  "code": "OK",
  "message": "success",
  "request_id": "9ae4dd5c-c67f-4f69-848a-228574f39ca4",
  "timestamp": "2026-03-31T13:18:30Z",
  "data": {
    "preference": {
      "enabled": true,
      "notify_time": "20:00",
      "timezone": "Asia/Shanghai"
    }
  }
}
```

---

## 7. 离线队列与冲突返回示例

### 7.1 本地离线操作结构（客户端本地）

```json
{
  "op_id": "offline-op-0001",
  "created_at": "2026-03-31T13:20:00Z",
  "endpoint": "/inventory/operations/batch",
  "payload": {
    "operations": [
      {
        "item_key": "MILK",
        "operation": "SET",
        "value": 1.0,
        "unit": "L",
        "source": "MANUAL"
      }
    ]
  },
  "retry_count": 0
}
```

### 7.2 冲突返回示例

```json
{
  "code": "BIZ_409_CONFLICT",
  "message": "inventory version conflict",
  "request_id": "d5ea75fd-7f9b-4579-bf25-c20f4cb6a603",
  "timestamp": "2026-03-31T13:22:00Z",
  "details": {
    "item_key": "MILK",
    "server_version": 18,
    "client_version": 16
  },
  "retriable": true
}
```

---

## 8. 错误码补充字典（建议）

| 错误码 | HTTP | 场景 |
|---|---:|---|
| AUTH_429_SMS_RATE_LIMIT | 429 | 验证码发送过于频繁 |
| AUTH_401_CODE_INVALID | 401 | 验证码错误 |
| AUTH_409_SESSION_REVOKED | 409 | 设备被踢下线 |
| VAL_400_INVALID_PARAM | 400 | 参数格式不合法 |
| BIZ_404_ITEM_NOT_FOUND | 404 | 物资不存在 |
| BIZ_409_CONFLICT | 409 | 库存版本冲突 |
| AI_429_RATE_LIMIT | 429 | AI 服务限流 |
| AI_504_TIMEOUT | 504 | AI 解析超时 |
| SYS_500_INTERNAL | 500 | 服务内部异常 |
| SYS_503_DEPENDENCY_DOWN | 503 | 第三方依赖不可用 |

---

## 9. 版本与废弃响应头示例

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-API-Revision: 1.3
Deprecated: true
Sunset: Thu, 30 Jul 2026 00:00:00 GMT
Link: </api/v2/inventory/items>; rel="successor-version"
```

---

*状态：可用于联调；后续如新增接口，请在本附录补齐字段表与示例 JSON。*
