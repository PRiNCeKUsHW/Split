import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class BalancesScreen extends StatefulWidget {
  const BalancesScreen({super.key});

  @override
  State<BalancesScreen> createState() => _BalancesScreenState();
}

class _BalancesScreenState extends State<BalancesScreen> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _rows = [];
  List<Map<String, dynamic>> _closedMonths = [];

  @override
  void initState() {
    super.initState();
    _loadBalances();
  }

  void _loadBalances() async {
    setState(() => _isLoading = true);
    try {
      final appState = Provider.of<AppState>(context, listen: false);
      final client = appState.client;
      final res = await client.get('/api/balances');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        setState(() {
          _rows = (data['rows'] as List).map((r) => r as Map<String, dynamic>).toList();
          _closedMonths = (data['closed_months'] as List).map((c) => c as Map<String, dynamic>).toList();
          _isLoading = false;
        });
        return;
      }
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'BALANCES',
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
              onRefresh: () async => _loadBalances(),
              color: Colors.black,
              backgroundColor: AppColors.action,
              child: ListView(
                padding: const EdgeInsets.all(16.0),
                children: [
                  Text(
                    'What each person paid out, minus what they used, plus what they have settled.',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                    ),
                  ),
                  const SizedBox(height: 14),

                  // Balances Card (.card-flat)
                  NeobrutalCard(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                    child: Column(
                      children: _rows.asMap().entries.map((entry) {
                        final idx = entry.key;
                        final row = entry.value;
                        final isLast = idx == _rows.length - 1;

                        final user = row['user'] as Map<String, dynamic>?;
                        final name = user?['name'] ?? 'Flatmate';
                        final initials = user?['initials'] ?? '?';

                        final paid = row['paid'] ?? '0.00';
                        final owed = row['owed'] ?? '0.00';
                        final sent = row['sent'];
                        final received = row['received'];

                        final isOwed = row['is_owed'] as bool? ?? false;
                        final owes = row['owes'] as bool? ?? false;
                        final magnitude = row['magnitude'] ?? '0.00';

                        Color amountColor = inkColor;
                        String prefix = '';
                        if (isOwed) {
                          amountColor = isDark ? AppColors.darkCreditText : AppColors.creditText;
                          prefix = '+';
                        } else if (owes) {
                          amountColor = isDark ? AppColors.darkDebitText : AppColors.debitText;
                          prefix = '-';
                        }

                        // Subtitle note
                        final notes = <String>[
                          'paid ₹$paid',
                          'share ₹$owed',
                        ];
                        if (sent != null && sent != '0.00') notes.add('sent ₹$sent');
                        if (received != null && received != '0.00') notes.add('got ₹$received');

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
                                child: AvatarChipWidget(
                                  initials: initials,
                                  size: 32,
                                  hasShadow: false,
                                ),
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
                                          '$prefix₹$magnitude',
                                          style: TextStyle(
                                            fontFamily: 'monospace',
                                            fontSize: 15,
                                            fontWeight: FontWeight.w800,
                                            color: amountColor,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      notes.join(' · '),
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
                  const SizedBox(height: 24),

                  // Closed Months (if any)
                  if (_closedMonths.isNotEmpty) ...[
                    Text(
                      'CLOSED MONTHS',
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
                      child: Column(
                        children: _closedMonths.asMap().entries.map((entry) {
                          final idx = entry.key;
                          final c = entry.value;
                          final isLast = idx == _closedMonths.length - 1;

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
                                Text(
                                  c['label'] ?? '',
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
                                  c['closed_by'] ?? '',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: isDark ? AppColors.darkMuted : AppColors.muted,
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],
                ],
              ),
            ),
    );
  }
}
