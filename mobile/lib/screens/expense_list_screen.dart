import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/category.dart';
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
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Scaffold(
      body: Column(
        children: [
          // 1. Top Section Header with Title & Add button
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurface : AppColors.surface,
              border: Border(
                bottom: BorderSide(
                  color: inkColor,
                  width: AppColors.borderWidth,
                ),
              ),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Text(
                      'EXPENSES',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                        color: inkColor,
                      ),
                    ),
                    const Spacer(),
                    GestureDetector(
                      onTap: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => const ExpenseFormScreen()),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
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
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.add, size: 16, color: Colors.black),
                            SizedBox(width: 4),
                            Text(
                              'ADD',
                              style: TextStyle(
                                fontWeight: FontWeight.w900,
                                fontSize: 12,
                                color: Colors.black,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                // Search row
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: 40,
                        decoration: BoxDecoration(
                          color: isDark ? AppColors.darkPaper : AppColors.paper,
                          border: Border.all(
                            color: inkColor,
                            width: AppColors.thinBorderWidth,
                          ),
                        ),
                        child: TextField(
                          controller: _searchController,
                          onSubmitted: (_) => _applyFilter(),
                          decoration: const InputDecoration(
                            hintText: 'Search expenses...',
                            hintStyle: TextStyle(fontSize: 13),
                            prefixIcon: Icon(Icons.search, size: 18),
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
                        height: 40,
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        decoration: BoxDecoration(
                          color: AppColors.action,
                          border: Border.all(
                            color: inkColor,
                            width: AppColors.thinBorderWidth,
                          ),
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
                            'FILTER',
                            style: TextStyle(fontWeight: FontWeight.w900, color: Colors.black, fontSize: 12),
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

          // 2. Expenses List in Single Card Flat (matching Web App)
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
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                children: [
                  if (appState.expenses.isEmpty)
                    NeobrutalCard(
                      padding: const EdgeInsets.all(20.0),
                      child: Center(
                        child: Text(
                          'Nothing here.\nTry a different filter or add an expense.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: isDark ? AppColors.darkMuted : AppColors.muted,
                          ),
                        ),
                      ),
                    )
                  else
                    NeobrutalCard(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                      child: Column(
                        children: appState.expenses.asMap().entries.map((entry) {
                          final idx = entry.key;
                          final exp = entry.value;
                          final isLast = idx == appState.expenses.length - 1;

                          return NeobrutalLedgerRow(
                            leading: CategoryDot(color: exp.category.color, size: 14),
                            title: exp.description,
                            subtitle: '${exp.date} · ${exp.category.name} · ${exp.paidBy.name} paid',
                            amount: exp.isDraft ? '—' : exp.amount,
                            subamount: exp.myShare != null && exp.myShare != exp.amount
                                ? 'Your share ₹${exp.myShare}'
                                : null,
                            showBottomBorder: !isLast,
                            trailing: exp.isDraft
                                ? const Padding(
                                    padding: EdgeInsets.only(left: 6.0),
                                    child: NeobrutalBadge(
                                      label: 'needs amount',
                                      backgroundColor: AppColors.action,
                                      textColor: Colors.black,
                                    ),
                                  )
                                : null,
                            onTap: () {
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => ExpenseDetailScreen(expenseId: exp.id),
                                ),
                              );
                            },
                          );
                        }).toList(),
                      ),
                    ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        ],
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
            border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: inkColor,
                      offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
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
}
