import 'package:flutter/material.dart';

enum ItemKey { egg, milk, mantou, rice, pork, veg }

enum InventoryStatus { plenty, warning, critical, empty }

enum Operation { add, set, subtract, clear }

enum ActionSource { voice, ocr, manual, autoDecay, calibrate }

ItemKey itemKeyFromApi(String value) {
  switch (value) {
    case 'EGG':
      return ItemKey.egg;
    case 'MILK':
      return ItemKey.milk;
    case 'MANTOU':
      return ItemKey.mantou;
    case 'RICE':
      return ItemKey.rice;
    case 'PORK':
      return ItemKey.pork;
    case 'VEG':
      return ItemKey.veg;
    default:
      return ItemKey.veg;
  }
}

String itemKeyToApi(ItemKey key) {
  switch (key) {
    case ItemKey.egg:
      return 'EGG';
    case ItemKey.milk:
      return 'MILK';
    case ItemKey.mantou:
      return 'MANTOU';
    case ItemKey.rice:
      return 'RICE';
    case ItemKey.pork:
      return 'PORK';
    case ItemKey.veg:
      return 'VEG';
  }
}

InventoryStatus statusFromApi(String value) {
  switch (value) {
    case 'PLENTY':
      return InventoryStatus.plenty;
    case 'WARNING':
      return InventoryStatus.warning;
    case 'CRITICAL':
      return InventoryStatus.critical;
    case 'EMPTY':
      return InventoryStatus.empty;
    default:
      return InventoryStatus.warning;
  }
}

Operation operationFromApi(String value) {
  switch (value) {
    case 'ADD':
      return Operation.add;
    case 'SET':
      return Operation.set;
    case 'SUBTRACT':
      return Operation.subtract;
    case 'CLEAR':
      return Operation.clear;
    default:
      return Operation.set;
  }
}

String operationToApi(Operation operation) {
  switch (operation) {
    case Operation.add:
      return 'ADD';
    case Operation.set:
      return 'SET';
    case Operation.subtract:
      return 'SUBTRACT';
    case Operation.clear:
      return 'CLEAR';
  }
}

ActionSource actionSourceFromApi(String value) {
  switch (value) {
    case 'VOICE':
      return ActionSource.voice;
    case 'OCR':
      return ActionSource.ocr;
    case 'MANUAL':
      return ActionSource.manual;
    case 'AUTO_DECAY':
      return ActionSource.autoDecay;
    case 'CALIBRATE':
      return ActionSource.calibrate;
    default:
      return ActionSource.manual;
  }
}

String actionSourceToApi(ActionSource source) {
  switch (source) {
    case ActionSource.voice:
      return 'VOICE';
    case ActionSource.ocr:
      return 'OCR';
    case ActionSource.manual:
      return 'MANUAL';
    case ActionSource.autoDecay:
      return 'AUTO_DECAY';
    case ActionSource.calibrate:
      return 'CALIBRATE';
  }
}

class InventoryItem {
  ItemKey itemKey;
  String itemName;
  String unit;
  double currentStock;
  double maxStock;
  double warningThreshold;
  double dailyAvgRate;
  DateTime lastUpdated;
  int serverVersion;

  InventoryItem({
    required this.itemKey,
    required this.itemName,
    required this.unit,
    required this.currentStock,
    required this.maxStock,
    required this.warningThreshold,
    required this.dailyAvgRate,
    required this.lastUpdated,
    required this.serverVersion,
  });

  factory InventoryItem.fromJson(Map<String, dynamic> json) {
    return InventoryItem(
      itemKey: itemKeyFromApi(json['item_key'] as String),
      itemName: (json['item_name'] as String?) ?? kItemLabel[itemKeyFromApi(json['item_key'] as String)] ?? '未知',
      unit: (json['unit'] as String?) ?? '',
      currentStock: (json['current_stock'] as num?)?.toDouble() ?? 0,
      maxStock: (json['max_stock'] as num?)?.toDouble() ?? 0,
      warningThreshold: (json['warning_threshold'] as num?)?.toDouble() ?? 0,
      dailyAvgRate: (json['daily_avg_rate'] as num?)?.toDouble() ?? 0,
      lastUpdated: DateTime.tryParse((json['last_updated'] as String?) ?? '') ?? DateTime.now(),
      serverVersion: (json['server_version'] as num?)?.toInt() ?? 1,
    );
  }

  InventoryStatus get status {
    if (currentStock <= 0) {
      return InventoryStatus.empty;
    }
    if (currentStock <= warningThreshold) {
      return InventoryStatus.critical;
    }
    if (currentStock <= warningThreshold * 2) {
      return InventoryStatus.warning;
    }
    return InventoryStatus.plenty;
  }

