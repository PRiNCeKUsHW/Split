import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/category.dart';
import '../models/expense.dart';
import '../models/user.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class ExpenseFormScreen extends StatefulWidget {
  final Expense? initialExpense;

  const ExpenseFormScreen({super.key, this.initialExpense});

  @override
  State<ExpenseFormScreen> createState() => _ExpenseFormScreenState();
}

class _ExpenseFormScreenState extends State<ExpenseFormScreen> {
  final _descController = TextEditingController();
  final _amountController = TextEditingController();
  final _notesController = TextEditingController();

  Category? _selectedCategory;
  User? _paidBy;
  DateTime _date = DateTime.now();

  bool _hasPeriod = false;
  DateTime _periodStart = DateTime.now();
  DateTime _periodEnd = DateTime.now();

  String _splitType = 'EQUAL';
  final Set<int> _selectedParticipants = {};
  final Map<int, TextEditingController> _customInputs = {};

  List<ExpenseShare> _previewShares = [];
  bool _isLoadingPreview = false;
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    final appState = Provider.of<AppState>(context, listen: false);
    if (appState.categories.isNotEmpty) {
      _selectedCategory = appState.categories.first;
    }
    if (appState.members.isNotEmpty) {
      _paidBy = appState.members.firstWhere(
        (m) => m.id == appState.currentUser?.id,
        orElse: () => appState.members.first,
      );
    } else {
      _paidBy = appState.currentUser;
    }
    for (var m in appState.members) {
      _selectedParticipants.add(m.id);
      _customInputs[m.id] = TextEditingController();
    }

    if (widget.initialExpense != null) {
      final exp = widget.initialExpense!;
      _descController.text = exp.description;
      if (exp.amount != null) _amountController.text = exp.amount!;
      if (exp.notes != null) _notesController.text = exp.notes!;
      _selectedCategory = exp.category;
      _paidBy = exp.paidBy;
      try {
        _date = DateTime.parse(exp.date);
      } catch (_) {}
      if (exp.periodStart != null && exp.periodEnd != null) {
        _hasPeriod = true;
        try {
          _periodStart = DateTime.parse(exp.periodStart!);
          _periodEnd = DateTime.parse(exp.periodEnd!);
        } catch (_) {}
      }
      _splitType = exp.splitType;
      _selectedParticipants.clear();
      for (var s in exp.shares) {
        final uid = s.userId ?? s.user?.id;
        if (uid != null) {
          _selectedParticipants.add(uid);
          if (s.basis.isNotEmpty) {
            _customInputs[uid]?.text = s.basis;
          }
        }
      }
    }

