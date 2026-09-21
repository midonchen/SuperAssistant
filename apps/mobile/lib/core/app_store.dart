import 'dart:convert';
import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter/material.dart';

import 'api_client.dart';
import 'models.dart';

class AppStore extends ChangeNotifier {
  static const _kAccessTokenKey = 'mobile.auth.access_token';
  static const _kRefreshTokenKey = 'mobile.auth.refresh_token';
  static const _kSessionIdKey = 'mobile.auth.session_id';
  static const _kDeviceIdKey = 'mobile.auth.device_id';
  static const _kUserIdKey = 'mobile.auth.user_id';
  static const _kPendingOfflineOpsKey = 'mobile.sync.pending_offline_ops';

  AppStore._internal() {
    _api.onSessionChanged = _persistSession;
    _api.onSessionCleared = _clearPersistedSession;
    _bootstrap();
  }

  static final AppStore instance = AppStore._internal();

  final ApiClient _api = ApiClient();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final List<InventoryItem> _items = [];
  final List<ActivityLogEntry> _logs = [];
  final List<PurchaseSuggestion> _suggestions = [];
  final List<Map<String, dynamic>> _pendingOfflineOps = [];

  bool _loading = false;
  bool _hydratingSession = false;
  bool _sessionHydrated = false;
  String _lastError = '';
  int _idSeed = 1;
  String _deviceId = 'ios-local-device-001';
  String _currentUserId = '';
  Household? _household;
  ConsumptionReport? _report;

  int shoppingCycle = 7;
  bool notifyEnabled = true;
  String notifyTime = '20:00';

  List<InventoryItem> get items => List.unmodifiable(_items);
  List<ActivityLogEntry> get logs => List.unmodifiable(_logs);
  PurchaseSuggestion? get latestSuggestion => _suggestions.isEmpty ? null : _suggestions.first;

  bool get loading => _loading;
  bool get hydratingSession => _hydratingSession;
  String get lastError => _lastError;
  bool get isAuthenticated => _api.hasToken;
  bool get hasSession => _api.hasToken || _api.hasRefreshToken;
  String get deviceId => _deviceId;
  String get currentUserId => _currentUserId;
  Household? get household => _household;
  ConsumptionReport? get report => _report;
  int get pendingOfflineReplayCount => _pendingOfflineOps.length;

  InventoryItem? findItem(ItemKey key) {
    for (final item in _items) {
      if (item.itemKey == key) {
        return item;
      }
    }
    return null;
  }

  void _setError(String message) {
    _lastError = message;
    notifyListeners();
  }

  Future<bool> _ensureAuthenticated() async {
    if (_api.hasToken) {
      return true;
    }
    try {
      final ok = await _api.ensureAccessToken();
      if (!ok && hasSession) {
        _lastError = '登录已过期，请重新登录';
        notifyListeners();
      }
      return ok;
    } catch (_) {
      if (hasSession) {
        _lastError = '登录已过期，请重新登录';
        notifyListeners();
      }
      return false;
    }
  }

