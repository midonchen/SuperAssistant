import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../routes/app_routes.dart';

class AuthGuard extends StatefulWidget {
  const AuthGuard({super.key, required this.child});

  final Widget child;

  @override
  State<AuthGuard> createState() => _AuthGuardState();
}

class _AuthGuardState extends State<AuthGuard> {
  final AppStore _store = AppStore.instance;
  bool _redirectScheduled = false;

  void _scheduleRedirect(BuildContext context) {
    if (_redirectScheduled) {
      return;
    }
    _redirectScheduled = true;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }

      final routeName = ModalRoute.of(context)?.settings.name;
      if (routeName == AppRoutes.auth) {
        _redirectScheduled = false;
        return;
      }

      final messenger = ScaffoldMessenger.maybeOf(context);
      final message = _store.lastError.isNotEmpty ? _store.lastError : '请先登录';
      messenger?.showSnackBar(SnackBar(content: Text(message)));
      Navigator.pushNamedAndRemoveUntil(context, AppRoutes.auth, (route) => false);
      _redirectScheduled = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _store,
      builder: (context, _) {
        if (_store.isAuthenticated) {
          _redirectScheduled = false;
          return widget.child;
        }

        _scheduleRedirect(context);
        return const Scaffold(
          body: SafeArea(
            child: Center(child: CircularProgressIndicator()),
          ),
        );
      },
    );
  }
}