    _amountController.addListener(_updatePreview);
    _descController.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _descController.dispose();
    _amountController.dispose();
    _notesController.dispose();
    for (var c in _customInputs.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _updatePreview() async {
    final amountText = _amountController.text.trim();
    if (amountText.isEmpty || _selectedParticipants.isEmpty) {
      setState(() => _previewShares = []);
      return;
    }

    setState(() => _isLoadingPreview = true);
    final appState = Provider.of<AppState>(context, listen: false);

    final payload = <String, dynamic>{
      'amount': amountText,
      'split_type': _splitType,
      'paid_by': _paidBy?.id ?? appState.currentUser?.id,
      'category': _selectedCategory?.id,
      'participants': _selectedParticipants.toList(),
      'date': DateFormat('yyyy-MM-dd').format(_date),
    };

    if (_hasPeriod) {
      payload['period_start'] = DateFormat('yyyy-MM-dd').format(_periodStart);
      payload['period_end'] = DateFormat('yyyy-MM-dd').format(_periodEnd);
    }

    for (var uid in _selectedParticipants) {
      final val = _customInputs[uid]?.text.trim() ?? '';
      if (_splitType == 'EXACT') payload['exact_$uid'] = val;
      if (_splitType == 'PERCENT') payload['percent_$uid'] = val;
      if (_splitType == 'SHARES') payload['units_$uid'] = val;
    }

    final shares = await appState.previewSplit(payload);
    if (mounted) {
      setState(() {
        _previewShares = shares;
        _isLoadingPreview = false;
      });
    }
  }

  void _submit() async {
    final desc = _descController.text.trim();
    if (desc.isEmpty) {
      setState(() => _errorMessage = 'Please enter a description');
      return;
    }
    if (_selectedCategory == null) {
      setState(() => _errorMessage = 'Please choose a category');
      return;
    }
    if (_selectedParticipants.isEmpty) {
      setState(() => _errorMessage = 'Select at least one participant');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    final appState = Provider.of<AppState>(context, listen: false);
    final payload = <String, dynamic>{
      'description': desc,
      'amount': _amountController.text.trim().isEmpty ? null : _amountController.text.trim(),
      'category': _selectedCategory!.id,
      'paid_by': _paidBy?.id ?? appState.currentUser!.id,
      'date': DateFormat('yyyy-MM-dd').format(_date),
      'split_type': _splitType,
      'participants': _selectedParticipants.toList(),
      'notes': _notesController.text.trim(),
    };

    if (_hasPeriod) {
      payload['period_start'] = DateFormat('yyyy-MM-dd').format(_periodStart);
      payload['period_end'] = DateFormat('yyyy-MM-dd').format(_periodEnd);
    }

    for (var uid in _selectedParticipants) {
      final val = _customInputs[uid]?.text.trim() ?? '';
      if (_splitType == 'EXACT') payload['exact_$uid'] = val;
      if (_splitType == 'PERCENT') payload['percent_$uid'] = val;
      if (_splitType == 'SHARES') payload['units_$uid'] = val;
    }

    final ok = widget.initialExpense != null
        ? await appState.updateExpense(widget.initialExpense!.id, payload)
        : await appState.createExpense(payload);
    setState(() => _isSubmitting = false);

    if (ok && mounted) {
      Navigator.of(context).pop();
    } else if (mounted && appState.errorMessage != null) {
      setState(() => _errorMessage = appState.errorMessage);
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.initialExpense != null ? 'EDIT EXPENSE' : 'ADD EXPENSE',
          style: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
        ),
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: Container(color: inkColor, height: 3),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_errorMessage != null) ...[
              NeobrutalCard(
                backgroundColor: AppColors.debitFill,
                child: Text(
                  _errorMessage!,
                  style: const TextStyle(fontWeight: FontWeight.w700, color: Colors.black),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // 1. Amount & Description
            NeobrutalTextField(
              controller: _amountController,
              label: 'Amount (₹) — Leave blank for variable draft',
              hint: '0.00',
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
            NeobrutalTextField(
              controller: _descController,
              label: 'Description',
              hint: 'What was this for? (e.g. Groceries, WiFi)',
            ),

            // 2. Category Selector
            Text(
              'CATEGORY',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 12,
                letterSpacing: 0.8,
                color: isDark ? AppColors.darkInk : AppColors.ink,
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: appState.categories.map((cat) {
                final isSelected = _selectedCategory?.id == cat.id;
                return GestureDetector(
                  onTap: () {
                    setState(() => _selectedCategory = cat);
                    _updatePreview();
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: isSelected ? cat.color : (isDark ? AppColors.darkSurface : AppColors.surface),
                      border: Border.all(color: inkColor, width: 2.0),
                      boxShadow: isSelected
                          ? [BoxShadow(color: inkColor, offset: const Offset(2, 2))]
                          : null,
                    ),
                    child: Text(
                      cat.name,
                      style: TextStyle(
                        fontWeight: isSelected ? FontWeight.w900 : FontWeight.w600,
                        fontSize: 13,
                        color: isSelected ? Colors.white : (isDark ? AppColors.darkInk : AppColors.ink),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            if (_selectedCategory != null) ...[
              const SizedBox(height: 6),
              Text(
                'Rule: ${_selectedCategory!.behaviourLabel}',
                style: TextStyle(fontSize: 12, color: isDark ? AppColors.darkMuted : AppColors.muted),
              ),
            ],
            const SizedBox(height: 16),

            // 3. Paid By & Date
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'PAID BY',
                        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: isDark ? AppColors.darkInk : AppColors.ink),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          color: isDark ? AppColors.darkSurface : AppColors.surface,
                          border: Border.all(color: inkColor, width: AppColors.borderWidth),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<User>(
                            value: appState.members.contains(_paidBy)
                                ? _paidBy
                                : (appState.members.isNotEmpty ? appState.members.first : null),
                            isExpanded: true,
                            items: appState.members.map((u) {
                              return DropdownMenuItem(value: u, child: Text(u.name));
                            }).toList(),
                            onChanged: (u) {
                              setState(() => _paidBy = u);
                              _updatePreview();
                            },
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'DATE',
                        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: isDark ? AppColors.darkInk : AppColors.ink),
                      ),
                      const SizedBox(height: 6),
                      GestureDetector(
                        onTap: () async {
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: _date,
                            firstDate: DateTime(2020),
                            lastDate: DateTime(2030),
                          );
                          if (picked != null) {
                            setState(() => _date = picked);
                            _updatePreview();
                          }
                        },
                        child: Container(
                          height: 48,
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: BoxDecoration(
                            color: isDark ? AppColors.darkSurface : AppColors.surface,
                            border: Border.all(color: inkColor, width: AppColors.borderWidth),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(DateFormat('dd MMM yyyy').format(_date)),
                              const Icon(Icons.calendar_month, size: 18),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // 4. Multi-day period proration switch
            Row(
              children: [
                Checkbox(
                  value: _hasPeriod,
                  activeColor: AppColors.action,
                  checkColor: Colors.black,
                  onChanged: (val) {
                    setState(() => _hasPeriod = val ?? false);
                    _updatePreview();
                  },
                ),
                const Text(
                  'Covers multiple days (for away-day proration)',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                ),
              ],
            ),
            if (_hasPeriod) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('START DATE', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11)),
                        const SizedBox(height: 4),
                        GestureDetector(
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: _periodStart,
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2030),
                            );
                            if (picked != null) {
                              setState(() => _periodStart = picked);
                              _updatePreview();
                            }
                          },
                          child: Container(
                            height: 40,
                            padding: const EdgeInsets.symmetric(horizontal: 10),
                            decoration: BoxDecoration(
                              border: Border.all(color: inkColor, width: 2),
                            ),
                            alignment: Alignment.centerLeft,
                            child: Text(DateFormat('dd MMM').format(_periodStart)),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('END DATE', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11)),
                        const SizedBox(height: 4),
                        GestureDetector(
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: _periodEnd,
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2030),
                            );
                            if (picked != null) {
                              setState(() => _periodEnd = picked);
                              _updatePreview();
                            }
                          },
                          child: Container(
                            height: 40,
                            padding: const EdgeInsets.symmetric(horizontal: 10),
                            decoration: BoxDecoration(
                              border: Border.all(color: inkColor, width: 2),
                            ),
                            alignment: Alignment.centerLeft,
                            child: Text(DateFormat('dd MMM').format(_periodEnd)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],

            // 5. Split Type Selection
            Text(
              'SPLIT TYPE',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, letterSpacing: 0.8, color: isDark ? AppColors.darkInk : AppColors.ink),
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                _splitTab('EQUAL', 'Equally'),
                _splitTab('EXACT', 'Exact'),
                _splitTab('PERCENT', 'Percent'),
                _splitTab('SHARES', 'Shares'),
              ],
            ),
            const SizedBox(height: 16),

            // 6. Participants Selection
            Text(
              'PARTICIPANTS',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, letterSpacing: 0.8, color: isDark ? AppColors.darkInk : AppColors.ink),
            ),
            const SizedBox(height: 6),
            ...appState.members.map((u) {
              final isChecked = _selectedParticipants.contains(u.id);
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: isDark ? AppColors.darkSurface : AppColors.surface,
                  border: Border.all(color: inkColor, width: 2),
                ),
                child: Row(
                  children: [
                    Checkbox(
                      value: isChecked,
                      activeColor: AppColors.action,
                      checkColor: Colors.black,
                      onChanged: (val) {
                        setState(() {
                          if (val == true) {
                            _selectedParticipants.add(u.id);
                          } else {
                            _selectedParticipants.remove(u.id);
                          }
                        });
                        _updatePreview();
                      },
                    ),
                    Text(u.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                    const Spacer(),
                    if (_splitType != 'EQUAL' && isChecked)
                      SizedBox(
                        width: 90,
                        height: 38,
                        child: TextField(
                          controller: _customInputs[u.id],
                          onChanged: (_) => _updatePreview(),
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: InputDecoration(
                            hintText: _splitType == 'PERCENT'
                                ? '25%'
                                : _splitType == 'SHARES'
                                    ? '1'
                                    : '₹0.00',
                            border: OutlineInputBorder(borderRadius: BorderRadius.zero, borderSide: BorderSide(color: inkColor, width: 2)),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                          ),
                        ),
                      ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 16),

            // 7. Live Preview Table
            if (_previewShares.isNotEmpty) ...[
              NeobrutalCard(
                backgroundColor: AppColors.creditFill.withValues(alpha: 0.2),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'LIVE SPLIT PREVIEW',
                          style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, letterSpacing: 0.8),
                        ),
                        if (_isLoadingPreview)
                          const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ..._previewShares.map((s) {
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(s.userName ?? 'User #${s.userId}', style: const TextStyle(fontWeight: FontWeight.w700)),
                            MoneyText(amount: s.amountOwed, fontSize: 15, fontWeight: FontWeight.w900),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],

            // 8. Submit Button
            NeobrutalButton(
              text: 'SAVE EXPENSE',
              onPressed: _isSubmitting ? null : _submit,
              isLoading: _isSubmitting,
              backgroundColor: AppColors.action,
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _splitTab(String type, String label) {
    final isSelected = _splitType == type;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          setState(() => _splitType = type);
          _updatePreview();
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.action : (isDark ? AppColors.darkSurface : AppColors.surface),
            border: Border.all(color: inkColor, width: 2),
            boxShadow: isSelected ? [BoxShadow(color: inkColor, offset: const Offset(2, 2))] : null,
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontWeight: isSelected ? FontWeight.w900 : FontWeight.w700,
                fontSize: 12,
                color: isSelected ? Colors.black : (isDark ? AppColors.darkInk : AppColors.ink),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
