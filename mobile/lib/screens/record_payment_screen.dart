import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/user.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class RecordPaymentScreen extends StatefulWidget {
  final User? preselectedRecipient;
  final String? prefilledAmount;

  const RecordPaymentScreen({
    super.key,
    this.preselectedRecipient,
    this.prefilledAmount,
  });

  @override
  State<RecordPaymentScreen> createState() => _RecordPaymentScreenState();
}

class _RecordPaymentScreenState extends State<RecordPaymentScreen> {
  User? _recipient;
  final _amountController = TextEditingController();
  final _noteController = TextEditingController();
  String _method = 'UPI';
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _recipient = widget.preselectedRecipient;
    if (widget.prefilledAmount != null) {
      _amountController.text = widget.prefilledAmount!;
    }
  }

  @override
  void dispose() {
    _amountController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  String _buildUpiUri() {
    if (_recipient == null || _recipient!.upiId.isEmpty) return '';
    final amount = double.tryParse(_amountController.text.trim()) ?? 0.0;
    final note = Uri.encodeComponent(_noteController.text.trim().isEmpty ? 'FlatSplit settlement' : _noteController.text.trim());
    return 'upi://pay?pa=${Uri.encodeComponent(_recipient!.upiId)}&pn=${Uri.encodeComponent(_recipient!.name)}&am=${amount.toStringAsFixed(2)}&cu=INR&tn=$note';
  }

  void _openUpiApp() async {
    final uriStr = _buildUpiUri();
    if (uriStr.isEmpty) return;
    final uri = Uri.parse(uriStr);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No UPI app found on this device.')),
        );
      }
    }
  }

  void _record() async {
    if (_recipient == null) {
      setState(() => _errorMessage = 'Please choose who to pay');
      return;
    }
    final amount = _amountController.text.trim();
    if (amount.isEmpty || (double.tryParse(amount) ?? 0) <= 0) {
      setState(() => _errorMessage = 'Please enter a valid amount');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    final appState = Provider.of<AppState>(context, listen: false);
    final ok = await appState.recordSettlement(
      toUserId: _recipient!.id,
      amount: amount,
      method: _method,
      note: _noteController.text.trim(),
    );

    setState(() => _isSubmitting = false);
    if (ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Payment recorded! Waiting for ${_recipient!.name} to confirm.')),
      );
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
    final upiUri = _buildUpiUri();

    final otherMembers = appState.members.where((u) => u.id != appState.currentUser?.id).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('RECORD PAYMENT', style: TextStyle(fontWeight: FontWeight.w900)),
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
                child: Text(_errorMessage!, style: const TextStyle(fontWeight: FontWeight.w700, color: Colors.black)),
              ),
              const SizedBox(height: 16),
            ],

            // 1. Recipient Selector
            Text('PAY TO', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, letterSpacing: 0.8, color: isDark ? AppColors.darkInk : AppColors.ink)),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurface : AppColors.surface,
                border: Border.all(color: inkColor, width: AppColors.borderWidth),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<User>(
                  value: _recipient,
                  hint: const Text('Select flatmate to pay'),
                  isExpanded: true,
                  items: otherMembers.map((u) {
                    return DropdownMenuItem(value: u, child: Text(u.name));
                  }).toList(),
                  onChanged: (u) => setState(() => _recipient = u),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // 2. Amount & Method
            NeobrutalTextField(
              controller: _amountController,
              label: 'Amount (₹)',
              hint: '0.00',
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
            NeobrutalTextField(
              controller: _noteController,
              label: 'Note (Optional)',
              hint: 'e.g. WiFi share',
            ),

            Text('METHOD', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, letterSpacing: 0.8, color: isDark ? AppColors.darkInk : AppColors.ink)),
            const SizedBox(height: 6),
            Row(
              children: ['UPI', 'CASH', 'BANK'].map((m) {
                final isSelected = _method == m;
                return Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: GestureDetector(
                      onTap: () => setState(() => _method = m),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: isSelected ? AppColors.action : (isDark ? AppColors.darkSurface : AppColors.surface),
                          border: Border.all(color: inkColor, width: 2),
                          boxShadow: isSelected ? [BoxShadow(color: inkColor, offset: const Offset(2, 2))] : null,
                        ),
                        child: Center(
                          child: Text(
                            m,
                            style: TextStyle(
                              fontWeight: isSelected ? FontWeight.w900 : FontWeight.w700,
                              color: isSelected ? Colors.black : (isDark ? AppColors.darkInk : AppColors.ink),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 20),

            // 3. Offline UPI QR Code & App Link (if method is UPI and recipient has upiId)
            if (_method == 'UPI' && _recipient != null && _recipient!.upiId.isNotEmpty && upiUri.isNotEmpty) ...[
              NeobrutalCard(
                child: Column(
                  children: [
                    Text(
                      'SCAN TO PAY ${_recipient!.name.toUpperCase()}',
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, letterSpacing: 0.8),
                    ),
                    const SizedBox(height: 12),
                    Container(
                      color: Colors.white,
                      padding: const EdgeInsets.all(12),
                      child: QrImageView(
                        data: upiUri,
                        version: QrVersions.auto,
                        size: 180.0,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _recipient!.upiId,
                      style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700, fontSize: 13),
                    ),
                    const SizedBox(height: 12),
                    NeobrutalButton(
                      text: 'OPEN IN UPI APP (GPAY/PHONEPE)',
                      icon: Icons.open_in_new,
                      backgroundColor: AppColors.creditFill,
                      onPressed: _openUpiApp,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],

            // 4. Save Button
            NeobrutalButton(
              text: 'RECORD SETTLEMENT',
              onPressed: _isSubmitting ? null : _record,
              isLoading: _isSubmitting,
              backgroundColor: AppColors.action,
            ),
            const SizedBox(height: 12),
            Center(
              child: Text(
                'Note: Recorded settlements start as PENDING and only move balances once confirmed by the receiver.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 11,
                  color: isDark ? AppColors.darkMuted : AppColors.muted,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
