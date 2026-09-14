import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';
import '../widgets/main_tab_scaffold.dart';

enum LogViewState { normal, loading, offline, failure }

class LogScreen extends StatefulWidget {
  const LogScreen({super.key});

  @override
  State<LogScreen> createState() => _LogScreenState();
}

class _LogScreenState extends State<LogScreen> {
  final store = AppStore.instance;
  final _searchController = TextEditingController();
  LogViewState _state = LogViewState.normal;
  Set<ActionSource> _sources = {};

  @override
  void initState() {
    super.initState();
    if (store.isAuthenticated) {
      store.refreshAll();
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<ActivityLogEntry> _filteredLogs() {
    final query = _searchController.text.trim();
    return store.logs.where((entry) {
      final bySource = _sources.isEmpty || _sources.contains(entry.source);
      final itemLabel = kItemLabel[entry.itemKey] ?? '';
      final byQuery = query.isEmpty || itemLabel.contains(query) || (entry.rawText ?? '').contains(query);
      return bySource && byQuery;
    }).toList();
  }

  void _openDetail(ActivityLogEntry entry) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('操作详情', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text('物资：${kItemLabel[entry.itemKey]}'),
              Text('来源：${_sourceLabel(entry.source)}'),
              Text('操作：${entry.operation.name}'),
              Text('变化：${entry.beforeValue.toStringAsFixed(1)} → ${entry.afterValue.toStringAsFixed(1)}'),
              if (entry.rawText != null) Text('原始文本：${entry.rawText}'),
              if (entry.confidence != null) Text('置信度：${entry.confidence!.toStringAsFixed(2)}'),
              Text('时间：${entry.timestamp}'),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        final rows = _filteredLogs();
        return MainTabScaffold(
          currentIndex: 2,
          title: '操作历史',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    children: [
                      TextField(
                        controller: _searchController,
                        decoration: const InputDecoration(
                          prefixIcon: Icon(Icons.search),
                          hintText: '搜索物资 / 原始文本',
                          border: OutlineInputBorder(),
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        children: ActionSource.values.map((source) {
                          return FilterChip(
                            label: Text(_sourceLabel(source)),
                            selected: _sources.contains(source),
                            onSelected: (selected) {
                              setState(() {
                                if (selected) {
                                  _sources.add(source);
                                } else {
                                  _sources.remove(source);
                                }
                              });
                            },
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                ),
              ),
              if (_state == LogViewState.loading) const LinearProgressIndicator(),
              if (_state == LogViewState.offline) const Padding(padding: EdgeInsets.symmetric(vertical: 6), child: Text('当前为离线只读模式')),
              if (_state == LogViewState.failure)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 6),
                  child: Text('日志加载失败', style: TextStyle(color: Color(0xFFC9410A))),
                ),
              if (rows.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('暂无操作记录'),
                  ),
                )
              else
                ...rows.map((entry) {
                  return Card(
                    child: ListTile(
                      title: Text('${kItemLabel[entry.itemKey]} · ${_sourceLabel(entry.source)}'),
                      subtitle: Text('${entry.beforeValue.toStringAsFixed(1)} → ${entry.afterValue.toStringAsFixed(1)}'),
                      trailing: Text('${entry.timestamp.hour.toString().padLeft(2, '0')}:${entry.timestamp.minute.toString().padLeft(2, '0')}'),
                      onTap: () => _openDetail(entry),
                    ),
                  );
                })
            ],
          ),
        );
      },
    );
  }

  String _sourceLabel(ActionSource source) {
    switch (source) {
      case ActionSource.voice:
        return '语音';
      case ActionSource.ocr:
        return 'OCR';
      case ActionSource.manual:
        return '手动';
      case ActionSource.autoDecay:
        return '自动衰减';
      case ActionSource.calibrate:
        return '校准';
    }
  }
}
