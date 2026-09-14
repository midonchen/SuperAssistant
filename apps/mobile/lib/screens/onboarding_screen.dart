import 'package:flutter/material.dart';

import '../routes/app_routes.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _pageController = PageController();
  int _step = 0;

  static const _steps = [
    ('欢迎使用', '帮你自动管理家里物资，减少断货与浪费'),
    ('初始库存', '录入鸡蛋、牛奶、蔬菜等初始库存，后续自动衰减'),
    ('消耗习惯', '设置每周大致消耗量，采购建议更准确'),
  ];

  void _finish() {
    Navigator.pushReplacementNamed(context, AppRoutes.home);
  }

  Future<void> _skip() async {
    final shouldSkip = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('确认跳过？'),
        content: const Text('跳过后会使用默认值，可在设置页调整。'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('取消')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('确认跳过')),
        ],
      ),
    );
    if ((shouldSkip ?? false) && mounted) {
      _finish();
    }
  }

  void _next() {
    if (_step == _steps.length - 1) {
      _finish();
      return;
    }
    final next = _step + 1;
    _pageController.animateToPage(next, duration: const Duration(milliseconds: 220), curve: Curves.easeOut);
    setState(() => _step = next);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Onboarding')),
      body: SafeArea(
        child: Column(
          children: [
            LinearProgressIndicator(value: (_step + 1) / _steps.length),
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _steps.length,
                itemBuilder: (context, index) {
                  final step = _steps[index];
                  return Padding(
                    padding: const EdgeInsets.all(20),
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('步骤 ${index + 1}', style: Theme.of(context).textTheme.labelLarge),
                            const SizedBox(height: 12),
                            Text(step.$1, style: Theme.of(context).textTheme.headlineSmall),
                            const SizedBox(height: 12),
                            Text(step.$2, style: Theme.of(context).textTheme.bodyLarge),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  OutlinedButton(onPressed: _skip, child: const Text('跳过')),
                  const Spacer(),
                  ElevatedButton(onPressed: _next, child: Text(_step == _steps.length - 1 ? '完成' : '下一步')),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
