import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class LoginSession {
  final String accessToken;
  final String refreshToken;
  final String sessionId;
  final String deviceId;

  LoginSession({
    required this.accessToken,
    required this.refreshToken,
    required this.sessionId,
    required this.deviceId,
  });
}

class PagedLogs {
  final List<ActivityLogEntry> rows;
  final int total;

  PagedLogs({required this.rows, required this.total});
}

class ApiRequestException implements Exception {
  final int statusCode;
  final String code;
  final String message;
  final bool retriable;
  final Map<String, dynamic>? details;

  ApiRequestException({
    required this.statusCode,
    required this.code,
    required this.message,
    this.retriable = false,
    this.details,
  });

  @override
  String toString() {
    return '$code: $message';
  }
}

class ApiClient {
  ApiClient({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000/api/v1');

  final http.Client _client;
  final String _baseUrl;
  String _accessToken = '';
  String _refreshToken = '';
  String _sessionId = '';
  String _deviceId = 'ios-local-device-001';
  Future<bool>? _refreshInFlight;
  void Function(LoginSession session)? onSessionChanged;
  void Function()? onSessionCleared;

  bool get hasToken => _accessToken.isNotEmpty;
  bool get hasRefreshToken => _refreshToken.isNotEmpty;
  String get accessToken => _accessToken;
  String get refreshToken => _refreshToken;
  String get sessionId => _sessionId;
  String get deviceId => _deviceId;

  void restoreSession(LoginSession session) {
    _accessToken = session.accessToken;
    _refreshToken = session.refreshToken;
    _sessionId = session.sessionId;
    _deviceId = session.deviceId;
  }

  void clearSession() {
    _accessToken = '';
    _refreshToken = '';
    _sessionId = '';
    onSessionCleared?.call();
  }

  void _applySession({
    required String accessToken,
    required String refreshToken,
    required String sessionId,
    required String deviceId,
    bool notify = true,
  }) {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
    _sessionId = sessionId;
    _deviceId = deviceId;
    if (notify) {
      onSessionChanged?.call(
        LoginSession(
          accessToken: _accessToken,
          refreshToken: _refreshToken,
          sessionId: _sessionId,
          deviceId: _deviceId,
        ),
      );
    }
  }

  Map<String, String> _headers({required bool write, bool auth = false}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'X-Request-Id': 'mobile-${DateTime.now().microsecondsSinceEpoch}',
      'X-App-Version': '1.1.0',
      'X-Platform': 'ios',
    };
    if (write) {
      headers['Idempotency-Key'] = 'op-${DateTime.now().microsecondsSinceEpoch}';
    }
    if (auth && _accessToken.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_accessToken';
    }
    return headers;
  }

  Future<http.Response> _send(
    String method,
    Uri uri, {
    required Map<String, String> headers,
    Map<String, dynamic>? body,
  }) async {
    if (method == 'GET') {
      return _client.get(uri, headers: headers);
    }
    if (method == 'POST') {
      return _client.post(uri, headers: headers, body: jsonEncode(body ?? <String, dynamic>{}));
    }
    if (method == 'PUT') {
      return _client.put(uri, headers: headers, body: jsonEncode(body ?? <String, dynamic>{}));
    }
    throw Exception('unsupported method: $method');
  }

  Map<String, dynamic> _decodePayload(http.Response response) {
    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      throw ApiRequestException(
        statusCode: response.statusCode,
        code: 'SYS_500_INVALID_RESPONSE',
        message: 'invalid response payload',
        retriable: true,
      );
    }
  }

  Future<bool> _refreshAccessToken() async {
    if (_refreshToken.isEmpty) {
      return false;
    }
    if (_refreshInFlight != null) {
      return _refreshInFlight!;
    }

    final future = () async {
      try {
        final uri = Uri.parse('$_baseUrl/auth/token/refresh');
        final headers = _headers(write: true, auth: false);
        final response = await _send(
          'POST',
          uri,
          headers: headers,
          body: {
            'refresh_token': _refreshToken,
            'device_id': _deviceId,
          },
        );

        final payload = _decodePayload(response);
        if (response.statusCode >= 200 && response.statusCode < 300) {
          final data = (payload['data'] as Map<String, dynamic>? ?? <String, dynamic>{});
          final sessionId = (data['session_id'] as String?) ?? _sessionId;
          final accessToken = (data['access_token'] as String?) ?? '';
          final refreshToken = (data['refresh_token'] as String?) ?? '';
          if (accessToken.isEmpty || refreshToken.isEmpty) {
            return false;
          }
          _applySession(
            accessToken: accessToken,
            refreshToken: refreshToken,
            sessionId: sessionId,
            deviceId: _deviceId,
          );
          return true;
        }

        final code = (payload['code'] as String?) ?? 'UNKNOWN';
        if (response.statusCode == 401 && code == 'AUTH_401_TOKEN_EXPIRED') {
          clearSession();
        }
        return false;
      } catch (_) {
        return false;
      }
    }();

    _refreshInFlight = future;
    try {
      return await future;
    } finally {
      _refreshInFlight = null;
    }
  }

  Future<bool> ensureAccessToken() async {
    if (_accessToken.isNotEmpty) {
      return true;
    }
    return _refreshAccessToken();
  }

  Future<Map<String, dynamic>> _request(
    String path, {
    required String method,
    bool write = false,
    bool auth = false,
    Map<String, dynamic>? body,
    bool allowRefreshRetry = true,
  }) async {
    final uri = Uri.parse('$_baseUrl$path');
    final headers = _headers(write: write, auth: auth);

    final response = await _send(method, uri, headers: headers, body: body);
    final payload = _decodePayload(response);

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return (payload['data'] as Map<String, dynamic>? ?? <String, dynamic>{});
    }

