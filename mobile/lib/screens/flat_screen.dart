import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'edit_profile_screen.dart';
import 'login_screen.dart';
import 'server_config_screen.dart';

class FlatScreen extends StatefulWidget {
  final bool showAppBar;
  const FlatScreen({super.key, this.showAppBar = false});

  @override
  State<FlatScreen> createState() => _FlatScreenState();
}

class _FlatScreenState extends State<FlatScreen> {
  int _year = DateTime.now().year;
  int _month = DateTime.now().month;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadSummary();
    });
  }

  void _loadSummary() {
    final appState = Provider.of<AppState>(context, listen: false);
    appState.fetchSummary(year: _year, month: _month);
  }

  void _prevMonth() {
    setState(() {
      if (_month == 1) {
        _month = 12;
        _year -= 1;
      } else {
        _month -= 1;
      }
    });
    _loadSummary();
  }

  void _nextMonth() {
    setState(() {
      if (_month == 12) {
        _month = 1;
        _year += 1;
      } else {
        _month += 1;
      }
    });
    _loadSummary();
  }

  void _toggleMonth(bool isClosed) async {
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
          isClosed ? 'REOPEN MONTH' : 'CLOSE MONTH',
          style: TextStyle(fontWeight: FontWeight.w900, color: inkColor),
        ),
        content: Text(
          isClosed
              ? 'Reopen editing for this month?'
              : 'Close this month? Its expenses will become read-only.',
          style: TextStyle(color: inkColor),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text('CANCEL', style: TextStyle(color: inkColor)),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('CONFIRM', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.black)),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      final appState = Provider.of<AppState>(context, listen: false);
      await appState.toggleMonth(year: _year, month: _month, reopen: isClosed);
    }
  }

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
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    final summary = appState.summary;
    final monthLabel = summary?['month_label'] ?? DateFormat('MMMM yyyy').format(DateTime(_year, _month));
    final grandTotal = summary?['grand_total']?.toString() ?? '0.00';
    final expenseCount = summary?['expense_count'] ?? 0;
    final isClosed = summary?['is_closed'] as bool? ?? false;
    final byCategory = (summary?['by_category'] as List?) ?? [];
    final perPerson = (summary?['per_person'] as List?) ?? [];

    Widget content = RefreshIndicator(
      onRefresh: () async {
        _loadSummary();
        await appState.refreshAll();
      },
      color: Colors.black,
      backgroundColor: AppColors.action,
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // 1. Month Selector Bar (matching Web App: ← Month Year →)
          Row(
            children: [
              GestureDetector(
                onTap: _prevMonth,
                child: Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkSurface : AppColors.surface,
                    border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                    boxShadow: [
                      BoxShadow(
                        color: inkColor,
                        offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
                        blurRadius: 0,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Icon(Icons.arrow_back, size: 18),
                  ),
                ),
              ),
              Expanded(
                child: Center(
                  child: Text(
                    monthLabel,
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.3,
                      color: inkColor,
                    ),
                  ),
                ),
              ),
              GestureDetector(
                onTap: _nextMonth,
                child: Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkSurface : AppColors.surface,
                    border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                    boxShadow: [
                      BoxShadow(
                        color: inkColor,
                        offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
                        blurRadius: 0,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Icon(Icons.arrow_forward, size: 18),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // 2. Flat Spent Hero Card (.balance-hero is-settled)
          NeobrutalCard(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'FLAT SPENT',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                    color: isDark ? AppColors.darkMuted : AppColors.muted,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '₹$grandTotal',
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 34,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -1.0,
                    color: inkColor,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '$expenseCount expense${expenseCount == 1 ? '' : 's'}${isClosed ? ' · month closed' : ''}',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: isDark ? AppColors.darkMuted : AppColors.muted,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 3. Where It Went (Category progress bars matching Web App)
          Text(
            'WHERE IT WENT',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
              color: inkColor,
            ),
          ),
          const SizedBox(height: 8),
          NeobrutalCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: byCategory.isEmpty
                ? Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12.0),
                    child: Center(
                      child: Text(
                        'Nothing spent this month.',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: isDark ? AppColors.darkMuted : AppColors.muted,
                        ),
                      ),
                    ),
                  )
                : Column(
                    children: byCategory.asMap().entries.map((entry) {
                      final idx = entry.key;
                      final row = entry.value;
                      final isLast = idx == byCategory.length - 1;

                      final catName = row['category__name'] ?? 'Uncategorized';
                      final colorHex = row['category__color'] ?? '#A78BFA';
                      final catColor = Color(int.parse(colorHex.replaceFirst('#', '0xFF')));
                      final total = row['total']?.toString() ?? '0.00';
                      final percent = (row['percent'] as num?)?.toDouble() ?? 0.0;

                      return Container(
                        padding: const EdgeInsets.symmetric(vertical: 8.0),
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
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                CategoryDot(color: catColor, size: 12),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    catName,
                                    style: TextStyle(
                                      fontWeight: FontWeight.w800,
                                      fontSize: 13,
                                      color: inkColor,
                                    ),
                                  ),
                                ),
                                Text(
                                  '₹$total',
                                  style: TextStyle(
                                    fontFamily: 'monospace',
                                    fontWeight: FontWeight.w800,
                                    fontSize: 13,
                                    color: inkColor,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            // Bar track (.bar-track)
                            Container(
                              height: 16,
                              width: double.infinity,
                              decoration: BoxDecoration(
                                color: isDark ? AppColors.darkPaper : AppColors.paper,
                                border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                              ),
                              child: FractionallySizedBox(
                                alignment: Alignment.centerLeft,
                                widthFactor: (percent / 100).clamp(0.0, 1.0),
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: catColor,
                                    border: Border(
                                      right: BorderSide(color: inkColor, width: AppColors.thinBorderWidth),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
          ),
          const SizedBox(height: 20),

          // 4. Per Person Section (ledger rows matching Web App)
          Text(
            'PER PERSON',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
              color: inkColor,
            ),
          ),
          const SizedBox(height: 8),
          NeobrutalCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
            child: perPerson.isEmpty
                ? Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12.0),
                    child: Center(
                      child: Text(
                        'No flatmate data.',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: isDark ? AppColors.darkMuted : AppColors.muted,
                        ),
                      ),
                    ),
                  )
                : Column(
                    children: perPerson.asMap().entries.map((entry) {
                      final idx = entry.key;
                      final row = entry.value;
                      final isLast = idx == perPerson.length - 1;

                      final person = row['person'] as Map<String, dynamic>;
                      final initials = person['initials'] ?? '?';
                      final name = person['name'] ?? 'Flatmate';
                      final paid = row['paid'] ?? '0.00';
                      final share = row['share'] ?? '0.00';
                      final diffNum = (row['diff_num'] as num?)?.toDouble() ?? 0.0;
                      final diffStr = row['diff']?.toString() ?? '0.00';

                      Color diffColor = inkColor;
                      String formattedDiff = '₹0.00';
                      if (diffNum > 0) {
                        diffColor = isDark ? AppColors.darkCreditText : AppColors.creditText;
                        formattedDiff = '+₹$diffStr';
                      } else if (diffNum < 0) {
                        diffColor = isDark ? AppColors.darkDebitText : AppColors.debitText;
                        formattedDiff = '-₹${diffStr.replaceAll('-', '')}';
                      }

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
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(top: 2.0),
                              child: AvatarChipWidget(initials: initials, size: 32, hasShadow: false),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Text(
                                        name,
                                        style: TextStyle(
                                          fontWeight: FontWeight.w800,
                                          fontSize: 14,
                                          color: inkColor,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      const Expanded(child: DottedLeaderLine()),
                                      const SizedBox(width: 8),
                                      Text(
                                        formattedDiff,
                                        style: TextStyle(
                                          fontFamily: 'monospace',
                                          fontWeight: FontWeight.w800,
                                          fontSize: 15,
                                          color: diffColor,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    'paid ₹$paid · share ₹$share',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
          ),
          const SizedBox(height: 16),

          // 5. Month Close / Reopen Button (matching Web App)
          GestureDetector(
            onTap: () => _toggleMonth(isClosed),
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurface : AppColors.surface,
                border: Border.all(color: inkColor, width: AppColors.borderWidth),
                boxShadow: [
                  BoxShadow(
                    color: inkColor,
                    offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
                    blurRadius: 0,
                  ),
                ],
              ),
              child: Center(
                child: Text(
                  isClosed ? 'REOPEN MONTH' : 'CLOSE MONTH',
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 13,
                    letterSpacing: 0.5,
                    color: inkColor,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // 6. Away Days Section
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
          const SizedBox(height: 8),
          NeobrutalCard(
            backgroundColor: AppColors.infoFill.withValues(alpha: 0.3),
            padding: const EdgeInsets.all(12),
            child: const Text(
              'Both dates count (5th–8th = 4 days). Away days only discount categories flagged "prorate by away days" (food, maid, gas). Rent is never reduced by travel.',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, height: 1.4),
            ),
          ),
          const SizedBox(height: 8),
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

          // 7. Flatmates Directory
          Text(
            'FLATMATES',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 8),
          NeobrutalCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Column(
              children: appState.members.map((m) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Row(
                    children: [
                      AvatarChipWidget(
                        initials: m.initials,
                        size: 32,
                        hasShadow: false,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(m.name, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: inkColor)),
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

          // 8. Profile, Server & Logout
          NeobrutalButton(
            text: 'EDIT MY PROFILE',
            icon: Icons.person,
            backgroundColor: AppColors.creditFill,
            textColor: Colors.black,
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const EditProfileScreen()),
              );
            },
          ),
          const SizedBox(height: 12),
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
          const SizedBox(height: 32),
        ],
      ),
    );

    if (widget.showAppBar) {
      return Scaffold(
        appBar: AppBar(
          title: const Text(
            'SUMMARY',
            style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
          ),
          elevation: 0,
          bottom: PreferredSize(
            preferredSize: const Size.fromHeight(3),
            child: Container(color: inkColor, height: 3),
          ),
        ),
        body: content,
      );
    }

    return content;
  }
}
