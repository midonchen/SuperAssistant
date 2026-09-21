import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';

class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key});

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  final store = AppStore.instance;
  String _month = '';

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    final prev = now.month == 1 ? DateTime(now.year - 1, 12) : DateTime(now.year, now.month - 1);
    _month = _monthOf(prev);
    _load();
  }

  String _monthOf(DateTime dt) => '${dt.year.toString().padLeft(4, '0')}-${dt.month.toString().padLeft(2, '0')}';

  String _shiftMonth(String month, int delta) {
    final parts = month.split('-');
    final year = int.parse(parts[0]);
    final m = int.parse(parts[1]);
    final total = year * 12 + (m - 1) + delta;
    final newYear = total ~/ 12;
    final newMonth = total % 12 + 1;
    return '${newYear.toString().padLeft(4, '0')}-${newMonth.toString().padLeft(2, '0')}';
  }

  Future<void> _load() async {
    await store.fetchMonthlyReport(month: _month);
  }

  void _changeMonth(int delta) {
    setState(() => _month = _shiftMonth(_month, delta));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        final report = store.report;
        return Scaffold(
          appBar: AppBar(title: const Text('月度消费报告')),
          body: SafeArea(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(onPressed: () => _changeMonth(-1), icon: const Icon(Icons.chevron_left)),
                    Text(_month, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
                    IconButton(onPressed: () => _changeMonth(1), icon: const Icon(Icons.chevron_right)),
                  ],
                ),
                if (store.loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
                if (!store.loading && report == null) ...[
                  const SizedBox(height: 24),
                  const Center(child: Text('暂无报告')),
                ],
                if (!store.loading && report != null) ...[
                  Row(
                    children: [
                      Expanded(child: _SummaryCard(title: '月度消耗', value: report.totalConsumedQty.toStringAsFixed(1))),
                      const SizedBox(width: 12),
                      Expanded(child: _SummaryCard(title: '预估浪费', value: report.totalWastedQty.toStringAsFixed(1))),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _Section(
                    title: '消耗 Top 10',
                    children: report.topConsumed.isEmpty
                        ? const [Padding(padding: EdgeInsets.all(16), child: Text('本月无消耗记录'))]
                        : report.topConsumed
                            .map((e) => ListTile(
                                  dense: true,
                                  leading: const Icon(Icons.trending_down),
                                  title: Text(e.itemName),
                                  subtitle: Text('消耗 ${e.consumedQty.toStringAsFixed(1)} ${e.unit}'),
                                ))
                            .toList(),
                  ),
                  const SizedBox(height: 12),
                  _Section(
                    title: '周转天数（当前库存可支撑）',
                    children: report.turnover.isEmpty
                        ? const [Padding(padding: EdgeInsets.all(16), child: Text('暂无周转数据'))]
                        : report.turnover
                            .map((e) => ListTile(
                                  dense: true,
                                  leading: const Icon(Icons.timer_outlined),
                                  title: Text(e.itemName),
                                  trailing: Text(e.turnoverDays == null ? '-' : '${e.turnoverDays!.toStringAsFixed(1)} 天'),
                                ))
                            .toList(),
                  ),
                  const SizedBox(height: 12),
                  _Section(
                    title: '浪费明细',
                    children: report.wasted.isEmpty
                        ? const [Padding(padding: EdgeInsets.all(16), child: Text('本月无浪费'))]
                        : report.wasted
                            .map((e) => ListTile(
                                  dense: true,
                                  leading: const Icon(Icons.delete_outline),
                                  title: Text(e.itemName),
                                  subtitle: Text('浪费 ${e.wastedQty.toStringAsFixed(1)} ${e.unit}'),
                                ))
                            .toList(),
                  ),
                  const SizedBox(height: 12),
                  _Section(
                    title: '建议采购清单',
                    children: report.suggestedPurchase.isEmpty
                        ? const [Padding(padding: EdgeInsets.all(16), child: Text('暂无采购建议'))]
                        : report.suggestedPurchase
                            .map((e) => ListTile(
                                  dense: true,
                                  leading: const Icon(Icons.shopping_cart_outlined),
                                  title: Text(kItemLabel[e.itemKey] ?? '未知'),
                                  subtitle: Text(e.reason),
                                  trailing: Text('${e.suggestedQty.toStringAsFixed(1)} ${e.unit}'),
                                ))
                            .toList(),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String title;
  final String value;
  const _SummaryCard({required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(color: Colors.grey, fontSize: 13)),
            const SizedBox(height: 4),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 20)),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _Section({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        Card(child: Column(children: children)),
      ],
    );
  }
}
