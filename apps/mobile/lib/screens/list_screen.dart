import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';
import '../routes/app_routes.dart';
import '../widgets/main_tab_scaffold.dart';

enum ListViewState { normal, generating, failure, offline }

class ListScreen extends StatefulWidget {
  const ListScreen({super.key});

  @override
  State<ListScreen> createState() => _ListScreenState();
}

class _ListScreenState extends State<ListScreen> {
  final store = AppStore.instance;
  ListViewState _state = ListViewState.normal;
  Set<InventoryStatus> _statusFilter = {};

  @override
  void initState() {
    super.initState();
    if (store.isAuthenticated) {
      store.refreshAll();
    }
  }

  Future<void> _generate() async {
    setState(() => _state = ListViewState.generating);
    await store.generateSuggestionRemote();
    if (!mounted) {
      return;
    }
    setState(() => _state = ListViewState.normal);
  }

  Future<void> _openFilterSheet() async {
    final result = await showModalBottomSheet<Set<InventoryStatus>>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        final local = Set<InventoryStatus>.from(_statusFilter);
        return StatefulBuilder(
          builder: (context, setLocalState) {
            return Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('筛选状态', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    children: InventoryStatus.values.map((status) {
                      return FilterChip(
                        label: Text(_statusLabel(status)),
                        selected: local.contains(status),
                        onSelected: (selected) {
                          setLocalState(() {
                            if (selected) {
                              local.add(status);
                            } else {
                              local.remove(status);
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      TextButton(onPressed: () => Navigator.pop(context, <InventoryStatus>{}), child: const Text('清空')),
                      const Spacer(),
                      ElevatedButton(onPressed: () => Navigator.pop(context, local), child: const Text('应用')),
                    ],
                  )
                ],
              ),
            );
          },
        );
      },
    );

    if (result != null) {
      setState(() => _statusFilter = result);
    }
  }

  List<SuggestionItem> _visibleItems() {
    final suggestion = store.latestSuggestion;
    if (suggestion == null) {
      return [];
    }

    if (_statusFilter.isEmpty) {
      return suggestion.items;
    }

    return suggestion.items.where((item) {
      final inventory = store.findItem(item.itemKey);
      if (inventory == null) {
        return false;
      }
      return _statusFilter.contains(inventory.status);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        final suggestion = store.latestSuggestion;
        final items = _visibleItems();
        return MainTabScaffold(
          currentIndex: 1,
          title: '采购清单',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('建议摘要', style: TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 6),
                      Text(suggestion == null ? '暂无建议' : '生成时间：${suggestion.generatedAt}'),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          ElevatedButton(onPressed: _state == ListViewState.generating ? null : _generate, child: Text(_state == ListViewState.generating ? '生成中...' : '生成建议')),
                          const SizedBox(width: 8),
                          OutlinedButton(onPressed: _openFilterSheet, child: const Text('筛选')),
                          const SizedBox(width: 8),
                          OutlinedButton(onPressed: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已触发导出（占位）'))), child: const Text('导出')),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              if (_state == ListViewState.failure)
                const Padding(
                  padding: EdgeInsets.only(bottom: 12),
                  child: Text('加载失败，请重试', style: TextStyle(color: Color(0xFFC9410A))),
                ),
              if (_state == ListViewState.offline)
                const Padding(
                  padding: EdgeInsets.only(bottom: 12),
                  child: Text('当前展示离线缓存数据'),
                ),
              if (items.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('暂无条目，请生成采购建议'),
                  ),
                )
              else
                ...items.map((item) {
                  return Card(
                    child: ListTile(
                      leading: Icon(kItemIcon[item.itemKey]),
                      title: Text('${kItemLabel[item.itemKey]} · ${item.suggestedQty.toStringAsFixed(1)} ${item.unit}'),
                      subtitle: Text(item.reason),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => Navigator.pushNamed(context, AppRoutes.itemDetail, arguments: {'itemKey': item.itemKey}),
                    ),
                  );
                })
            ],
          ),
        );
      },
    );
  }

  String _statusLabel(InventoryStatus status) {
    switch (status) {
      case InventoryStatus.plenty:
        return '充足';
      case InventoryStatus.warning:
        return '预警';
      case InventoryStatus.critical:
        return '紧缺';
      case InventoryStatus.empty:
        return '告罄';
    }
  }
}