  double get ratio {
    if (maxStock <= 0) {
      return 0;
    }
    return (currentStock / maxStock).clamp(0.0, 1.0);
  }
}

class ParsedEntity {
  final ItemKey itemKey;
  final Operation operation;
  final double value;
  final String unit;
  final double normalizedValue;
  final String normalizedUnit;
  final double confidence;
  final String parseSessionId;

  ParsedEntity({
    required this.itemKey,
    required this.operation,
    required this.value,
    required this.unit,
    double? normalizedValue,
    String? normalizedUnit,
    required this.confidence,
    this.parseSessionId = '',
  })  : normalizedValue = normalizedValue ?? value,
        normalizedUnit = normalizedUnit ?? unit;

  factory ParsedEntity.fromJson(Map<String, dynamic> json) {
    return ParsedEntity(
      itemKey: itemKeyFromApi((json['item_key'] as String?) ?? 'VEG'),
      operation: operationFromApi((json['operation'] as String?) ?? 'SET'),
      value: (json['value'] as num?)?.toDouble() ?? 0,
      unit: (json['unit'] as String?) ?? '',
      normalizedValue: (json['normalized_value'] as num?)?.toDouble(),
      normalizedUnit: json['normalized_unit'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      parseSessionId: (json['parse_session_id'] as String?) ?? '',
    );
  }

  ParsedEntity withSessionId(String sessionId) {
    if (parseSessionId.isNotEmpty) {
      return this;
    }
    return ParsedEntity(
      itemKey: itemKey,
      operation: operation,
      value: value,
      unit: unit,
      normalizedValue: normalizedValue,
      normalizedUnit: normalizedUnit,
      confidence: confidence,
      parseSessionId: sessionId,
    );
  }

  Map<String, dynamic> toConfirmJson() {
    return {
      'item_key': itemKeyToApi(itemKey),
      'operation': operationToApi(operation),
      'value': value,
      'unit': unit,
      'normalized_value': normalizedValue,
      'normalized_unit': normalizedUnit,
      'confidence': confidence,
      'parse_session_id': parseSessionId,
    };
  }
}

class VoiceParseResult {
  final String sessionId;
  final List<ParsedEntity> entities;
  final double confidence;

  VoiceParseResult({
    required this.sessionId,
    required this.entities,
    required this.confidence,
  });

  factory VoiceParseResult.fromJson(Map<String, dynamic> json) {
    final rawEntities = (json['entities'] as List<dynamic>? ?? []).whereType<Map<String, dynamic>>().toList();
    return VoiceParseResult(
      sessionId: (json['session_id'] as String?) ?? '',
      entities: rawEntities.map(ParsedEntity.fromJson).toList(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
    );
  }
}

class OcrParseResult {
  final String sessionId;
  final List<ParsedEntity> entities;
  final List<String> unknownItems;

  OcrParseResult({
    required this.sessionId,
    required this.entities,
    required this.unknownItems,
  });

  factory OcrParseResult.fromJson(Map<String, dynamic> json) {
    final rawEntities = (json['entities'] as List<dynamic>? ?? []).whereType<Map<String, dynamic>>().toList();
    return OcrParseResult(
      sessionId: (json['session_id'] as String?) ?? '',
      entities: rawEntities.map(ParsedEntity.fromJson).toList(),
      unknownItems: (json['unknown_items'] as List<dynamic>? ?? []).whereType<String>().toList(),
    );
  }
}

class ActivityLogEntry {
  final String activityId;
  final ItemKey itemKey;
  final ActionSource source;
  final Operation operation;
  final double deltaValue;
  final double beforeValue;
  final double afterValue;
  final DateTime timestamp;
  final String? rawText;
  final double? confidence;

  ActivityLogEntry({
    required this.activityId,
    required this.itemKey,
    required this.source,
    required this.operation,
    required this.deltaValue,
    required this.beforeValue,
    required this.afterValue,
    required this.timestamp,
    this.rawText,
    this.confidence,
  });

  factory ActivityLogEntry.fromJson(Map<String, dynamic> json) {
    return ActivityLogEntry(
      activityId: (json['activity_id'] as String?) ?? 'unknown',
      itemKey: itemKeyFromApi((json['item_key'] as String?) ?? 'VEG'),
      source: actionSourceFromApi((json['action_type'] as String?) ?? 'MANUAL'),
      operation: operationFromApi((json['operation'] as String?) ?? 'SET'),
      deltaValue: (json['delta_value'] as num?)?.toDouble() ?? 0,
      beforeValue: (json['before_value'] as num?)?.toDouble() ?? 0,
      afterValue: (json['after_value'] as num?)?.toDouble() ?? 0,
      timestamp: DateTime.tryParse((json['timestamp'] as String?) ?? '') ?? DateTime.now(),
      rawText: json['raw_text'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
    );
  }
}

class SuggestionItem {
  final ItemKey itemKey;
  final double suggestedQty;
  final String unit;
  final String reason;

