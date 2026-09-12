import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'login_screen.dart';
import 'main_shell.dart';
import 'server_config_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  String _status = 'Starting FlatSplit...';
  bool _showTroubleshooting = false;
  Timer? _troubleTimer;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    // After 4 seconds of waiting, show server config option
    _troubleTimer = Timer(const Duration(seconds: 4), () {
      if (mounted) {
        setState(() {
          _showTroubleshooting = true;
          _status = 'Connecting taking longer than usual...';
        });
      }
    });

    _initializeApp();
  }

  @override
  void dispose() {
    _animController.dispose();
    _troubleTimer?.cancel();
    super.dispose();
  }

  Future<void> _initializeApp() async {
    final appState = Provider.of<AppState>(context, listen: false);

    try {
      if (mounted) {
        setState(() => _status = 'Checking local ledger...');
      }

      // Allow a brief moment for smooth visual presentation
      final minWait = Future.delayed(const Duration(milliseconds: 800));
      final initTask = appState.init();

      await Future.wait([minWait, initTask]);
    } catch (_) {
      // Ignored: handled gracefully below
    }

    if (!mounted) return;

    // Navigate to appropriate screen with smooth fade
    if (appState.isAuthenticated) {
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => const MainShell(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) =>
              FadeTransition(opacity: animation, child: child),
          transitionDuration: const Duration(milliseconds: 300),
        ),
      );
    } else {
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => const LoginScreen(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) =>
              FadeTransition(opacity: animation, child: child),
          transitionDuration: const Duration(milliseconds: 300),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    const inkColor = AppColors.ink;
    const purpleBg = AppColors.action; // FlatSplit purple (#A78BFA)

    return Scaffold(
      backgroundColor: purpleBg,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
          child: Column(
            children: [
              const Spacer(flex: 2),

              // Hero Neobrutalist Emblem
              Center(
                child: Container(
                  width: 104,
                  height: 104,
                  decoration: BoxDecoration(
                    color: AppColors.creditFill, // Electric Lime #BEF264
                    border: Border.all(color: inkColor, width: AppColors.borderWidth),
                    boxShadow: const [
                      BoxShadow(
                        color: inkColor,
                        offset: Offset(
                          AppColors.largeShadowOffset,
                          AppColors.largeShadowOffset,
                        ),
                        blurRadius: 0,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text(
                      '₹',
                      style: TextStyle(
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.w900,
                        fontSize: 54,
                        color: inkColor,
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 28),

              // App Title
              const Text(
                'FLATSPLIT',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 34,
                  letterSpacing: 2.0,
                  color: inkColor,
                ),
              ),

              const SizedBox(height: 10),

              // Tagline
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.white,
                  border: Border.all(
                    color: inkColor,
                    width: AppColors.thinBorderWidth,
                  ),
                  boxShadow: const [
                    BoxShadow(
                      color: inkColor,
                      offset: Offset(
                        AppColors.smallShadowOffset,
                        AppColors.smallShadowOffset,
                      ),
                      blurRadius: 0,
                    ),
                  ],
                ),
                child: const Text(
                  'SHARED LIVING • LOCAL FIRST',
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w800,
                    fontSize: 11,
                    letterSpacing: 0.8,
                    color: inkColor,
                  ),
                ),
              ),

              const Spacer(flex: 2),

              // Animated Neobrutalist Progress Bar
              Container(
                width: 220,
                height: 16,
                decoration: BoxDecoration(
                  color: Colors.white,
                  border: Border.all(color: inkColor, width: 2.5),
                  boxShadow: const [
                    BoxShadow(
                      color: inkColor,
                      offset: Offset(2.5, 2.5),
                      blurRadius: 0,
                    ),
                  ],
                ),
                child: AnimatedBuilder(
                  animation: _animController,
                  builder: (context, child) {
                    return FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: 0.25 + (_animController.value * 0.70),
                      child: Container(
                        color: AppColors.creditFill,
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 14),

              // Status message
              Text(
                _status,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                  color: inkColor,
                ),
                textAlign: TextAlign.center,
              ),

              // Troubleshooting options if loading is slow
              if (_showTroubleshooting) ...[
                const SizedBox(height: 24),
                NeobrutalCard(
                  backgroundColor: Colors.white,
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    children: [
                      const Text(
                        'SERVER UNREACHABLE?',
                        style: TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 12,
                          color: inkColor,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: NeobrutalButton(
                              text: 'CONFIG IP',
                              height: 38,
                              backgroundColor: AppColors.infoFill,
                              onPressed: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (_) => const ServerConfigScreen(),
                                  ),
                                );
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: NeobrutalButton(
                              text: 'RETRY',
                              height: 38,
                              backgroundColor: AppColors.creditFill,
                              onPressed: () {
                                setState(() {
                                  _status = 'Retrying connection...';
                                });
                                _initializeApp();
                              },
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],

              const Spacer(flex: 1),

              // Version / System info
              Text(
                'v2.0 • OFFLINE READY • ZERO DRIFT',
                style: TextStyle(
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.w800,
                  fontSize: 11,
                  color: inkColor.withValues(alpha: 0.6),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}
