import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';
import '../routes/app_routes.dart';
import '../widgets/main_tab_scaffold.dart';

enum HomeViewState { normal, loading, error, offline }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final store = AppStore.instance;
  HomeViewState _state = HomeViewState.normal;

  @override
  void initState() {
    super.initState();
    if (store.isAuthenticated) {
      store.refreshAll();
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        return MainTabScaffold(
          currentIndex: 0,
          title: 'Home',
          actions: [
            IconButton(
              onPressed: store.loading ? null : () => store.refreshAll(),
              icon: store.loading ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.refresh),
            )
          ],
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('你好，今天是库存检查日', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              _stateSwitcher(),
              const SizedBox(height: 12),
              if (_state == HomeViewState.error) _errorBanner(),
              if (store.lastError.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(store.lastError, style: const TextStyle(color: Color(0xFFC9410A))),
                ),
              _briefingCard(),
              const SizedBox(height: 12),
              _inventoryGrid(),
              const SizedBox(height: 16),
              _actionDock(),
            ],
          ),
        );
      },
    );
  }

  Widget _stateSwitcher() {
    return Wrap(
      spacing: 8,
      children: HomeViewState.values.map((state) {
        final selected = _state == state;
        return ChoiceChip(
          label: Text(_label(state)),
          selected: selected,
          onSelected: (_) => setState(() => _state = state),
        );
      }).toList(),
    );
  }

  String _label(HomeViewState state) {
    switch (state) {
      case HomeViewState.normal:
        return '默认';
      case HomeViewState.loading:
        return '加载';
      case HomeViewState.error:
        return '失败';
      case HomeViewState.offline:
        return '离线';
    }
  }

  Widget _errorBanner() {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: Theme.of(context).colorScheme.errorContainer, borderRadius: BorderRadius.circular(10)),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFC9410A)),
          const SizedBox(width: 8),
          const Expanded(child: Text('网络异常，请稍后重试')),
          TextButton(onPressed: () => setState(() => _state = HomeViewState.normal), child: const Text('重试')),
        ],
      ),
    );
  }

  Widget _briefingCard() {
    final suggestion = store.latestSuggestion;
    final warnCount = store.items.where((item) => item.status != InventoryStatus.plenty).length;
    final pendingReplay = store.pendingOfflineReplayCount;

    if (_state == HomeViewState.loading) {
      return _skeleton(height: 120);
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('AI 简报', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('当前有 $warnCount 项库存需要关注'),
            const SizedBox(height: 4),
            Text('最新建议：${suggestion?.items.length ?? 0} 项待采购，建议在 ${store.notifyTime} 前补货'),
            if (pendingReplay > 0) ...[
              const SizedBox(height: 4),
              Text('离线重放队列：$pendingReplay 条待同步', style: const TextStyle(color: Color(0xFFC9410A))),
            ],
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: () => Navigator.pushReplacementNamed(context, AppRoutes.list),
              child: const Text('查看采购清单'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _inventoryGrid() {
    if (_state == HomeViewState.loading) {
      return Column(
        children: List.generate(2, (_) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _skeleton(height: 120),
        )),
      );
    }

    final items = store.items;
    return GridView.builder(
      itemCount: items.length,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 1.25,
      ),
      itemBuilder: (context, index) {
        final item = items[index];
        return InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => Navigator.pushNamed(context, AppRoutes.itemDetail, arguments: {'itemKey': item.itemKey}),
          onLongPress: () => Navigator.pushNamed(
            context,
            AppRoutes.voice,
            arguments: {'itemKey': item.itemKey, 'mode': 'calibrate'},
          ),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(kItemIcon[item.itemKey], color: statusColor(item.status)),
                  const SizedBox(height: 6),
                  Text(item.itemName, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('${item.currentStock.toStringAsFixed(1)} ${item.unit}'),
                  const Spacer(),
                  LinearProgressIndicator(value: item.ratio, color: statusColor(item.status), backgroundColor: Theme.of(context).colorScheme.onSurface.withOpacity(0.12)),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _actionDock() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _dockButton(Icons.mic_none_rounded, '语音', () => Navigator.pushNamed(context, AppRoutes.voice)),
            _dockButton(Icons.document_scanner_outlined, '拍票', () => Navigator.pushNamed(context, AppRoutes.ocr)),
            _dockButton(Icons.edit_outlined, '手动', () => Navigator.pushNamed(context, AppRoutes.manualFill, arguments: {'unknownItems': <String>[] })),
          ],
        ),
      ),
    );
  }

  Widget _dockButton(IconData icon, String label, VoidCallback onTap) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Column(
          children: [
            Icon(icon),
            const SizedBox(height: 4),
            Text(label),
          ],
        ),
      ),
    );
  }

  Widget _skeleton({required double height}) {
    return Container(
      height: height,
      width: double.infinity,
      decoration: BoxDecoration(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.12), borderRadius: BorderRadius.circular(16)),
    );
  }
}