  SuggestionItem({
    required this.itemKey,
    required this.suggestedQty,
    required this.unit,
    required this.reason,
  });

  factory SuggestionItem.fromJson(Map<String, dynamic> json) {
    return SuggestionItem(
      itemKey: itemKeyFromApi((json['item_key'] as String?) ?? 'VEG'),
      suggestedQty: (json['suggested_qty'] as num?)?.toDouble() ?? 0,
      unit: (json['unit'] as String?) ?? '',
      reason: (json['reason'] as String?) ?? '',
    );
  }
}

class PurchaseSuggestion {
  final String suggestionId;
  final DateTime generatedAt;
  final String mode;
  final List<SuggestionItem> items;
  final String status;

  PurchaseSuggestion({
    required this.suggestionId,
    required this.generatedAt,
    required this.mode,
    required this.items,
    required this.status,
  });

  factory PurchaseSuggestion.fromJson(Map<String, dynamic> json) {
    final rawItems = (json['items'] as List<dynamic>? ?? []).whereType<Map<String, dynamic>>().toList();
    return PurchaseSuggestion(
      suggestionId: (json['suggestion_id'] as String?) ?? 'unknown',
      generatedAt: DateTime.tryParse((json['generated_at'] as String?) ?? '') ?? DateTime.now(),
      mode: (json['mode'] as String?) ?? 'AUTO',
      items: rawItems.map(SuggestionItem.fromJson).toList(),
      status: (json['status'] as String?) ?? 'PENDING',
    );
  }
}

const Map<ItemKey, String> kItemLabel = {
  ItemKey.egg: '鸡蛋',
  ItemKey.milk: '牛奶',
  ItemKey.mantou: '馒头',
  ItemKey.rice: '大米',
  ItemKey.pork: '猪肉',
  ItemKey.veg: '蔬菜',
};

const Map<ItemKey, IconData> kItemIcon = {
  ItemKey.egg: Icons.egg_alt_outlined,
  ItemKey.milk: Icons.local_drink_outlined,
  ItemKey.mantou: Icons.bakery_dining_outlined,
  ItemKey.rice: Icons.grain_outlined,
  ItemKey.pork: Icons.set_meal_outlined,
  ItemKey.veg: Icons.eco_outlined,
};

Color statusColor(InventoryStatus status) {
  switch (status) {
    case InventoryStatus.plenty:
      return const Color(0xFF2E8B57);
    case InventoryStatus.warning:
      return const Color(0xFFE5BE45);
    case InventoryStatus.critical:
      return const Color(0xFFC9410A);
    case InventoryStatus.empty:
      return const Color(0xFF9A9A9A);
  }
}

enum HouseholdRole { owner, admin, member, viewer }

HouseholdRole householdRoleFromApi(String value) {
  switch (value) {
    case 'OWNER':
      return HouseholdRole.owner;
    case 'ADMIN':
      return HouseholdRole.admin;
    case 'MEMBER':
      return HouseholdRole.member;
    case 'VIEWER':
      return HouseholdRole.viewer;
    default:
      return HouseholdRole.member;
  }
}

String householdRoleToApi(HouseholdRole role) {
  switch (role) {
    case HouseholdRole.owner:
      return 'OWNER';
    case HouseholdRole.admin:
      return 'ADMIN';
    case HouseholdRole.member:
      return 'MEMBER';
    case HouseholdRole.viewer:
      return 'VIEWER';
  }
}

String householdRoleLabel(HouseholdRole role) {
  switch (role) {
    case HouseholdRole.owner:
      return '所有者';
    case HouseholdRole.admin:
      return '管理员';
    case HouseholdRole.member:
      return '成员';
    case HouseholdRole.viewer:
      return '只读';
  }
}

class HouseholdMember {
  final String userId;
  final String phoneMasked;
  final HouseholdRole role;
  final DateTime joinedAt;

  HouseholdMember({
    required this.userId,
    required this.phoneMasked,
    required this.role,
    required this.joinedAt,
  });

  factory HouseholdMember.fromJson(Map<String, dynamic> json) {
    return HouseholdMember(
      userId: (json['user_id'] as String?) ?? '',
      phoneMasked: (json['phone_masked'] as String?) ?? '',
      role: householdRoleFromApi((json['role'] as String?) ?? 'MEMBER'),
      joinedAt: DateTime.tryParse((json['joined_at'] as String?) ?? '') ?? DateTime.now(),
    );
  }
}

class Household {
  final String householdId;
  final String name;
  final String createdBy;
  final List<HouseholdMember> members;
  final DateTime createdAt;

