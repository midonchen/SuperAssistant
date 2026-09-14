import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';

class ManualFillScreen extends StatefulWidget {
  const ManualFillScreen({super.key});

  @override
  State<ManualFillScreen> createState() => _ManualFillScreenState();
}

class _ManualFillScreenState extends State<ManualFillScreen> {
  final store = AppStore.instance;
  final Map<String, TextEditingController> _controllers = {};

  @override
  void dispose() {
    for (final ctrl in _controllers.values) {
      ctrl.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
    final unknownItems = (args?['unknownItems'] as List?)?.whereType<String>().toList() ?? <String>[];
    if (unknownItems.isEmpty) {
      unknownItems.add('未命名条目');
    }

    for (final item in unknownItems) {
      _controllers.putIfAbsent(item, () => TextEditingController());
    }

    return Scaffold(
      appBar: AppBar(title: const Text('手动补全')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text('请为未识别项补充数量，默认映射到蔬菜类。'),
            const SizedBox(height: 12),
            ...unknownItems.map((item) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(
                  controller: _controllers[item],
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(
                    labelText: '$item 数量（份）',
                    border: const OutlineInputBorder(),
                  ),
                ),
              );
            }),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: () {
                for (final item in unknownItems) {
                  final value = double.tryParse(_controllers[item]!.text.trim());
                  if (value == null || value <= 0) {
                    continue;
                  }
                  store.applyOperation(
                    itemKey: ItemKey.veg,
                    operation: Operation.add,
                    value: value,
                    source: ActionSource.manual,
                    rawText: 'manual_fill:$item',
                  );
                }
                Navigator.pop(context);
              },
              child: const Text('提交并返回'),
            ),
          ],
        ),
      ),
    );
  }
}
