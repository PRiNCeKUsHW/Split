import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'dashboard_screen.dart';
import 'expense_form_screen.dart';
import 'expense_list_screen.dart';
import 'flat_screen.dart';
import 'login_screen.dart';
import 'server_config_screen.dart';
import 'settle_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    DashboardScreen(),
    ExpenseListScreen(),
    SettleScreen(),
    FlatScreen(),
  ];

  void _showProfileModal(BuildContext context, AppState appState) {
    final user = appState.currentUser;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
      builder: (ctx) {
        return Container(
          padding: const EdgeInsets.all(24.0),
          decoration: BoxDecoration(
            border: Border(top: BorderSide(color: inkColor, width: AppColors.borderWidth)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  AvatarChipWidget(
                    initials: user?.initials ?? '?',
                    size: 48,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user?.name ?? 'Flatmate',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            color: isDark ? AppColors.darkInk : AppColors.ink,
                          ),
                        ),
                        Text(
                          '@${user?.username ?? ''}',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: isDark ? AppColors.darkMuted : AppColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              NeobrutalCard(
                backgroundColor: AppColors.infoFill,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                child: Row(
                  children: [
                    const Icon(Icons.apartment, size: 20, color: Colors.black),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Flat: ${appState.flatName}',
                        style: const TextStyle(fontWeight: FontWeight.w800, color: Colors.black, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              NeobrutalButton(
                text: 'LOGOUT',
                icon: Icons.logout,
                backgroundColor: AppColors.debitFill,
                textColor: Colors.black,
                onPressed: () async {
                  await appState.logout();
                  if (context.mounted) {
                    Navigator.of(context).pushAndRemoveUntil(
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                      (route) => false,
                    );
                  }
                },
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;
    final user = appState.currentUser;

    return Scaffold(
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(58),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.topbar,
            border: Border(
              bottom: BorderSide(color: AppColors.ink, width: AppColors.borderWidth),
            ),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 6.0),
              child: Row(
                children: [
                  // Signature Web Brand: ₹ FLATSPLIT
                  GestureDetector(
                    onTap: () => setState(() => _currentIndex = 0),
                    child: Row(
                      children: const [
                        Text(
                          '₹',
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontSize: 22,
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF0A0A0A),
                          ),
                        ),
                        SizedBox(width: 6),
                        Text(
                          'FLATSPLIT',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.5,
                            color: Color(0xFF0A0A0A),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),
                  // Square Theme Toggle Button
                  _topbarSquareButton(
                    icon: isDark ? Icons.light_mode : Icons.dark_mode,
                    onTap: () {
                      appState.setThemeMode(isDark ? ThemeMode.light : ThemeMode.dark);
                    },
                  ),
                  const SizedBox(width: 8),
                  // Square Server Settings Button
                  _topbarSquareButton(
                    icon: Icons.dns_outlined,
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ServerConfigScreen()),
                      );
                    },
                  ),
                  const SizedBox(width: 8),
                  // Avatar Chip
                  AvatarChipWidget(
                    initials: user?.initials ?? 'FS',
                    size: 38,
                    onTap: () => _showProfileModal(context, appState),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      // 5-Slot Bottom Navigation matching FlatSplit Web
      bottomNavigationBar: Container(
        height: 66 + MediaQuery.of(context).padding.bottom,
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).padding.bottom),
        decoration: BoxDecoration(
          color: isDark ? AppColors.darkSurface : AppColors.surface,
          border: Border(
            top: BorderSide(color: inkColor, width: AppColors.borderWidth),
          ),
        ),
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            Row(
              children: [
                _webNavItem(
                  targetIndex: 0,
                  icon: Icons.home_outlined,
                  selectedIcon: Icons.home,
                  label: 'Home',
                ),
                _webNavItem(
                  targetIndex: 1,
                  icon: Icons.receipt_long_outlined,
                  selectedIcon: Icons.receipt_long,
                  label: 'Expenses',
                ),
                // Center spacer for the raised Add FAB
                Expanded(
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ExpenseFormScreen()),
                      );
                    },
                    child: Container(
                      decoration: BoxDecoration(
                        border: Border(
                          right: BorderSide(color: inkColor, width: AppColors.thinBorderWidth),
                        ),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Text(
                            'ADD',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.5,
                              color: isDark ? AppColors.darkInk : AppColors.ink,
                            ),
                          ),
                          const SizedBox(height: 6),
                        ],
                      ),
                    ),
                  ),
                ),
                _webNavItem(
                  targetIndex: 2,
                  icon: Icons.swap_horiz,
                  selectedIcon: Icons.swap_horiz,
                  label: 'Settle',
                  badgeCount: appState.awaitingConfirmation.length,
                ),
                _webNavItem(
                  targetIndex: 3,
                  icon: Icons.bar_chart,
                  selectedIcon: Icons.bar_chart,
                  label: 'Flat',
                  isLast: true,
                ),
              ],
            ),
            // Floating Raised Square FAB in the center
            Positioned(
              top: -22,
              left: MediaQuery.of(context).size.width / 2 - 25,
              child: GestureDetector(
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const ExpenseFormScreen()),
                  );
                },
                child: Container(
                  width: 50,
                  height: 50,
                  decoration: BoxDecoration(
                    color: AppColors.action,
                    border: Border.all(color: Colors.black, width: AppColors.borderWidth),
                    boxShadow: const [
                      BoxShadow(
                        color: Colors.black,
                        offset: Offset(AppColors.shadowOffset, AppColors.shadowOffset),
                        blurRadius: 0,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Icon(Icons.add, color: Colors.black, size: 28),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _topbarSquareButton({required IconData icon, required VoidCallback onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: Colors.black, width: AppColors.thinBorderWidth),
          boxShadow: const [
            BoxShadow(
              color: Colors.black,
              offset: Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
              blurRadius: 0,
            ),
          ],
        ),
        child: Center(
          child: Icon(icon, color: Colors.black, size: 20),
        ),
      ),
    );
  }

  Widget _webNavItem({
    required int targetIndex,
    required IconData icon,
    required IconData selectedIcon,
    required String label,
    int badgeCount = 0,
    bool isLast = false,
  }) {
    final isSelected = _currentIndex == targetIndex;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => setState(() => _currentIndex = targetIndex),
        child: Container(
          height: 66,
          decoration: BoxDecoration(
            color: isSelected ? AppColors.action : Colors.transparent,
            border: Border(
              right: isLast
                  ? BorderSide.none
                  : BorderSide(color: inkColor, width: AppColors.thinBorderWidth),
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  Icon(
                    isSelected ? selectedIcon : icon,
                    color: isSelected
                        ? Colors.black
                        : (isDark ? AppColors.darkMuted : AppColors.muted),
                    size: 22,
                  ),
                  if (badgeCount > 0)
                    Positioned(
                      top: -4,
                      right: -10,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                        decoration: BoxDecoration(
                          color: AppColors.debitFill,
                          border: Border.all(color: Colors.black, width: 1.5),
                        ),
                        child: Text(
                          '$badgeCount',
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w900,
                            color: Colors.black,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 3),
              Text(
                label.toUpperCase(),
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: isSelected ? FontWeight.w900 : FontWeight.w700,
                  letterSpacing: 0.4,
                  color: isSelected
                      ? Colors.black
                      : (isDark ? AppColors.darkMuted : AppColors.muted),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