  Household({
    required this.householdId,
    required this.name,
    required this.createdBy,
    required this.members,
    required this.createdAt,
  });

  factory Household.fromJson(Map<String, dynamic> json) {
    final rawMembers = (json['members'] as List<dynamic>? ?? []).whereType<Map<String, dynamic>>().toList();
    return Household(
      householdId: (json['household_id'] as String?) ?? '',
      name: (json['name'] as String?) ?? '',
      createdBy: (json['created_by'] as String?) ?? '',
      members: rawMembers.map(HouseholdMember.fromJson).toList(),
      createdAt: DateTime.tryParse((json['created_at'] as String?) ?? '') ?? DateTime.now(),
    );
  }

  HouseholdMember? findMember(String userId) {
    for (final member in members) {
      if (member.userId == userId) {
        return member;
      }
    }
    return null;
  }
}

class HouseholdInvitation {
  final String invitationId;
  final String householdId;
  final String inviteCode;
  final String status;
  final DateTime expiresAt;
  final DateTime createdAt;

  HouseholdInvitation({
    required this.invitationId,
    required this.householdId,
    required this.inviteCode,
    required this.status,
    required this.expiresAt,
    required this.createdAt,
  });

  factory HouseholdInvitation.fromJson(Map<String, dynamic> json) {
    return HouseholdInvitation(
      invitationId: (json['invitation_id'] as String?) ?? '',
      householdId: (json['household_id'] as String?) ?? '',
      inviteCode: (json['invite_code'] as String?) ?? '',
      status: (json['status'] as String?) ?? 'PENDING',
      expiresAt: DateTime.tryParse((json['expires_at'] as String?) ?? '') ?? DateTime.now(),
      createdAt: DateTime.tryParse((json['created_at'] as String?) ?? '') ?? DateTime.now(),
    );
  }
}

class MonthlyReportEntry {
  final String itemKey;
  final String itemName;
  final String unit;
  final double consumedQty;
  final double wastedQty;
  final double? turnoverDays;

  MonthlyReportEntry({
    required this.itemKey,
    required this.itemName,
    required this.unit,
    required this.consumedQty,
    required this.wastedQty,
    this.turnoverDays,
  });

  factory MonthlyReportEntry.fromJson(Map<String, dynamic> json) {
    return MonthlyReportEntry(
      itemKey: (json['item_key'] as String?) ?? '',
      itemName: (json['item_name'] as String?) ?? '',
      unit: (json['unit'] as String?) ?? '',
      consumedQty: (json['consumed_qty'] as num?)?.toDouble() ?? 0,
      wastedQty: (json['wasted_qty'] as num?)?.toDouble() ?? 0,
      turnoverDays: (json['turnover_days'] as num?)?.toDouble(),
    );
  }
}

class ConsumptionReport {
  final String reportId;
  final String householdId;
  final String month;
  final DateTime generatedAt;
  final double totalConsumedQty;
  final double totalWastedQty;
  final List<MonthlyReportEntry> topConsumed;
  final List<MonthlyReportEntry> wasted;
  final List<MonthlyReportEntry> turnover;
  final List<SuggestionItem> suggestedPurchase;

  ConsumptionReport({
    required this.reportId,
    required this.householdId,
    required this.month,
    required this.generatedAt,
    required this.totalConsumedQty,
    required this.totalWastedQty,
    required this.topConsumed,
    required this.wasted,
    required this.turnover,
    required this.suggestedPurchase,
  });

  factory ConsumptionReport.fromJson(Map<String, dynamic> json) {
    final topConsumed = (json['top_consumed'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(MonthlyReportEntry.fromJson)
        .toList();
    final wasted = (json['wasted'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(MonthlyReportEntry.fromJson)
        .toList();
    final turnover = (json['turnover'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(MonthlyReportEntry.fromJson)
        .toList();
    final suggested = (json['suggested_purchase'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(SuggestionItem.fromJson)
        .toList();
    return ConsumptionReport(
      reportId: (json['report_id'] as String?) ?? '',
      householdId: (json['household_id'] as String?) ?? '',
      month: (json['month'] as String?) ?? '',
      generatedAt: DateTime.tryParse((json['generated_at'] as String?) ?? '') ?? DateTime.now(),
      totalConsumedQty: (json['total_consumed_qty'] as num?)?.toDouble() ?? 0,
      totalWastedQty: (json['total_wasted_qty'] as num?)?.toDouble() ?? 0,
      topConsumed: topConsumed,
      wasted: wasted,
      turnover: turnover,
      suggestedPurchase: suggested,
    );
  }
}