  void _bootstrap({bool clearPersistedReplay = false}) {
    _items
      ..clear()
      ..addAll([
        InventoryItem(
          itemKey: ItemKey.egg,
          itemName: '鸡蛋',
          unit: '个',
          currentStock: 8,
          maxStock: 30,
          warningThreshold: 6,
          dailyAvgRate: 2.1,
          lastUpdated: DateTime.now(),
          serverVersion: 1,
        ),
        InventoryItem(
          itemKey: ItemKey.milk,
          itemName: '牛奶',
          unit: 'L',
          currentStock: 1.8,
          maxStock: 4,
          warningThreshold: 1,
          dailyAvgRate: 0.4,
          lastUpdated: DateTime.now(),
          serverVersion: 1,
        ),
        InventoryItem(
          itemKey: ItemKey.mantou,
          itemName: '馒头',
          unit: '个',
          currentStock: 6,
          maxStock: 20,
          warningThreshold: 4,
          dailyAvgRate: 1.2,
          lastUpdated: DateTime.now(),
          serverVersion: 1,
        ),
        InventoryItem(
          itemKey: ItemKey.rice,
          itemName: '大米',
          unit: 'kg',
          currentStock: 3.2,
          maxStock: 10,
          warningThreshold: 2,
          dailyAvgRate: 0.35,
          lastUpdated: DateTime.now(),
          serverVersion: 1,
        ),
        InventoryItem(
          itemKey: ItemKey.pork,
          itemName: '猪肉',
          unit: 'g',
          currentStock: 420,
          maxStock: 1500,
          warningThreshold: 300,
          dailyAvgRate: 90,
          lastUpdated: DateTime.now(),
          serverVersion: 1,
        ),
        InventoryItem(
          itemKey: ItemKey.veg,
          itemName: '蔬菜',
          unit: '份',
          currentStock: 1,
          maxStock: 7,
          warningThreshold: 2,
          dailyAvgRate: 1,
          lastUpdated: DateTime.now(),
          serverVersion: 1,
        ),
      ]);
    _logs.clear();
    _suggestions.clear();
    _pendingOfflineOps.clear();
    if (clearPersistedReplay) {
      _secureStorage.delete(key: _kPendingOfflineOpsKey);
    }
    generateSuggestion(mode: 'AUTO', silent: true);
  }

  String _nextId() {
    final id = 'id-${_idSeed.toString().padLeft(6, '0')}';
    _idSeed += 1;
    return id;
  }

  Map<String, dynamic> _buildOfflineReplayJob(List<Map<String, dynamic>> operations, {int retryCount = 0}) {
    final firstOp = operations.isNotEmpty ? operations.first : <String, dynamic>{};
    final opId = (firstOp['op_id'] as String?) ?? 'offline-op-${DateTime.now().microsecondsSinceEpoch}';
    return {
      'op_id': opId,
      'created_at': DateTime.now().toUtc().toIso8601String(),
      'endpoint': '/inventory/operations/batch',
      'retry_count': retryCount,
      'payload': {
        'operations': operations.map((row) => Map<String, dynamic>.from(row)).toList(),
      },
    };
  }

  void _queueOfflineReplayJob(Map<String, dynamic> job, {String? message}) {
    final opId = job['op_id'] as String? ?? '';
    final exists = _pendingOfflineOps.any((row) => row['op_id'] == opId);
    if (!exists) {
      _pendingOfflineOps.add(job);
      _persistPendingOfflineReplayQueue();
    }
    if (message != null && message.isNotEmpty) {
      _setError(message);
    } else {
      notifyListeners();
    }
  }

  Future<void> _flushPendingOfflineReplayJobs() async {
    if (_pendingOfflineOps.isEmpty || !_api.hasToken) {
      return;
    }
    final snapshot = _pendingOfflineOps.map((row) => Map<String, dynamic>.from(row)).toList();
    try {
      await _api.enqueueOfflineReplay(snapshot);
      _pendingOfflineOps.clear();
      await _persistPendingOfflineReplayQueue();
      notifyListeners();
    } catch (_) {
      // Keep local pending queue for next retry cycle.
    }
  }

  Future<void> _persistPendingOfflineReplayQueue() async {
    if (_pendingOfflineOps.isEmpty) {
      await _secureStorage.delete(key: _kPendingOfflineOpsKey);
      return;
    }
    await _secureStorage.write(
      key: _kPendingOfflineOpsKey,
      value: jsonEncode(_pendingOfflineOps),
    );
  }

