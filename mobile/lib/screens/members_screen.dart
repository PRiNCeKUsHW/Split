import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class MembersScreen extends StatelessWidget {
  const MembersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'FLATMATES',
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
        ),
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: Container(color: inkColor, height: 3),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () => appState.fetchMembers(),
        color: Colors.black,
        backgroundColor: AppColors.action,
        child: ListView(
          padding: const EdgeInsets.all(16.0),
          children: [
            NeobrutalCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: appState.members.isEmpty
                  ? Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16.0),
                      child: Center(
                        child: Text(
                          'No flatmates found.',
                          style: TextStyle(
                            color: isDark ? AppColors.darkMuted : AppColors.muted,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    )
                  : Column(
                      children: appState.members.asMap().entries.map((entry) {
                        final idx = entry.key;
                        final m = entry.value;
                        final isLast = idx == appState.members.length - 1;

                        return Container(
                          padding: const EdgeInsets.symmetric(vertical: 12.0),
                          decoration: BoxDecoration(
                            border: isLast
                                ? null
                                : Border(
                                    bottom: BorderSide(
                                      color: inkColor,
                                      width: AppColors.thinBorderWidth,
                                    ),
                                  ),
                          ),
                          child: Row(
                            children: [
                              AvatarChipWidget(
                                initials: m.initials,
                                size: 36,
                                hasShadow: false,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      m.name,
                                      style: TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 15,
                                        color: inkColor,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      m.upiId.isNotEmpty ? m.upiId : '@${m.username}',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontFamily: 'monospace',
                                        color: isDark ? AppColors.darkMuted : AppColors.muted,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              if (m.isStaff)
                                const NeobrutalBadge(
                                  label: 'ADMIN',
                                  backgroundColor: AppColors.action,
                                  textColor: Colors.black,
                                ),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
