import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'away_days_screen.dart';
import 'balances_screen.dart';
import 'expense_detail_screen.dart';
import 'expense_list_screen.dart';
import 'members_screen.dart';
import 'record_payment_screen.dart';
import 'settle_screen.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    Color heroBg;
    String heroStatus;
    if (appState.isOwed) {
      heroBg = AppColors.creditFill;
      heroStatus = 'YOU ARE OWED';
    } else if (appState.owes) {
      heroBg = AppColors.debitFill;
      heroStatus = 'YOU OWE';
    } else {
      heroBg = isDark ? AppColors.darkSurface : AppColors.surface;
      heroStatus = 'YOU ARE SETTLED UP';
    }

    final String monthName = _getCurrentMonthName();

    return RefreshIndicator(
      onRefresh: () => appState.refreshAll(),
      color: Colors.black,
      backgroundColor: AppColors.action,
      child: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 16.0),
        children: [
          // 1. Balance Hero Card matching .balance-hero
          NeobrutalCard(
            backgroundColor: heroBg,
            shadowOffset: AppColors.largeShadowOffset,
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 22.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  heroStatus,
                  style: const TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 12,
                    letterSpacing: 1.2,
                    color: Color(0xFF0A0A0A),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '₹${appState.myBalanceMagnitude}',
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w900,
                    fontSize: 40,
                    letterSpacing: -1.0,
                    color: Color(0xFF0A0A0A),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  appState.isSettled
                      ? 'Nothing owed either way.'
                      : 'Paid ₹${appState.myPaid} · your share ₹${appState.myOwed}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF0A0A0A),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // 2. Waiting for you to confirm (if any pending settlements)
          if (appState.awaitingConfirmation.isNotEmpty) ...[
            NeobrutalCard(
              backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'WAITING FOR YOU TO CONFIRM',
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 11,
                      letterSpacing: 1.0,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                    ),
                  ),
                  const SizedBox(height: 10),
                  ...appState.awaitingConfirmation.map((s) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8.0),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${s.fromUser?.name ?? 'Flatmate'} says they sent you',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: isDark ? AppColors.darkInk : AppColors.ink,
                              ),
                            ),
                          ),
                          MoneyText(
                            amount: s.amount,
                            fontSize: 14,
                            fontWeight: FontWeight.w900,
                          ),
                        ],
                      ),
                    );
                  }),
                  const SizedBox(height: 8),
                  NeobrutalButton(
                    text: 'Review ${appState.awaitingConfirmation.length} payment${appState.awaitingConfirmation.length == 1 ? '' : 's'}',
                    backgroundColor: AppColors.action,
                    textColor: Colors.black,
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const SettleScreen()),
                      );
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // 3. Needs an amount (Drafts)
          if (appState.drafts.isNotEmpty) ...[
            NeobrutalCard(
              backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'NEEDS AN AMOUNT',
                    style: TextStyle(
                      fontWeight: FontWeight.w900,
                      fontSize: 11,
                      letterSpacing: 1.0,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                    ),
                  ),
                  const SizedBox(height: 10),
                  ...appState.drafts.map((d) {
                    return NeobrutalLedgerRow(
                      title: d['description'] ?? 'Draft Expense',
                      subtitle: '${d['date'] ?? ''} · ${d['category_name'] ?? ''}',
                      trailing: GestureDetector(
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => ExpenseDetailScreen(expenseId: d['id']),
                            ),
                          );
                        },
                        child: const NeobrutalBadge(
                          label: 'Fill in',
                          backgroundColor: AppColors.action,
                          textColor: Colors.black,
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // 4. Who Pays Whom Section
          _sectionTitle('WHO PAYS WHOM', isDark),
          NeobrutalCard(
            child: appState.transfers.isEmpty
                ? Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12.0),
                    child: Center(
                      child: Text(
                        'Everyone is square.\nNo payments needed.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: isDark ? AppColors.darkMuted : AppColors.muted,
                        ),
                      ),
                    ),
                  )
                : Column(
                    children: appState.transfers.asMap().entries.map((entry) {
                      final idx = entry.key;
                      final t = entry.value;
                      final isMePayer = t.iPay;
                      final isMeReceiver = t.involvesMe && !t.iPay;
                      final isLast = idx == appState.transfers.length - 1;

                      return NeobrutalLedgerRow(
                        title: '${t.fromUser.name} → ${t.toUser.name}',
                        subtitle: isMePayer
                            ? 'You pay this one'
                            : (isMeReceiver ? 'Owed to you' : null),
                        amount: t.amount,
                        amountColor: isMePayer
                            ? (isDark ? AppColors.darkDebitText : AppColors.debitText)
                            : (isMeReceiver
                                ? (isDark ? AppColors.darkCreditText : AppColors.creditText)
                                : null),
                        showBottomBorder: !isLast,
                        trailing: isMePayer
                            ? GestureDetector(
                                onTap: () {
                                  Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (_) => RecordPaymentScreen(
                                        preselectedRecipient: t.toUser,
                                        prefilledAmount: t.amount,
                                      ),
                                    ),
                                  );
                                },
                                child: const NeobrutalBadge(
                                  label: 'PAY',
                                  backgroundColor: AppColors.action,
                                  textColor: Colors.black,
                                ),
                              )
                            : null,
                      );
                    }).toList(),
                  ),
          ),
          const SizedBox(height: 20),

          // 5. Month So Far Section
          _sectionTitle('$monthName SO FAR', isDark),
          NeobrutalCard(
            child: Column(
              children: [
                NeobrutalLedgerRow(
                  title: 'Flat total',
                  amount: appState.monthTotal,
                  showBottomBorder: true,
                ),
                NeobrutalLedgerRow(
                  title: 'Your share',
                  amount: appState.myMonthShare,
                  showBottomBorder: false,
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 6. Recent Section with "See all"
          Row(
            children: [
              _sectionTitle('RECENT', isDark, marginBottom: 0),
              const Spacer(),
              GestureDetector(
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const ExpenseListScreen()),
                  );
                },
                child: Text(
                  'See all',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    decoration: TextDecoration.underline,
                    color: isDark ? AppColors.darkInk : AppColors.ink,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          NeobrutalCard(
            child: appState.expenses.isEmpty
                ? Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12.0),
                    child: Center(
                      child: Text(
                        'No expenses recorded this month.',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: isDark ? AppColors.darkMuted : AppColors.muted,
                        ),
                      ),
                    ),
                  )
                : Column(
                    children: appState.expenses.take(5).toList().asMap().entries.map((entry) {
                      final idx = entry.key;
                      final e = entry.value;
                      final isLast = idx == (appState.expenses.length > 5 ? 4 : appState.expenses.length - 1);

                      return NeobrutalLedgerRow(
                        leading: CategoryDot(color: e.category.color),
                        title: e.description,
                        subtitle: '${e.date} · ${e.paidBy.name} paid',
                        amount: e.isDraft ? '—' : e.amount,
                        showBottomBorder: !isLast,
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => ExpenseDetailScreen(expenseId: e.id),
                            ),
                          );
                        },
                      );
                    }).toList(),
                  ),
          ),
          const SizedBox(height: 20),

          // 7. Web Navigation Links matching web dashboard footer
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _webQuickLink(context, 'Balances', isDark, onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const BalancesScreen()),
                );
              }),
              _webQuickLink(context, 'Away days', isDark, onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const AwayDaysScreen()),
                );
              }),
              _webQuickLink(context, 'Flatmates', isDark, onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const MembersScreen()),
                );
              }),
            ],
          ),
          const SizedBox(height: 28),
        ],
      ),
    );
  }

  Widget _webQuickLink(BuildContext context, String label, bool isDark, {required VoidCallback onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isDark ? AppColors.darkSurface : AppColors.surface,
          border: Border.all(
            color: isDark ? AppColors.darkInk : AppColors.ink,
            width: AppColors.thinBorderWidth,
          ),
          boxShadow: [
            BoxShadow(
              color: isDark ? AppColors.darkInk : AppColors.ink,
              offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
              blurRadius: 0,
            ),
          ],
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w800,
            color: isDark ? AppColors.darkInk : AppColors.ink,
          ),
        ),
      ),
    );
  }

  Widget _sectionTitle(String title, bool isDark, {double marginBottom = 8}) {
    return Padding(
      padding: EdgeInsets.only(bottom: marginBottom),
      child: Text(
        title.toUpperCase(),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w900,
          letterSpacing: 1.0,
          color: isDark ? AppColors.darkInk : AppColors.ink,
        ),
      ),
    );
  }

  String _getCurrentMonthName() {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return months[DateTime.now().month - 1];
  }
}
