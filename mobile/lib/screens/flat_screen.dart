import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'login_screen.dart';
import 'server_config_screen.dart';

class FlatScreen extends StatelessWidget {
  const FlatScreen({super.key});

  void _addAwayPeriod(BuildContext context) async {
    final appState = Provider.of<AppState>(context, listen: false);
    final now = DateTime.now();

    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
      initialDateRange: DateTimeRange(start: now, end: now.add(const Duration(days: 3))),
      helpText: 'MARK EVERY DAY YOU WERE AWAY FOR DINNER',
    );

    if (picked != null) {
      final startStr = DateFormat('yyyy-MM-dd').format(picked.start);
      final endStr = DateFormat('yyyy-MM-dd').format(picked.end);
      final ok = await appState.createAwayPeriod(startStr, endStr);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(ok ? 'Away period logged!' : 'Failed to log away period.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return RefreshIndicator(
      onRefresh: () => appState.refreshAll(),
      color: Colors.black,
      backgroundColor: AppColors.action,
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // 1. Current User Profile Card
          if (appState.currentUser != null) ...[
            NeobrutalCard(
              backgroundColor: AppColors.action,
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: Colors.black,
                    child: Text(
                      appState.currentUser!.initials,
                      style: const TextStyle(fontWeight: FontWeight.w900, color: Colors.white, fontSize: 18),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          appState.currentUser!.name,
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Colors.black),
                        ),
                        Text(
                          '@${appState.currentUser!.username} · ${appState.currentUser!.upiId.isNotEmpty ? appState.currentUser!.upiId : "No UPI set"}',
                          style: const TextStyle(fontSize: 12, color: Colors.black87, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],

          // 2. Away Days Section
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'AWAY DAYS',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.8,
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                ),
              ),
              GestureDetector(
                onTap: () => _addAwayPeriod(context),
                child: const NeobrutalBadge(
                  label: '+ LOG TRIP',
                  backgroundColor: AppColors.creditFill,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          NeobrutalCard(
            backgroundColor: AppColors.infoFill.withValues(alpha: 0.3),
            padding: const EdgeInsets.all(12),
            child: const Text(
              'Both dates count (5th–8th = 4 days). Away days only discount categories flagged "prorate by away days" (food, maid, gas). Rent is never reduced by travel.',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, height: 1.4),
            ),
          ),
          const SizedBox(height: 10),
          if (appState.awayPeriods.isEmpty)
            NeobrutalCard(
              child: Text(
                'No away periods recorded.',
                style: TextStyle(
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          else
            ...appState.awayPeriods.map((p) {
              final user = p['user'] as Map<String, dynamic>?;
              final isMine = p['is_mine'] as bool? ?? false;
              final id = p['id'] as int;
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: NeobrutalCard(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            user != null ? user['name'] : 'Flatmate',
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                          ),
                          Text(
                            '${p['start_date']} to ${p['end_date']} (${p['days_count']} days)',
                            style: TextStyle(fontSize: 12, color: isDark ? AppColors.darkMuted : AppColors.muted),
                          ),
                        ],
                      ),
                      if (isMine)
                        IconButton(
                          icon: const Icon(Icons.close, size: 18, color: Colors.red),
                          onPressed: () => appState.deleteAwayPeriod(id),
                        ),
                    ],
                  ),
                ),
              );
            }),
          const SizedBox(height: 24),

          // 3. Flatmates Directory
          Text(
            'FLATMATES',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          NeobrutalCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Column(
              children: appState.members.map((m) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 14,
                        backgroundColor: AppColors.action,
                        child: Text(
                          m.initials,
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Colors.black),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(m.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
                            Text(
                              m.upiId.isNotEmpty ? m.upiId : 'No UPI ID',
                              style: TextStyle(
                                fontSize: 11,
                                fontFamily: 'monospace',
                                color: isDark ? AppColors.darkMuted : AppColors.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (m.joinedOn != null)
                        Text(
                          'Joined ${m.joinedOn}',
                          style: TextStyle(fontSize: 11, color: isDark ? AppColors.darkMuted : AppColors.muted),
                        ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 24),

          // 4. Categories & Rules Cheat Sheet
          Text(
            'CATEGORY PRORATION RULES',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          NeobrutalCard(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: appState.categories.map((c) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6.0),
                  child: Row(
                    children: [
                      Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(color: c.color, border: Border.all(color: Colors.black, width: 1.5)),
                      ),
                      const SizedBox(width: 8),
                      Text(c.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                      const Spacer(),
                      NeobrutalBadge(
                        label: c.behaviourLabel,
                        backgroundColor: c.prorateByPresence
                            ? AppColors.creditFill
                            : (c.prorateByTenancy ? AppColors.infoFill : AppColors.paper),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 28),

          // 5. Server & Logout
          NeobrutalButton(
            text: 'CONFIGURE SERVER CONNECTION',
            icon: Icons.wifi,
            backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
            textColor: isDark ? AppColors.darkInk : AppColors.ink,
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const ServerConfigScreen()),
              );
            },
          ),
          const SizedBox(height: 12),
          NeobrutalButton(
            text: 'LOG OUT',
            icon: Icons.logout,
            backgroundColor: AppColors.debitFill,
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
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
