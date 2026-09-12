import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/app_state.dart';
import 'screens/splash_screen.dart';
import 'theme/colors.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final appState = AppState();

  runApp(
    ChangeNotifierProvider.value(
      value: appState,
      child: const FlatSplitApp(),
    ),
  );
}

class FlatSplitApp extends StatelessWidget {
  const FlatSplitApp({super.key});

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);

    final lightTheme = ThemeData(
      useMaterial3: false,
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.paper,
      primaryColor: AppColors.action,
      fontFamily: 'sans-serif',
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.surface,
        foregroundColor: AppColors.ink,
        elevation: 0,
      ),
      colorScheme: const ColorScheme.light(
        primary: AppColors.action,
        surface: AppColors.surface,
        onSurface: AppColors.ink,
      ),
    );

    final darkTheme = ThemeData(
      useMaterial3: false,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.darkPaper,
      primaryColor: AppColors.action,
      fontFamily: 'sans-serif',
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.darkSurface,
        foregroundColor: AppColors.darkInk,
        elevation: 0,
      ),
      colorScheme: const ColorScheme.dark(
        primary: AppColors.action,
        surface: AppColors.darkSurface,
        onSurface: AppColors.darkInk,
      ),
    );

    return MaterialApp(
      title: 'FlatSplit',
      debugShowCheckedModeBanner: false,
      themeMode: appState.themeMode,
      theme: lightTheme,
      darkTheme: darkTheme,
      home: const SplashScreen(),
    );
  }
}
