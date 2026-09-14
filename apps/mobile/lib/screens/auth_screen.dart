import 'dart:async';

import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../routes/app_routes.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _store = AppStore.instance;
  final _phoneController = TextEditingController(text: '13800138000');
  final _codeController = TextEditingController();
  bool _agreed = true;
  bool _checkingSession = true;
  bool _sending = false;
  bool _loggingIn = false;
  int _countdown = 0;
  Timer? _timer;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _phoneController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  bool get _canSendCode => _countdown == 0 && !_sending;

  Future<void> _restoreSession() async {
    await _store.initializeSession();
    if (!mounted) {
      return;
    }
    if (_store.isAuthenticated) {
      Navigator.pushReplacementNamed(context, AppRoutes.home);
      return;
    }
    setState(() {
      _checkingSession = false;
      if (_store.lastError.isNotEmpty) {
        _error = _store.lastError;
      }
    });
  }

  Future<void> _sendCode() async {
    final phone = _phoneController.text.trim();
    if (!_isPhone(phone)) {
      setState(() => _error = '手机号格式错误');
      return;
    }
    setState(() {
      _sending = true;
      _error = '';
    });
    try {
      await _store.sendSmsCode(phone);
      if (!mounted) {
        return;
      }
      setState(() => _countdown = 60);
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _sending = false);
      }
    }

    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_countdown <= 1) {
        timer.cancel();
        setState(() => _countdown = 0);
      } else {
        setState(() => _countdown -= 1);
      }
    });
  }

  bool _isPhone(String phone) {
    final regex = RegExp(r'^1\d{10}$');
    return regex.hasMatch(phone);
  }

  Future<void> _login() async {
    final phone = _phoneController.text.trim();
    final code = _codeController.text.trim();

    if (!_agreed) {
      setState(() => _error = '请先勾选隐私协议');
      return;
    }
    if (!_isPhone(phone)) {
      setState(() => _error = '手机号格式错误');
      return;
    }
    if (code.length != 6) {
      setState(() => _error = '验证码应为 6 位');
      return;
    }

    setState(() {
      _loggingIn = true;
      _error = '';
    });
    final ok = await _store.login(phone: phone, code: code, deviceId: _store.deviceId);
    if (!mounted) {
      return;
    }
    setState(() => _loggingIn = false);
    if (!ok) {
      setState(() => _error = _store.lastError.isEmpty ? '登录失败' : _store.lastError);
      return;
    }
    Navigator.pushReplacementNamed(context, AppRoutes.onboarding);
  }

  @override
  Widget build(BuildContext context) {
    if (_checkingSession || _store.hydratingSession) {
      return const Scaffold(
        body: SafeArea(
          child: Center(
            child: CircularProgressIndicator(),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('登录')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('手机号 + 验证码登录', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _phoneController,
                      keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(labelText: '手机号', border: OutlineInputBorder()),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _codeController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(labelText: '验证码', border: OutlineInputBorder()),
                          ),
                        ),
                        const SizedBox(width: 8),
                        FilledButton.tonal(
                          onPressed: _canSendCode ? _sendCode : null,
                          child: Text(_countdown > 0 ? '$_countdown s' : (_sending ? '发送中...' : '发送验证码')),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _agreed,
                      title: const Text('我已阅读并同意隐私协议'),
                      onChanged: (next) => setState(() => _agreed = next ?? false),
                    ),
                    if (_error.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(_error, style: const TextStyle(color: Color(0xFFC9410A))),
                    ],
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _loggingIn ? null : _login,
                        child: Text(_loggingIn ? '登录中...' : '登录'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
