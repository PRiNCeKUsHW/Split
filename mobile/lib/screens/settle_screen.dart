import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'record_payment_screen.dart';

class SettleScreen extends StatefulWidget {
  const SettleScreen({super.key});

  @override
  State<SettleScreen> createState() => _SettleScreenState();
}

class _SettleScreenState extends State<SettleScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _confirmPayment(int id) async {
    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.confirmSettlement(id);
    if (ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Payment confirmed! Balances updated.')),
      );
    }
  }

  void _rejectPayment(int id) async {
    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.rejectSettlement(id);
    if (ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Payment marked as rejected.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Column(
      children: [
        // Tab Header
        Container(
          decoration: BoxDecoration(
            color: isDark ? AppColors.darkSurface : AppColors.surface,
            border: Border(
              bottom: BorderSide(color: inkColor, width: AppColors.borderWidth),
            ),
          ),
          child: TabBar(
            controller: _tabController,
            labelColor: isDark ? AppColors.darkInk : AppColors.ink,
            indicatorColor: AppColors.action,
            indicatorWeight: 4,
            labelStyle: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13),
            tabs: [
              const Tab(text: 'BALANCES & HISTORY'),
              Tab(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text('PENDING'),
                    if (appState.awaitingConfirmation.isNotEmpty) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: const BoxDecoration(
                          color: AppColors.debitFill,
                          border: Border.fromBorderSide(BorderSide(color: Colors.black, width: 1.5)),
                        ),
                        child: Text(
                          '${appState.awaitingConfirmation.length}',
                          style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Colors.black),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),

        // Tab Content
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildBalancesTab(appState, isDark),
              _buildPendingTab(appState, isDark),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBalancesTab(AppState appState, bool isDark) {
    return RefreshIndicator(
      onRefresh: () => appState.fetchSettlements(),
      color: Colors.black,
      backgroundColor: AppColors.action,
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // Settle Up Button
          NeobrutalButton(
            text: 'RECORD A SETTLEMENT',
            icon: Icons.payments,
            backgroundColor: AppColors.action,
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const RecordPaymentScreen()),
              );
            },
          ),
          const SizedBox(height: 20),

          // Net Balances Breakdown
          Text(
            'NET BALANCES',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          NeobrutalCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Column(
              children: appState.balanceRows.map((b) {
                final netNum = double.tryParse(b.net) ?? 0.0;
                final isPositive = netNum > 0;
                final isZero = netNum == 0;

                Color badgeBg = isZero
                    ? AppColors.infoFill
                    : isPositive
                        ? AppColors.creditFill
                        : AppColors.debitFill;

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 14,
                        backgroundColor: b.isMe ? AppColors.action : Colors.grey.shade300,
                        child: Text(
                          b.user.initials,
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Colors.black),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        b.isMe ? '${b.user.name} (You)' : b.user.name,
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                      ),
                      const Spacer(),
                      NeobrutalBadge(
                        label: isZero ? 'Settled' : (isPositive ? '+₹${b.net}' : '-₹${b.net.replaceAll('-', '')}'),
                        backgroundColor: badgeBg,
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 24),

          // Confirmed Settlements History
          Text(
            'CONFIRMED HISTORY',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          if (appState.settlementHistory.isEmpty)
            NeobrutalCard(
              child: Text(
                'No settled payments yet.',
                style: TextStyle(
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          else
            ...appState.settlementHistory.map((h) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: NeobrutalCard(
                  padding: const EdgeInsets.all(12.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${h.fromUser?.name} → ${h.toUser?.name}',
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                          ),
                          Text(
                            '${h.date} · via ${h.method}',
                            style: TextStyle(fontSize: 11, color: isDark ? AppColors.darkMuted : AppColors.muted),
                          ),
                        ],
                      ),
                      MoneyText(amount: h.amount, fontSize: 15, fontWeight: FontWeight.w900),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildPendingTab(AppState appState, bool isDark) {
    return RefreshIndicator(
      onRefresh: () => appState.fetchSettlements(),
      color: Colors.black,
      backgroundColor: AppColors.action,
      child: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          Text(
            'PAYMENTS AWAITING YOUR CONFIRMATION',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          if (appState.awaitingConfirmation.isEmpty)
            NeobrutalCard(
              child: Text(
                'No pending payments awaiting your approval.',
                style: TextStyle(
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          else
            ...appState.awaitingConfirmation.map((item) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 12.0),
                child: NeobrutalCard(
                  padding: const EdgeInsets.all(16.0),
                  backgroundColor: AppColors.creditFill.withValues(alpha: 0.15),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '${item.fromUser?.name} sent you',
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15),
                          ),
                          MoneyText(
                            amount: item.amount,
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                            color: isDark ? AppColors.darkCreditText : AppColors.creditText,
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Method: ${item.method} · Date: ${item.date}',
                        style: TextStyle(fontSize: 12, color: isDark ? AppColors.darkMuted : AppColors.muted),
                      ),
                      if (item.note.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text('Note: "${item.note}"', style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
                      ],
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: NeobrutalButton(
                              text: 'CONFIRM',
                              height: 40,
                              backgroundColor: AppColors.creditFill,
                              onPressed: () => _confirmPayment(item.id),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: NeobrutalButton(
                              text: 'REJECT',
                              height: 40,
                              backgroundColor: AppColors.debitFill,
                              onPressed: () => _rejectPayment(item.id),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),

          const SizedBox(height: 24),
          Text(
            'PAYMENTS YOU SENT (WAITING FOR OTHERS)',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          if (appState.myPendingSent.isEmpty)
            NeobrutalCard(
              child: Text(
                'None.',
                style: TextStyle(
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          else
            ...appState.myPendingSent.map((s) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: NeobrutalCard(
                  padding: const EdgeInsets.all(12.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('To: ${s.toUser?.name}', style: const TextStyle(fontWeight: FontWeight.w800)),
                          Text('${s.date} · via ${s.method}', style: TextStyle(fontSize: 11, color: isDark ? AppColors.darkMuted : AppColors.muted)),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          MoneyText(amount: s.amount, fontSize: 15, fontWeight: FontWeight.w900),
                          const SizedBox(height: 2),
                          const NeobrutalBadge(label: 'PENDING', backgroundColor: AppColors.infoFill),
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
