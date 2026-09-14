import 'package:flutter/material.dart';

class AppShell extends StatelessWidget {
  final String title;
  final Widget child;

  const AppShell({super.key, required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: child,
      ),
    );
  }
}
