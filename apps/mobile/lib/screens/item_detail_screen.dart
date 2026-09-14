import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';

class ItemDetailScreen extends StatelessWidget {
  const ItemDetailScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
    final itemKey = args?['itemKey'] as ItemKey?;
    final store = AppStore.instance;
    final item = itemKey == null ? null : store.findItem(itemKey);

    if (item == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('物资详情')),
        body: const Center(child: Text('未找到物资')),
      );
    }

    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        return Scaffold(
          appBar: AppBar(title: Text(item.itemName)),
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('当前库存 ${item.currentStock.toStringAsFixed(1)} ${item.unit}', style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 8),
                          LinearProgressIndicator(value: item.ratio),
                          const SizedBox(height: 8),
                          Text('满载量 ${item.maxStock.toStringAsFixed(1)} ${item.unit} · 预警阈值 ${item.warningThreshold.toStringAsFixed(1)}'),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ElevatedButton(
                        onPressed: () {
                          store.applyOperation(
                            itemKey: item.itemKey,
                            operation: Operation.add,
                            value: 1,
                            source: ActionSource.manual,
                          );
                        },
                        child: const Text('+1'),
                      ),
                      ElevatedButton(
                        onPressed: () {
                          store.applyOperation(
                            itemKey: item.itemKey,
                            operation: Operation.subtract,
                            value: 1,
                            source: ActionSource.manual,
                          );
                        },
                        child: const Text('-1'),
                      ),
                      OutlinedButton(
                        onPressed: () {
                          Navigator.pop(context);
                        },
                        child: const Text('返回'),
                      ),
                    ],
                  )
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
