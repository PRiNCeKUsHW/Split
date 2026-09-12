import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/expense.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class ExpenseDetailScreen extends StatefulWidget {
  final int expenseId;

  const ExpenseDetailScreen({super.key, required this.expenseId});

  @override
  State<ExpenseDetailScreen> createState() => _ExpenseDetailScreenState();
}

class _ExpenseDetailScreenState extends State<ExpenseDetailScreen> {
  Expense? _expense;
  bool _isLoading = true;
  final TextEditingController _commentController = TextEditingController();
  final TextEditingController _draftAmountController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  @override
  void dispose() {
    _commentController.dispose();
    _draftAmountController.dispose();
    super.dispose();
  }

  void _loadDetail() async {
    setState(() => _isLoading = true);
    final appState = Provider.of<AppState>(context, listen: false);
    final exp = await appState.getExpenseDetail(widget.expenseId);
    setState(() {
      _expense = exp;
      _isLoading = false;
    });
  }

  void _postComment() async {
    final text = _commentController.text.trim();
    if (text.isEmpty) return;

    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.addComment(widget.expenseId, text);
    if (ok) {
      _commentController.clear();
      _loadDetail();
    }
  }

  void _fillDraft() async {
    final amount = _draftAmountController.text.trim();
    if (amount.isEmpty) return;

    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.fillDraftAmount(widget.expenseId, amount);
    if (ok && mounted) {
      Navigator.of(context).pop();
      _loadDetail();
    }
  }

  void _confirmDelete() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
        title: const Text('DELETE EXPENSE', style: TextStyle(fontWeight: FontWeight.w900)),
        content: const Text('Are you sure you want to remove this expense?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('CANCEL'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('DELETE', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      final appState = Provider.of<AppState>(context, listen: false);
      final ok = await appState.deleteExpense(widget.expenseId);
      if (ok && mounted) {
        Navigator.of(context).pop();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('EXPENSE DETAILS')),
        body: const Center(child: CircularProgressIndicator(color: Colors.black)),
      );
    }

    if (_expense == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('EXPENSE DETAILS')),
        body: const Center(child: Text('Expense not found.')),
      );
    }

    final exp = _expense!;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'EXPENSE DETAILS',
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
        ),
        elevation: 0,
        actions: [
          if (!exp.isMonthClosed)
            IconButton(
              icon: const Icon(Icons.delete_outline, color: Colors.red),
              onPressed: _confirmDelete,
            ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: Container(color: inkColor, height: 3),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // 1. Main Header Card
          NeobrutalCard(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    NeobrutalBadge(
                      label: exp.category.name.toUpperCase(),
                      backgroundColor: exp.category.color,
                      textColor: Colors.white,
                    ),
                    NeobrutalBadge(
                      label: exp.splitTypeLabel ?? exp.splitType,
                      backgroundColor: AppColors.action,
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  exp.description,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 10),
                if (exp.amount != null)
                  MoneyText(
                    amount: exp.amount!,
                    fontSize: 32,
                    fontWeight: FontWeight.w900,
                  )
                else
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const NeobrutalBadge(
                        label: 'VARIABLE DRAFT: NO AMOUNT ENTERED',
                        backgroundColor: AppColors.infoFill,
                      ),
                      const SizedBox(height: 10),
                      NeobrutalButton(
                        text: 'FILL AMOUNT IN',
                        backgroundColor: AppColors.action,
                        onPressed: () {
                          showDialog(
                            context: context,
                            builder: (ctx) => AlertDialog(
                              shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
                              title: const Text('ENTER AMOUNT', style: TextStyle(fontWeight: FontWeight.w900)),
                              content: TextField(
                                controller: _draftAmountController,
                                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                decoration: const InputDecoration(hintText: 'e.g. 1250.00'),
                              ),
                              actions: [
                                TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('CANCEL')),
                                TextButton(onPressed: _fillDraft, child: const Text('SAVE', style: TextStyle(fontWeight: FontWeight.bold))),
                              ],
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                const SizedBox(height: 12),
                const Divider(thickness: 2),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.person, size: 16),
                    const SizedBox(width: 6),
                    Text(
                      'Paid by ${exp.paidBy.name}',
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                    ),
                    const Spacer(),
                    const Icon(Icons.calendar_today, size: 14),
                    const SizedBox(width: 6),
                    Text(
                      exp.date,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                    ),
                  ],
                ),
                if (exp.periodStart != null && exp.periodEnd != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Period: ${exp.periodStart} to ${exp.periodEnd} (${exp.periodDays} days)',
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 2. Shares Breakdown
          Text(
            'SPLIT BREAKDOWN',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          NeobrutalCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Column(
              children: exp.shares.map((share) {
                final user = share.user;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8.0),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 14,
                        backgroundColor: AppColors.action,
                        child: Text(
                          user?.initials ?? '?',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w900,
                            color: Colors.black,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user?.name ?? 'Flatmate',
                              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                            ),
                            if (share.basis.isNotEmpty)
                              Text(
                                share.basis,
                                style: TextStyle(
                                  fontSize: 11,
                                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                                ),
                              ),
                          ],
                        ),
                      ),
                      MoneyText(
                        amount: share.amountOwed,
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 20),

          // 3. Comments Thread
          Text(
            'COMMENTS (${exp.comments.length})',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.8,
              color: isDark ? AppColors.darkMuted : AppColors.muted,
            ),
          ),
          const SizedBox(height: 10),
          if (exp.comments.isEmpty)
            NeobrutalCard(
              child: Text(
                'No comments yet.',
                style: TextStyle(
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            )
          else
            ...exp.comments.map((c) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: NeobrutalCard(
                  padding: const EdgeInsets.all(12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            c.author.name,
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                          ),
                          Text(
                            c.createdAt.split('T')[0],
                            style: TextStyle(
                              fontSize: 11,
                              color: isDark ? AppColors.darkMuted : AppColors.muted,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(c.body, style: const TextStyle(fontSize: 13)),
                    ],
                  ),
                ),
              );
            }),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: NeobrutalTextField(
                  controller: _commentController,
                  label: '',
                  hint: 'Write a comment...',
                ),
              ),
              const SizedBox(width: 8),
              Padding(
                padding: const EdgeInsets.only(bottom: 16.0),
                child: GestureDetector(
                  onTap: _postComment,
                  child: Container(
                    height: 50,
                    width: 50,
                    decoration: BoxDecoration(
                      color: AppColors.action,
                      border: Border.all(color: inkColor, width: AppColors.borderWidth),
                      boxShadow: [
                        BoxShadow(
                          color: inkColor,
                          offset: const Offset(3, 3),
                          blurRadius: 0,
                        ),
                      ],
                    ),
                    child: const Icon(Icons.send, color: Colors.black, size: 20),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