    final code = (payload['code'] as String?) ?? 'UNKNOWN';
    final message = (payload['message'] as String?) ?? 'request failed';

    final shouldRefresh = auth && allowRefreshRetry && response.statusCode == 401 && code == 'AUTH_401_TOKEN_EXPIRED';
    if (shouldRefresh && await _refreshAccessToken()) {
      return _request(
        path,
        method: method,
        write: write,
        auth: auth,
        body: body,
        allowRefreshRetry: false,
      );
    }

    throw ApiRequestException(
      statusCode: response.statusCode,
      code: code,
      message: message,
      retriable: (payload['retriable'] as bool?) ?? false,
      details: payload['details'] is Map<String, dynamic> ? payload['details'] as Map<String, dynamic> : null,
    );
  }

  Future<void> sendSmsCode(String phone) async {
    await _request(
      '/auth/sms/send',
      method: 'POST',
      write: true,
      body: {
        'phone': phone,
        'purpose': 'LOGIN',
      },
    );
  }

  Future<LoginSession> login(String phone, String code, String deviceId) async {
    final data = await _request(
      '/auth/sms/login',
      method: 'POST',
      write: true,
      body: {
        'phone': phone,
        'code': code,
        'device_id': deviceId,
      },
    );
    final accessToken = (data['access_token'] as String?) ?? '';
    final refreshToken = (data['refresh_token'] as String?) ?? '';
    final sessionId = (data['session_id'] as String?) ?? '';
    _applySession(
      accessToken: accessToken,
      refreshToken: refreshToken,
      sessionId: sessionId,
      deviceId: deviceId,
    );
    return LoginSession(
      accessToken: accessToken,
      refreshToken: refreshToken,
      sessionId: sessionId,
      deviceId: deviceId,
    );
  }

  Future<void> logout() async {
    final sid = _sessionId;
    try {
      if (sid.isNotEmpty) {
        await _request(
          '/auth/logout',
          method: 'POST',
          auth: true,
          write: true,
          body: {'session_id': sid},
          allowRefreshRetry: false,
        );
      }
    } finally {
      clearSession();
    }
  }

  Future<List<InventoryItem>> fetchInventory() async {
    final data = await _request('/inventory/items', method: 'GET', auth: true);
    final items = (data['items'] as List<dynamic>? ?? []).whereType<Map<String, dynamic>>().toList();
    return items.map(InventoryItem.fromJson).toList();
  }

  Future<PagedLogs> fetchLogs({int page = 1, int pageSize = 30}) async {
    final data = await _request('/inventory/logs?page=$page&page_size=$pageSize', method: 'GET', auth: true);
    final list = (data['list'] as List<dynamic>? ?? []).whereType<Map<String, dynamic>>().toList();
    return PagedLogs(
      rows: list.map(ActivityLogEntry.fromJson).toList(),
      total: (data['total'] as num?)?.toInt() ?? list.length,
    );
  }

  Future<PurchaseSuggestion?> fetchLatestSuggestion() async {
    final data = await _request('/suggestions/latest', method: 'GET', auth: true);
    final suggestion = data['suggestion'];
    if (suggestion is Map<String, dynamic>) {
      return PurchaseSuggestion.fromJson(suggestion);
    }
    return null;
  }

  Future<PurchaseSuggestion?> generateSuggestion() async {
    await _request(
      '/suggestions/generate',
      method: 'POST',
      auth: true,
      write: true,
      body: {'mode': 'MANUAL'},
    );
    return fetchLatestSuggestion();
  }

  Future<void> batchOperations(List<Map<String, dynamic>> operations) async {
    await _request(
      '/inventory/operations/batch',
      method: 'POST',
      auth: true,
      write: true,
      body: {'operations': operations},
    );
  }

  Future<void> enqueueOfflineReplay(List<Map<String, dynamic>> offlineOps) async {
    await _request(
      '/inventory/offline/replay',
      method: 'POST',
      auth: true,
      write: true,
      body: {'offline_ops': offlineOps},
    );
  }

  Future<void> updatePushPreference({required bool enabled, required String notifyTime}) async {
    await _request(
      '/push/preference',
      method: 'PUT',
      auth: true,
      write: true,
      body: {
        'enabled': enabled,
        'notify_time': notifyTime,
      },
    );
  }

  Future<VoiceParseResult> parseVoice({required String audioUrl, required String locale}) async {
    final data = await _request(
      '/ai/voice/parse',
      method: 'POST',
      auth: true,
      write: true,
      body: {
        'audio_url': audioUrl,
        'locale': locale,
      },
    );
    return VoiceParseResult.fromJson(data);
  }

  Future<OcrParseResult> parseOcr({required List<String> imageUrls}) async {
    final data = await _request(
      '/ai/ocr/parse',
      method: 'POST',
      auth: true,
      write: true,
      body: {'image_urls': imageUrls},
    );
    return OcrParseResult.fromJson(data);
  }

  Future<void> confirmParse({required String sessionId, required List<ParsedEntity> entities}) async {
    await _request(
      '/ai/parse/confirm',
      method: 'POST',
      auth: true,
      write: true,
      body: {
        'session_id': sessionId,
        'entities': entities.map((entity) => entity.toConfirmJson()).toList(),
      },
    );
  }
}
