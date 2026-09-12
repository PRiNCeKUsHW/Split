import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/expense.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'expense_form_screen.dart';

class ExpenseDetailScreen extends StatefulWidget {
  final int expenseId;

  const ExpenseDetailScreen({super.key, required this.expenseId});

  @override
  State<ExpenseDetailScreen> createState() => _ExpenseDetailScreenState();
}

class _ExpenseDetailScreenState extends State<ExpenseDetailScreen> {
  Expense? _expense;
  bool _isLoading = true;
  bool _isPostingComment = false;
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
    if (mounted) {
      setState(() {
        _expense = exp;
        _isLoading = false;
      });
    }
  }

  void _postComment() async {
    final text = _commentController.text.trim();
    if (text.isEmpty || _isPostingComment) return;

    setState(() => _isPostingComment = true);
    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.addComment(widget.expenseId, text);
    if (mounted) {
      setState(() => _isPostingComment = false);
      if (ok) {
        _commentController.clear();
        _loadDetail();
      }
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
          'DELETE EXPENSE',
          style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: inkColor),
        ),
        content: Text(
          'Delete this expense? It stays in the history.',
          style: TextStyle(color: inkColor, fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(
              'CANCEL',
              style: TextStyle(fontWeight: FontWeight.w800, color: inkColor),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text(
              'DELETE',
              style: TextStyle(color: Colors.red, fontWeight: FontWeight.w900),
            ),
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
        title: Text(
          exp.description.toUpperCase(),
          style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5, fontSize: 16),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
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
          // 1. Main Header Card (card-flat)
          NeobrutalCard(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Eyebrow
                Text(
                  exp.category.name.toUpperCase(),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                    color: isDark ? AppColors.darkMuted : AppColors.muted,
                  ),
                ),
                const SizedBox(height: 6),
                // Title
                Text(
                  exp.description,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: inkColor,
                  ),
                ),
                const SizedBox(height: 10),
                // Money hero
                if (exp.amount != null)
                  Text(
                    '₹${exp.amount}',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 34,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -1.0,
                      color: inkColor,
                    ),
                  )
                else
                  Text(
                    '—',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 34,
                      fontWeight: FontWeight.w700,
                      color: inkColor,
                    ),
                  ),
                const SizedBox(height: 10),
                // Paid by & date
                Text(
                  '${exp.paidBy.name} paid · ${exp.date}',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: isDark ? AppColors.darkMuted : AppColors.muted,
                  ),
                ),
                if (exp.periodDays != null && exp.periodDays! > 1) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Covers ${exp.periodStart ?? ''} – ${exp.periodEnd ?? ''} (${exp.periodDays} days)',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                    ),
                  ),
                ],
                // Calculation Notes (as seen on web)
                if (exp.notes != null && exp.notes!.trim().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10.0),
                    decoration: BoxDecoration(
                      color: isDark ? AppColors.darkPaper : AppColors.paper,
                      border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                    ),
                    child: Text(
                      exp.notes!,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: inkColor,
                        height: 1.45,
                      ),
                    ),
                  ),
                ],
                // Draft amount prompt
                if (exp.isDraft) ...[
                  const SizedBox(height: 14),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.action.withValues(alpha: 0.2),
                      border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Variable Draft: No amount entered',
                          style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Colors.black),
                        ),
                        const SizedBox(height: 10),
                        GestureDetector(
                          onTap: () {
                            showDialog(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
                                shape: RoundedRectangleBorder(
                                  side: BorderSide(color: inkColor, width: AppColors.borderWidth),
                                  borderRadius: BorderRadius.zero,
                                ),
                                title: Text(
                                  'ENTER AMOUNT',
                                  style: TextStyle(fontWeight: FontWeight.w900, color: inkColor),
                                ),
                                content: TextField(
                                  controller: _draftAmountController,
                                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                  decoration: InputDecoration(
                                    hintText: 'e.g. 1250.00',
                                    border: OutlineInputBorder(
                                      borderSide: BorderSide(color: inkColor, width: 2),
                                      borderRadius: BorderRadius.zero,
                                    ),
                                  ),
                                ),
                                actions: [
                                  TextButton(
                                    onPressed: () => Navigator.of(ctx).pop(),
                                    child: Text('CANCEL', style: TextStyle(color: inkColor)),
                                  ),
                                  TextButton(
                                    onPressed: _fillDraft,
                                    child: const Text('SAVE', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.black)),
                                  ),
                                ],
                              ),
                            );
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                            decoration: BoxDecoration(
                              color: AppColors.action,
                              border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                              boxShadow: [
                                BoxShadow(
                                  color: inkColor,
                                  offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
                                  blurRadius: 0,
                                ),
                              ],
                            ),
                            child: const Text(
                              'FILL AMOUNT IN',
                              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: Colors.black),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

          if (exp.isMonthClosed) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.shade100,
                border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
              ),
              child: Text(
                '${exp.date} is closed, so this expense is read-only.',
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Colors.black),
              ),
            ),
          ],

          const SizedBox(height: 20),

          // 2. The Split Section
          if (exp.shares.isNotEmpty) ...[
            Text(
              'THE SPLIT',
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
              child: Column(
                children: [
                  ...exp.shares.map((share) {
                    final user = share.user;
                    final initials = user?.initials ?? (share.userName != null && share.userName!.isNotEmpty ? share.userName![0] : '?');
                    final name = user?.name ?? share.userName ?? 'Flatmate';

                    return Container(
                      padding: const EdgeInsets.symmetric(vertical: 10.0),
                      decoration: BoxDecoration(
                        border: Border(
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
                          Flexible(
                            fit: FlexFit.loose,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  name,
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    fontSize: 14,
                                    color: inkColor,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                if (share.basis.isNotEmpty) ...[
                                  const SizedBox(height: 2),
                                  Text(
                                    share.basis,
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Expanded(
                            child: DottedLeaderLine(),
                          ),
                          const SizedBox(width: 8),
                          MoneyText(
                            amount: share.amountOwed,
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                            color: inkColor,
                          ),
                        ],
                      ),
                    );
                  }),
                  // Total Row
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 10.0),
                    child: Row(
                      children: [
                        Text(
                          'Total',
                          style: TextStyle(
                            fontWeight: FontWeight.w900,
                            fontSize: 14,
                            color: inkColor,
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Expanded(
                          child: DottedLeaderLine(),
                        ),
                        const SizedBox(width: 8),
                        MoneyText(
                          amount: exp.amount ?? '0.00',
                          fontSize: 15,
                          fontWeight: FontWeight.w900,
                          color: inkColor,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],

          // 3. Comments Section
          Text(
            'COMMENTS',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.0,
              color: inkColor,
            ),
          ),
          const SizedBox(height: 8),
          NeobrutalCard(
            padding: const EdgeInsets.all(14.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Comments list
                if (exp.comments.isNotEmpty) ...[
                  ...exp.comments.asMap().entries.map((entry) {
                    final idx = entry.key;
                    final c = entry.value;
                    final isLast = idx == exp.comments.length - 1;

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
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              AvatarChipWidget(
                                initials: c.author.initials,
                                size: 26,
                                hasShadow: false,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                c.author.name,
                                style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 13,
                                  color: inkColor,
                                ),
                              ),
                              const Spacer(),
                              Text(
                                c.createdAt.split('T')[0],
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            c.body,
                            style: TextStyle(
                              fontSize: 13,
                              color: inkColor,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                  const SizedBox(height: 14),
                  Divider(color: inkColor, thickness: AppColors.thinBorderWidth),
                  const SizedBox(height: 10),
                ],

                // Comment input form
                Container(
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkPaper : AppColors.paper,
                    border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                  ),
                  child: TextField(
                    controller: _commentController,
                    maxLines: 3,
                    minLines: 2,
                    style: TextStyle(fontSize: 13, color: inkColor),
                    decoration: InputDecoration(
                      hintText: 'Write a comment...',
                      hintStyle: TextStyle(
                        fontSize: 13,
                        color: isDark ? AppColors.darkMuted : AppColors.muted,
                      ),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.all(10),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                GestureDetector(
                  onTap: _isPostingComment ? null : _postComment,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: isDark ? AppColors.darkPaper : Colors.white,
                      border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                      boxShadow: [
                        BoxShadow(
                          color: inkColor,
                          offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
                          blurRadius: 0,
                        ),
                      ],
                    ),
                    child: _isPostingComment
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                          )
                        : Text(
                            'Post comment',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 12,
                              color: inkColor,
                            ),
                          ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // 4. Action Buttons (Edit & Delete)
          if (!exp.isMonthClosed) ...[
            Row(
              children: [
                Expanded(
                  child: GestureDetector(
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ExpenseFormScreen(initialExpense: exp),
                        ),
                      );
                    },
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
                          'EDIT',
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
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: GestureDetector(
                    onTap: _confirmDelete,
                    child: Container(
                      height: 44,
                      decoration: BoxDecoration(
                        color: AppColors.debitFill,
                        border: Border.all(color: inkColor, width: AppColors.borderWidth),
                        boxShadow: [
                          BoxShadow(
                            color: inkColor,
                            offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
                            blurRadius: 0,
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Text(
                          'DELETE',
                          style: TextStyle(
                            fontWeight: FontWeight.w900,
                            fontSize: 13,
                            letterSpacing: 0.5,
                            color: Colors.black,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 32),
          ],
        ],
      ),
    );
  }
}

