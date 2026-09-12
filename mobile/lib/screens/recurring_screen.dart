import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class RecurringScreen extends StatelessWidget {
  const RecurringScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return RefreshIndicator(
      onRefresh: () => appState.fetchRecurring(),
      color: Colors.black,
      backgroundColor: AppColors.action,
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          NeobrutalCard(
            backgroundColor: AppColors.infoFill,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text(
                  'RECURRING BILLS',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, letterSpacing: 0.8),
                ),
                SizedBox(height: 6),
                Text(
                  'Templates produce expenses automatically each month. Variable bills (like electricity) arrive as drafts to fill in.',
                  style: TextStyle(fontSize: 12, color: Colors.black87, height: 1.4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          NeobrutalButton(
            text: 'GENERATE THIS MONTH\'S BILLS',
            icon: Icons.auto_awesome,
            backgroundColor: AppColors.action,
            onPressed: () async {
              final ok = await appState.generateRecurring();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      ok
                          ? 'Generated recurring bills for this month!'
                          : 'No new bills to generate (already generated).',
                    ),
                  ),
                );
              }
            },
          ),
          const SizedBox(height: 24),
          Text(
            'ACTIVE TEMPLATES',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          if (appState.recurringTemplates.isEmpty)
            NeobrutalCard(
              child: Text(
                'No recurring templates created.',
                style: TextStyle(
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          else
            ...appState.recurringTemplates.map((t) {
              final cat = t['category'] as Map<String, dynamic>?;
              final isVar = t['is_variable'] as bool? ?? false;
              final amount = t['amount']?.toString();
              final day = t['day_of_month'];

              return Padding(
                padding: const EdgeInsets.only(bottom: 12.0),
                child: NeobrutalCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              t['description'] ?? '',
                              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
                            ),
                          ),
                          if (isVar)
                            const NeobrutalBadge(label: 'VARIABLE', backgroundColor: AppColors.infoFill)
                          else if (amount != null)
                            MoneyText(amount: amount, fontSize: 16, fontWeight: FontWeight.w900),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          if (cat != null) ...[
                            NeobrutalBadge(
                              label: cat['name'] ?? '',
                              backgroundColor: AppColors.action,
                            ),
                            const SizedBox(width: 8),
                          ],
                          Text(
                            'Due day $day · ${t['frequency_label'] ?? 'Monthly'}',
                            style: TextStyle(
                              fontSize: 12,
                              color: isDark ? AppColors.darkMuted : AppColors.muted,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }
}
