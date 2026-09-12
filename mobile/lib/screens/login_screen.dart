import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'main_shell.dart';
import 'server_config_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _submit() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text;
    if (username.isEmpty) return;

    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.login(username, password);
    if (ok && mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const MainShell()),
        (route) => false,
      );
    }
  }

  void _quickLogin(String username) async {
    _usernameController.text = username;
    _passwordController.text = 'flatsplit';
    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.login(username, 'flatsplit');
    if (ok && mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const MainShell()),
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  GestureDetector(
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ServerConfigScreen()),
                      );
                    },
                    child: NeobrutalBadge(
                      label: 'HOST: ${appState.serverUrl.replaceAll('http://', '')}',
                      backgroundColor: AppColors.infoFill,
                      icon: Icons.wifi,
                    ),
                  ),
                  IconButton(
                    icon: Icon(
                      isDark ? Icons.light_mode : Icons.dark_mode,
                      color: isDark ? AppColors.darkInk : AppColors.ink,
                    ),
                    onPressed: () {
                      appState.setThemeMode(isDark ? ThemeMode.light : ThemeMode.dark);
                    },
                  ),
                ],
              ),
              const SizedBox(height: 32),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.action,
                  border: Border.all(
                    color: isDark ? AppColors.darkInk : AppColors.ink,
                    width: AppColors.borderWidth,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: isDark ? AppColors.darkInk : AppColors.ink,
                      offset: const Offset(4, 4),
                      blurRadius: 0,
                    ),
                  ],
                ),
                child: const Text(
                  'FLATSPLIT',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 2.0,
                    color: Colors.black,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Expense splitting for flatmates over local Wi-Fi.',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                ),
              ),
              const SizedBox(height: 36),
              if (appState.errorMessage != null) ...[
                NeobrutalCard(
                  backgroundColor: AppColors.debitFill,
                  child: Text(
                    appState.errorMessage!,
                    style: const TextStyle(fontWeight: FontWeight.w700, color: Colors.black),
                  ),
                ),
                const SizedBox(height: 20),
              ],
              NeobrutalTextField(
                controller: _usernameController,
                label: 'Username',
                hint: 'e.g. anuj',
              ),
              NeobrutalTextField(
                controller: _passwordController,
                label: 'Password',
                hint: '••••••••',
                obscureText: true,
              ),
              const SizedBox(height: 8),
              NeobrutalButton(
                text: 'LOG IN',
                onPressed: appState.isLoading ? null : _submit,
                isLoading: appState.isLoading,
                backgroundColor: AppColors.action,
              ),
              const SizedBox(height: 36),
              Text(
                'QUICK DEMO FLATMATES',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8,
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _flatmateChip('anuj', 'Anuj (Admin)', AppColors.creditFill),
                  _flatmateChip('priya', 'Priya', AppColors.action),
                  _flatmateChip('rohit', 'Rohit', AppColors.infoFill),
                  _flatmateChip('meera', 'Meera', AppColors.debitFill),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _flatmateChip(String username, String label, Color color) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return GestureDetector(
      onTap: () => _quickLogin(username),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: color,
          border: Border.all(color: inkColor, width: 2.5),
          boxShadow: [
            BoxShadow(
              color: inkColor,
              offset: const Offset(3, 3),
              blurRadius: 0,
            ),
          ],
        ),
        child: Text(
          label,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 13,
            color: Colors.black,
          ),
        ),
      ),
    );
  }
}
