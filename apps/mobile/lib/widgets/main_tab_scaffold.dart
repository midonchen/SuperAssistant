import 'package:flutter/material.dart';

import '../routes/app_routes.dart';

class MainTabScaffold extends StatelessWidget {
  final int currentIndex;
  final String title;
  final Widget child;
  final List<Widget>? actions;

  const MainTabScaffold({
    super.key,
    required this.currentIndex,
    required this.title,
    required this.child,
    this.actions,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: actions,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: child,
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) => _switchTab(context, index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.shopping_basket_outlined), label: 'List'),
          NavigationDestination(icon: Icon(Icons.timeline_outlined), label: 'Log'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
        ],
      ),
    );
  }

  void _switchTab(BuildContext context, int index) {
    final routes = [AppRoutes.home, AppRoutes.list, AppRoutes.log, AppRoutes.settings];
    final target = routes[index];
    if (index == currentIndex) {
      return;
    }
    Navigator.pushReplacementNamed(context, target);
  }
}
