import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';
import '../routes/app_routes.dart';
import '../widgets/main_tab_scaffold.dart';

enum SaveState { idle, saving, success, failure }

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final store = AppStore.instance;
  final _cycleController = TextEditingController();
  final _notifyController = TextEditingController();
  final Map<ItemKey, TextEditingController> _maxControllers = {};

  bool _notifyEnabled = true;
  SaveState _saveState = SaveState.idle;

  @override
  void initState() {
    super.initState();
    _cycleController.text = store.shoppingCycle.toString();
    _notifyController.text = store.notifyTime;
    _notifyEnabled = store.notifyEnabled;
    for (final item in store.items) {
      _maxControllers[item.itemKey] = TextEditingController(text: item.maxStock.toStringAsFixed(1));
    }
  }

  @override
  void dispose() {
    _cycleController.dispose();
    _notifyController.dispose();
    for (final ctrl in _maxControllers.values) {
      ctrl.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final cycle = int.tryParse(_cycleController.text.trim());
    if (cycle == null || cycle <= 0) {
      setState(() => _saveState = SaveState.failure);
      return;
    }
    setState(() => _saveState = SaveState.saving);

    final maxStocks = <ItemKey, double>{};
    for (final entry in _maxControllers.entries) {
      final value = double.tryParse(entry.value.text.trim());
      if (value != null && value > 0) {
        maxStocks[entry.key] = value;
      }
    }

    await store.updateSettings(
      nextCycle: cycle,
      nextNotifyEnabled: _notifyEnabled,
      nextNotifyTime: _notifyController.text.trim().isEmpty ? '20:00' : _notifyController.text.trim(),
      maxStocks: maxStocks,
    );

    if (!mounted) {
      return;
    }

    setState(() => _saveState = SaveState.success);
  }

  Future<void> _logout() async {
    await store.logout();
    if (!mounted) {
      return;
    }
    Navigator.pushNamedAndRemoveUntil(context, AppRoutes.auth, (route) => false);
  }

  @override
  Widget build(BuildContext context) {
    return MainTabScaffold(
      currentIndex: 3,
      title: '设置',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('采购周期与通知', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _cycleController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: '采购周期（天）', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    value: _notifyEnabled,
                    onChanged: (next) => setState(() => _notifyEnabled = next),
                    title: const Text('开启推送提醒'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _notifyController,
                    keyboardType: TextInputType.datetime,
                    decoration: const InputDecoration(labelText: '提醒时间（HH:mm）', border: OutlineInputBorder()),
                  ),
                ],
              ),
            ),
          ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('满载量设置', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  ...store.items.map((item) {
                    final ctrl = _maxControllers[item.itemKey]!;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: TextField(
                        controller: ctrl,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: InputDecoration(
                          labelText: '${item.itemName} 满载量（${item.unit}）',
                          border: const OutlineInputBorder(),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
          if (_saveState == SaveState.success)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: Text('保存成功', style: TextStyle(color: Color(0xFF2E8B57))),
            ),
          if (_saveState == SaveState.failure)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: Text('保存失败，请检查输入', style: TextStyle(color: Color(0xFFC9410A))),
            ),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _saveState == SaveState.saving ? null : _save,
              child: Text(_saveState == SaveState.saving ? '保存中...' : '保存设置'),
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: store.loading ? null : _logout,
              child: const Text('退出登录'),
            ),
          ),
        ],
      ),
    );
  }
}
