import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/category.dart';
import '../models/expense.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';
import 'expense_detail_screen.dart';
import 'expense_form_screen.dart';

class ExpenseListScreen extends StatefulWidget {
  const ExpenseListScreen({super.key});

  @override
  State<ExpenseListScreen> createState() => _ExpenseListScreenState();
}

class _ExpenseListScreenState extends State<ExpenseListScreen> {
  final TextEditingController _searchController = TextEditingController();
  Category? _selectedCategory;
  int? _selectedYear;
  int? _selectedMonth;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _applyFilter() {
    final appState = Provider.of<AppState>(context, listen: false);
    appState.fetchExpenses(
      year: _selectedYear,
      month: _selectedMonth,
      categoryId: _selectedCategory?.id,
      query: _searchController.text.trim(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: Column(
        children: [
          // 1. Search & Filter Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurface : AppColors.surface,
              border: Border(
                bottom: BorderSide(
                  color: isDark ? AppColors.darkInk : AppColors.ink,
                  width: AppColors.borderWidth,
                ),
              ),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: 44,
                        decoration: BoxDecoration(
                          color: isDark ? AppColors.darkPaper : AppColors.paper,
                          border: Border.all(
                            color: isDark ? AppColors.darkInk : AppColors.ink,
                            width: 2.5,
                          ),
                        ),
                        child: TextField(
                          controller: _searchController,
                          onSubmitted: (_) => _applyFilter(),
                          decoration: const InputDecoration(
                            hintText: 'Search expenses...',
                            hintStyle: TextStyle(fontSize: 14),
                            prefixIcon: Icon(Icons.search, size: 20),
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(vertical: 10),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: _applyFilter,
                      child: Container(
                        height: 44,
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        decoration: BoxDecoration(
                          color: AppColors.action,
                          border: Border.all(
                            color: isDark ? AppColors.darkInk : AppColors.ink,
                            width: 2.5,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: isDark ? AppColors.darkInk : AppColors.ink,
                              offset: const Offset(2, 2),
                              blurRadius: 0,
                            ),
                          ],
                        ),
                        child: const Center(
                          child: Text(
                            'FILTER',
                            style: TextStyle(fontWeight: FontWeight.w900, color: Colors.black),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                // Category Pills
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _filterChip('All', _selectedCategory == null, () {
                        setState(() => _selectedCategory = null);
                        _applyFilter();
                      }),
                      ...appState.categories.map((cat) {
                        final isSelected = _selectedCategory?.id == cat.id;
                        return _filterChip(cat.name, isSelected, () {
                          setState(() => _selectedCategory = cat);
                          _applyFilter();
                        }, color: cat.color);
                      }),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // 2. Expenses List
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => appState.fetchExpenses(
                year: _selectedYear,
                month: _selectedMonth,
                categoryId: _selectedCategory?.id,
                query: _searchController.text.trim(),
              ),
              color: Colors.black,
              backgroundColor: AppColors.action,
              child: appState.expenses.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: NeobrutalCard(
                          child: Text(
                            'No expenses found.',
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              color: isDark ? AppColors.darkMuted : AppColors.muted,
                            ),
                          ),
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      itemCount: appState.expenses.length,
                      itemBuilder: (context, index) {
                        final exp = appState.expenses[index];
                        return _expenseRow(exp, isDark);
                      },
                    ),
            ),
          ),
        ],
      ),
      floatingActionButton: GestureDetector(
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const ExpenseFormScreen()),
          );
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          decoration: BoxDecoration(
            color: AppColors.action,
            border: Border.all(
              color: isDark ? AppColors.darkInk : AppColors.ink,
              width: AppColors.borderWidth,
            ),
            boxShadow: [
              BoxShadow(
                color: isDark ? AppColors.darkInk : AppColors.ink,
                offset: const Offset(4, 4),
                blurRadius: 0,
              ),
            ],
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.add, color: Colors.black, size: 22),
              SizedBox(width: 8),
              Text(
                'ADD EXPENSE',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 14,
                  letterSpacing: 0.5,
                  color: Colors.black,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _filterChip(String label, bool isSelected, VoidCallback onTap, {Color? color}) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Padding(
      padding: const EdgeInsets.only(right: 8.0),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: isSelected
                ? (color ?? AppColors.action)
                : (isDark ? AppColors.darkSurface : AppColors.surface),
            border: Border.all(color: inkColor, width: 2.0),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: inkColor,
                      offset: const Offset(2, 2),
                      blurRadius: 0,
                    ),
                  ]
                : null,
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
              color: isSelected ? Colors.black : (isDark ? AppColors.darkInk : AppColors.ink),
            ),
          ),
        ),
      ),
    );
  }

  Widget _expenseRow(Expense exp, bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10.0),
      child: NeobrutalCard(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => ExpenseDetailScreen(expenseId: exp.id),
            ),
          );
        },
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            CategoryDot(color: exp.category.color, size: 16),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    exp.description,
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                      color: isDark ? AppColors.darkInk : AppColors.ink,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Text(
                        '${exp.date} · ${exp.paidBy.name} paid',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: isDark ? AppColors.darkMuted : AppColors.muted,
                        ),
                      ),
                      if (exp.isDraft) ...[
                        const SizedBox(width: 6),
                        const NeobrutalBadge(
                          label: 'needs amount',
                          backgroundColor: AppColors.action,
                          textColor: Colors.black,
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const SizedBox(
              width: 28,
              child: DottedLeaderLine(),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (exp.amount != null)
                  MoneyText(
                    amount: exp.amount!,
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                  )
                else
                  const Text('—', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                if (exp.myShare != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Your share ₹${exp.myShare}',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: isDark ? AppColors.darkMuted : AppColors.muted,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