  Future<void> _loadPendingOfflineReplayQueue() async {
    final raw = await _secureStorage.read(key: _kPendingOfflineOpsKey);
    if (raw == null || raw.isEmpty) {
      _pendingOfflineOps.clear();
      return;
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) {
        _pendingOfflineOps.clear();
        await _secureStorage.delete(key: _kPendingOfflineOpsKey);
        return;
      }
      _pendingOfflineOps
        ..clear()
        ..addAll(decoded.whereType<Map>().map((row) => Map<String, dynamic>.from(row)));
    } catch (_) {
      _pendingOfflineOps.clear();
      await _secureStorage.delete(key: _kPendingOfflineOpsKey);
    }
  }

  void _persistSession(LoginSession session) {
    _secureStorage.write(key: _kAccessTokenKey, value: session.accessToken);
    _secureStorage.write(key: _kRefreshTokenKey, value: session.refreshToken);
    _secureStorage.write(key: _kSessionIdKey, value: session.sessionId);
    _secureStorage.write(key: _kDeviceIdKey, value: session.deviceId);
  }

  void _clearPersistedSession() {
    _secureStorage.delete(key: _kAccessTokenKey);
    _secureStorage.delete(key: _kRefreshTokenKey);
    _secureStorage.delete(key: _kSessionIdKey);
    _secureStorage.delete(key: _kDeviceIdKey);
    _secureStorage.delete(key: _kUserIdKey);
  }

  Future<void> initializeSession() async {
    if (_sessionHydrated) {
      return;
    }
    _sessionHydrated = true;
    _hydratingSession = true;
    notifyListeners();

    try {
      await _loadPendingOfflineReplayQueue();
      final accessToken = await _secureStorage.read(key: _kAccessTokenKey) ?? '';
      final refreshToken = await _secureStorage.read(key: _kRefreshTokenKey) ?? '';
      final sessionId = await _secureStorage.read(key: _kSessionIdKey) ?? '';
      _deviceId = await _secureStorage.read(key: _kDeviceIdKey) ?? _deviceId;
      _currentUserId = await _secureStorage.read(key: _kUserIdKey) ?? '';

      if (refreshToken.isNotEmpty || accessToken.isNotEmpty) {
        _api.restoreSession(
          LoginSession(
            accessToken: accessToken,
            refreshToken: refreshToken,
            sessionId: sessionId,
            deviceId: _deviceId,
          ),
        );
        await _api.ensureAccessToken();
        if (_api.hasToken) {
          await refreshAll();
        }
      }
    } catch (e) {
      _setError(e.toString());
    } finally {
      _hydratingSession = false;
      notifyListeners();
    }
  }

  Future<void> sendSmsCode(String phone) async {
    _lastError = '';
    try {
      await _api.sendSmsCode(phone);
    } catch (e) {
      _setError(e.toString());
      rethrow;
    }
  }

  Future<bool> login({required String phone, required String code, required String deviceId}) async {
    _loading = true;
    _lastError = '';
    notifyListeners();
    try {
      _deviceId = deviceId;
      await _api.login(phone, code, deviceId);
      _currentUserId = _api.userId;
      await _secureStorage.write(key: _kUserIdKey, value: _currentUserId);
      await refreshAll();
      return true;
    } catch (e) {
      _setError(e.toString());
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> refreshAll() async {
    final ready = await _ensureAuthenticated();
    if (!ready) {
      return;
    }
    _loading = true;
    _lastError = '';
    notifyListeners();
    try {
      final futures = await Future.wait([
        _api.fetchInventory(),
        _api.fetchLogs(),
        _api.fetchLatestSuggestion(),
      ]);
      final inventory = futures[0] as List<InventoryItem>;
      final logs = futures[1] as PagedLogs;
      final suggestion = futures[2] as PurchaseSuggestion?;

      _items
        ..clear()
        ..addAll(inventory);
      _logs
        ..clear()
        ..addAll(logs.rows);
      _suggestions.clear();
      if (suggestion != null) {
        _suggestions.add(suggestion);
      } else {
        generateSuggestion(mode: 'AUTO', silent: true);
      }
      try {
        _household = await _api.fetchHousehold();
      } catch (_) {
        // best-effort: household fetch failure should not block inventory refresh
      }
      await _flushPendingOfflineReplayJobs();
    } catch (e) {
      _setError(e.toString());
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> _syncBatch(List<Map<String, dynamic>> operations) async {
    final replayJob = _buildOfflineReplayJob(operations);
    final ready = await _ensureAuthenticated();
    if (!ready) {
      _queueOfflineReplayJob(replayJob, message: '当前离线，操作已加入重放队列');
      return;
    }
    try {
      await _api.batchOperations(operations);
      await refreshAll();
    } catch (e) {
      if (e is ApiRequestException && e.code == 'BIZ_409_CONFLICT') {
        _setError('库存版本冲突，已自动刷新');
        await refreshAll();
        return;
      }
      _queueOfflineReplayJob(replayJob, message: '同步失败，操作已加入离线重放队列');
    }
  }

  void applyOperation({
    required ItemKey itemKey,
    required Operation operation,
    required double value,
    required ActionSource source,
    String? rawText,
    double? confidence,
  }) {
    final item = findItem(itemKey);
    if (item == null) {
      return;
    }

    final before = item.currentStock;
    double after = before;
    switch (operation) {
      case Operation.add:
        after = before + value;
        break;
      case Operation.set:
        after = value;
        break;
      case Operation.subtract:
        after = max(0, before - value);
        break;
      case Operation.clear:
        after = 0;
        break;
    }

    item.currentStock = double.parse(after.toStringAsFixed(2));
    item.lastUpdated = DateTime.now();
    item.serverVersion += 1;

    _logs.insert(
      0,
      ActivityLogEntry(
        activityId: _nextId(),
        itemKey: itemKey,
        source: source,
        operation: operation,
        deltaValue: double.parse((after - before).toStringAsFixed(2)),
        beforeValue: before,
        afterValue: after,
        timestamp: DateTime.now(),
        rawText: rawText,
        confidence: confidence,
      ),
    );

    generateSuggestion(mode: 'AUTO', silent: true);
    notifyListeners();

    final op = {
      'item_key': itemKeyToApi(itemKey),
      'operation': operationToApi(operation),
      'value': value,
      'unit': item.unit,
      'source': actionSourceToApi(source),
      'op_id': 'mobile-op-${DateTime.now().microsecondsSinceEpoch}',
      'client_version': item.serverVersion - 1,
    };
    _syncBatch([op]);
  }

  Future<void> generateSuggestionRemote() async {
    final ready = await _ensureAuthenticated();
    if (!ready) {
      generateSuggestion(mode: 'MANUAL');
      return;
    }
    _loading = true;
    notifyListeners();
    try {
      final suggestion = await _api.generateSuggestion();
      if (suggestion != null) {
        _suggestions.insert(0, suggestion);
      }
    } catch (e) {
      _setError(e.toString());
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  PurchaseSuggestion generateSuggestion({String mode = 'MANUAL', bool silent = false}) {
    final suggestionItems = <SuggestionItem>[];
    for (final item in _items) {
      final expected = (item.dailyAvgRate * shoppingCycle);
      final qty = expected - item.currentStock + (expected * 0.2);
      if (qty > 0) {
        suggestionItems.add(
          SuggestionItem(
            itemKey: item.itemKey,
            suggestedQty: double.parse(qty.toStringAsFixed(1)),
            unit: item.unit,
            reason: '预计$shoppingCycle天消耗+20%安全余量',
          ),
        );
      }
    }

    final suggestion = PurchaseSuggestion(
      suggestionId: _nextId(),
      generatedAt: DateTime.now(),
      mode: mode,
      items: suggestionItems,
      status: 'PENDING',
    );
    _suggestions.insert(0, suggestion);
    if (!silent) {
      notifyListeners();
    }
    return suggestion;
  }

  Future<void> updateSettings({
    required int nextCycle,
    required bool nextNotifyEnabled,
    required String nextNotifyTime,
    required Map<ItemKey, double> maxStocks,
  }) async {
    shoppingCycle = nextCycle;
    notifyEnabled = nextNotifyEnabled;
    notifyTime = nextNotifyTime;

    for (final item in _items) {
      final next = maxStocks[item.itemKey];
      if (next != null && next > 0) {
        item.maxStock = next;
      }
    }

    generateSuggestion(mode: 'MANUAL', silent: true);
    notifyListeners();

    if (await _ensureAuthenticated()) {
      try {
        await _api.updatePushPreference(enabled: notifyEnabled, notifyTime: notifyTime);
      } catch (e) {
        _setError(e.toString());
      }
    }
  }

  Future<void> logout() async {
    _loading = true;
    _lastError = '';
    notifyListeners();
    try {
      await _api.logout();
      _bootstrap(clearPersistedReplay: true);
    } catch (e) {
      _setError(e.toString());
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<VoiceParseResult> parseVoice({required String audioUrl, String locale = 'zh-CN'}) async {
    _lastError = '';
    if (!await _ensureAuthenticated()) {
      final sessionId = 'local-v-${DateTime.now().millisecondsSinceEpoch}';
      return VoiceParseResult(
        sessionId: sessionId,
        entities: [
          ParsedEntity(
            itemKey: ItemKey.egg,
            operation: Operation.add,
            value: 10,
            unit: '个',
            confidence: 0.95,
            parseSessionId: sessionId,
          ),
        ],
        confidence: 0.95,
      );
    }
    try {
      return await _api.parseVoice(audioUrl: audioUrl, locale: locale);
    } catch (e) {
      _setError(e.toString());
      rethrow;
    }
  }

  Future<OcrParseResult> parseOcr({required List<String> imageUrls}) async {
    _lastError = '';
    if (!await _ensureAuthenticated()) {
      final sessionId = 'local-o-${DateTime.now().millisecondsSinceEpoch}';
      return OcrParseResult(
        sessionId: sessionId,
        entities: [
          ParsedEntity(
            itemKey: ItemKey.pork,
            operation: Operation.add,
            value: 500,
            unit: 'g',
            confidence: 0.88,
            parseSessionId: sessionId,
          ),
          ParsedEntity(
            itemKey: ItemKey.veg,
            operation: Operation.add,
            value: 2,
            unit: '份',
            confidence: 0.92,
            parseSessionId: sessionId,
          ),
        ],
        unknownItems: const ['酸奶'],
      );
    }
    try {
      return await _api.parseOcr(imageUrls: imageUrls);
    } catch (e) {
      _setError(e.toString());
      rethrow;
    }
  }

  Future<void> confirmParsedEntities({
    required String sessionId,
    required List<ParsedEntity> entities,
    required ActionSource source,
    String? rawText,
  }) async {
    if (entities.isEmpty) {
      return;
    }

    final payload = entities.map((entity) => entity.withSessionId(sessionId)).toList();
    if (!await _ensureAuthenticated()) {
      for (final entity in payload) {
        applyOperation(
          itemKey: entity.itemKey,
          operation: entity.operation,
          value: entity.normalizedValue,
          source: source,
          rawText: rawText,
          confidence: entity.confidence,
        );
      }
      return;
    }

    _lastError = '';
    _loading = true;
    notifyListeners();
    try {
      await _api.confirmParse(sessionId: sessionId, entities: payload);
      await refreshAll();
    } catch (e) {
      _setError(e.toString());
      rethrow;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> refreshHousehold() async {
    if (!await _ensureAuthenticated()) {
      return;
    }
    try {
      _household = await _api.fetchHousehold();
      notifyListeners();
    } catch (e) {
      _setError(e.toString());
    }
  }

  Future<bool> createHousehold(String name) async {
    if (!await _ensureAuthenticated()) {
      return false;
    }
    try {
      _household = await _api.createHousehold(name);
      await refreshAll();
      return true;
    } catch (e) {
      _setError(e.toString());
      return false;
    }
  }

  Future<String?> createInvitation({String role = 'MEMBER'}) async {
    if (!await _ensureAuthenticated()) {
      return null;
    }
    try {
      final invitation = await _api.createInvitation(role: role);
      return invitation.inviteCode;
    } catch (e) {
      _setError(e.toString());
      return null;
    }
  }

  Future<bool> joinHousehold(String inviteCode) async {
    if (!await _ensureAuthenticated()) {
      return false;
    }
    try {
      _household = await _api.joinHousehold(inviteCode);
      await refreshAll();
      return true;
    } catch (e) {
      _setError(e.toString());
      return false;
    }
  }

  Future<ConsumptionReport?> fetchMonthlyReport({String? month}) async {
    if (!await _ensureAuthenticated()) {
      return null;
    }
    _lastError = '';
    _loading = true;
    notifyListeners();
    try {
      _report = await _api.fetchMonthlyReport(month: month);
      return _report;
    } catch (e) {
      _setError(e.toString());
      return null;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}
