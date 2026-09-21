import 'package:flutter/material.dart';
import '../screens/auth_screen.dart';
import '../screens/home_screen.dart';
import '../screens/item_detail_screen.dart';
import '../screens/list_screen.dart';
import '../screens/log_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/voice_modal_screen.dart';
import '../screens/ocr_modal_screen.dart';
import '../screens/onboarding_screen.dart';
import '../screens/manual_fill_screen.dart';
import '../screens/household_screen.dart';
import '../screens/report_screen.dart';
import '../widgets/auth_guard.dart';

class AppRoutes {
  static const auth = '/auth';
  static const onboarding = '/onboarding';
  static const home = '/home';
  static const list = '/list';
  static const log = '/log';
  static const settings = '/settings';
  static const household = '/household';
  static const report = '/report';
  static const voice = '/voice-modal';
  static const ocr = '/ocr-modal';
  static const manualFill = '/manual-fill';
  static const itemDetail = '/item-detail';

  static Widget _protected(Widget child) {
    return AuthGuard(child: child);
  }

  static final routes = <String, WidgetBuilder>{
    auth: (_) => const AuthScreen(),
    onboarding: (_) => _protected(const OnboardingScreen()),
    home: (_) => _protected(const HomeScreen()),
    list: (_) => _protected(const ListScreen()),
    log: (_) => _protected(const LogScreen()),
    settings: (_) => _protected(const SettingsScreen()),
    household: (_) => _protected(const HouseholdScreen()),
    report: (_) => _protected(const ReportScreen()),
    voice: (_) => _protected(const VoiceModalScreen()),
    ocr: (_) => _protected(const OcrModalScreen()),
    manualFill: (_) => _protected(const ManualFillScreen()),
    itemDetail: (_) => _protected(const ItemDetailScreen()),
  };
}
