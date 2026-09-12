import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class AwayDaysScreen extends StatefulWidget {
  const AwayDaysScreen({super.key});

  @override
  State<AwayDaysScreen> createState() => _AwayDaysScreenState();
}

class _AwayDaysScreenState extends State<AwayDaysScreen> {
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAway();
    });
  }

  Future<void> _loadAway() async {
    setState(() => _isLoading = true);
    final appState = Provider.of<AppState>(context, listen: false);
    await appState.fetchAwayPeriods();
    if (mounted) setState(() => _isLoading = false);
  }

  void _markDaysAway() async {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;
    final now = DateTime.now();

    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
      initialDateRange: DateTimeRange(start: now, end: now.add(const Duration(days: 3))),
      helpText: 'MARK EVERY DAY YOU WERE AWAY FOR DINNER',
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: AppColors.action,
              onPrimary: Colors.black,
              surface: isDark ? AppColors.darkSurface : AppColors.surface,
              onSurface: inkColor,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null && mounted) {
      final startStr = DateFormat('yyyy-MM-dd').format(picked.start);
      final endStr = DateFormat('yyyy-MM-dd').format(picked.end);
      final appState = Provider.of<AppState>(context, listen: false);
      final ok = await appState.createAwayPeriod(startStr, endStr);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ok ? 'Away period logged!' : 'Failed to log away period.'),
            backgroundColor: ok ? AppColors.creditText : AppColors.debitText,
          ),
        );
      }
    }
  }

  void _confirmDelete(int periodId) async {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
        shape: RoundedRectangleBorder(
          side: BorderSide(color: inkColor, width: AppColors.borderWidth),
          borderRadius: BorderRadius.zero,
        ),
        title: Text(
          'REMOVE AWAY PERIOD',
          style: TextStyle(fontWeight: FontWeight.w900, color: inkColor),
        ),
        content: Text(
          'Are you sure you want to remove this away period?',
          style: TextStyle(color: inkColor),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text('CANCEL', style: TextStyle(color: inkColor)),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('REMOVE', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      final appState = Provider.of<AppState>(context, listen: false);
      final ok = await appState.deleteAwayPeriod(periodId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ok ? 'Away period removed.' : 'Failed to remove away period.'),
          ),
        );
      }
    }
  }

  String _formatRange(String? start, String? end) {
    if (start == null || end == null) return '';
    try {
      final s = DateTime.parse(start);
      final e = DateTime.parse(end);
      final sStr = DateFormat('d MMM').format(s);
      final eStr = DateFormat('d MMM yyyy').format(e);
      return '$sStr – $eStr';
    } catch (_) {
      return '$start – $end';
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;
    final periods = appState.awayPeriods;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'AWAY DAYS',
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
        ),
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: Container(color: inkColor, height: 3),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.black))
          : RefreshIndicator(
              onRefresh: _loadAway,
              color: Colors.black,
              backgroundColor: AppColors.action,
              child: ListView(
                padding: const EdgeInsets.all(16.0),
                children: [
                  Text(
                    'Mark the days you were not in the flat. Groceries, gas and the maid are then split by who was actually here. Rent is not — your room stays yours.',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Button to mark days away
                  NeobrutalButton(
                    text: '+ MARK DAYS AWAY',
                    backgroundColor: AppColors.action,
                    textColor: Colors.black,
                    onPressed: _markDaysAway,
                  ),
                  const SizedBox(height: 24),

                  Text(
                    'MARKED SO FAR',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1.0,
                      color: inkColor,
                    ),
                  ),
                  const SizedBox(height: 8),

                  NeobrutalCard(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                    child: periods.isEmpty
                        ? Padding(
                            padding: const EdgeInsets.symmetric(vertical: 20.0),
                            child: Center(
                              child: Text(
                                'No away days marked yet.',
                                style: TextStyle(
                                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          )
                        : Column(
                            children: periods.asMap().entries.map((entry) {
                              final idx = entry.key;
                              final p = entry.value;
                              final isLast = idx == periods.length - 1;

                              final user = p['user'] as Map<String, dynamic>?;
                              final name = user?['name'] ?? 'Flatmate';
                              final initials = user?['initials'] ?? '?';
                              final rangeStr = _formatRange(p['start_date'] as String?, p['end_date'] as String?);
                              final days = p['days_count'] ?? 1;
                              final isMine = p['is_mine'] as bool? ?? false;
                              final id = p['id'] as int? ?? 0;

                              return Container(
                                padding: const EdgeInsets.symmetric(vertical: 10.0),
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
                                      initials: initials,
                                      size: 32,
                                      hasShadow: false,
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            name,
                                            style: TextStyle(
                                              fontSize: 13,
                                              fontWeight: FontWeight.w800,
                                              color: inkColor,
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            rangeStr,
                                            style: TextStyle(
                                              fontSize: 11,
                                              fontWeight: FontWeight.w600,
                                              color: isDark ? AppColors.darkMuted : AppColors.muted,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: isDark ? AppColors.darkSurface : const Color(0xFFEEEEEE),
                                        border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                                      ),
                                      child: Text(
                                        '${days}d',
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w900,
                                          fontFamily: 'monospace',
                                          color: inkColor,
                                        ),
                                      ),
                                    ),
                                    if (isMine) ...[
                                      const SizedBox(width: 6),
                                      IconButton(
                                        icon: const Icon(Icons.close, size: 16),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        color: isDark ? AppColors.darkMuted : AppColors.muted,
                                        tooltip: 'Remove',
                                        onPressed: () => _confirmDelete(id),
                                      ),
                                    ],
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
