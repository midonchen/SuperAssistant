import 'package:flutter/material.dart';
import 'routes/app_routes.dart';

void main() {
  runApp(const SuperAssistantApp());
}

class SuperAssistantApp extends StatelessWidget {
  const SuperAssistantApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SuperAssistant',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFE5BE45)),
        scaffoldBackgroundColor: const Color(0xFFF7F6F2),
        cardTheme: const CardThemeData(
          color: Colors.white,
          elevation: 0,
          margin: EdgeInsets.zero,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFE5BE45),
          brightness: Brightness.dark,
        ),
        cardTheme: const CardThemeData(
          elevation: 0,
          margin: EdgeInsets.zero,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      initialRoute: AppRoutes.auth,
      routes: AppRoutes.routes,
    );
  }
}
