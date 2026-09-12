import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _displayNameController;
  late TextEditingController _phoneController;
  late TextEditingController _upiIdController;
  late TextEditingController _passwordController;
  bool _saving = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    final user = Provider.of<AppState>(context, listen: false).currentUser;
    _displayNameController = TextEditingController(text: user?.displayName.isNotEmpty == true ? user!.displayName : user?.name ?? '');
    _phoneController = TextEditingController(text: user?.phone ?? '');
    _upiIdController = TextEditingController(text: user?.upiId ?? '');
    _passwordController = TextEditingController();
  }

  @override
  void dispose() {
    _displayNameController.dispose();
    _phoneController.dispose();
    _upiIdController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _saving = true;
      _errorMessage = null;
    });

    final appState = Provider.of<AppState>(context, listen: false);
    final result = await appState.updateProfile(
      displayName: _displayNameController.text.trim(),
      phone: _phoneController.text.trim(),
      upiId: _upiIdController.text.trim(),
      password: _passwordController.text.isNotEmpty ? _passwordController.text : null,
    );

    if (!mounted) return;

    setState(() => _saving = false);

    if (result['ok'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Profile updated successfully!'),
          backgroundColor: AppColors.creditText,
        ),
      );
      Navigator.of(context).pop();
    } else {
      setState(() {
        _errorMessage = result['error'] ?? 'Failed to update profile';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final user = appState.currentUser;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;
    final paperColor = isDark ? AppColors.darkPaper : AppColors.paper;

    return Scaffold(
      backgroundColor: paperColor,
      appBar: AppBar(
        title: const Text(
          'EDIT PROFILE',
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
        ),
        elevation: 0,
        backgroundColor: isDark ? AppColors.darkSurface : AppColors.topbar,
        foregroundColor: inkColor,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // User Info Card
                NeobrutalCard(
                  backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
                  child: Row(
                    children: [
                      AvatarChipWidget(
                        initials: user?.initials ?? '?',
                        size: 56,
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user?.name ?? 'Flatmate',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w900,
                                color: inkColor,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              '@${user?.username ?? ''}',
                              style: TextStyle(
                                fontFamily: 'monospace',
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: isDark ? AppColors.darkMuted : AppColors.muted,
                              ),
                            ),
                            const SizedBox(height: 6),
                            if (user?.isStaff == true)
                              const NeobrutalBadge(
                                label: 'FLAT ADMIN',
                                backgroundColor: AppColors.creditFill,
                              )
                            else
                              const NeobrutalBadge(
                                label: 'FLATMATE',
                                backgroundColor: AppColors.infoFill,
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 24),

                if (_errorMessage != null) ...[
                  NeobrutalCard(
                    backgroundColor: AppColors.debitFill,
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: Colors.black, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: const TextStyle(
                              color: Colors.black,
                              fontWeight: FontWeight.w700,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                ],

                // Display Name
                NeobrutalTextField(
                  controller: _displayNameController,
                  label: 'Full Name / Display Name',
                  hint: 'e.g. Priya Sharma',
                  validator: (val) {
                    if (val == null || val.trim().isEmpty) {
                      return 'Display name cannot be empty';
                    }
                    return null;
                  },
                ),

                // Phone Number
                NeobrutalTextField(
                  controller: _phoneController,
                  label: 'Phone Number',
                  hint: 'e.g. 9876543210',
                  keyboardType: TextInputType.phone,
                ),

                // UPI ID
                NeobrutalTextField(
                  controller: _upiIdController,
                  label: 'UPI ID (For Receiving Repayments)',
                  hint: 'e.g. name@okhdfcbank',
                  keyboardType: TextInputType.emailAddress,
                ),

                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkSurface : AppColors.surface,
                    border: Border.all(color: inkColor, width: 2.0),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.qr_code, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Your UPI ID is used to generate QR codes and payment deep-links when flatmates settle debts with you.',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: isDark ? AppColors.darkMuted : AppColors.muted,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 20),

                // New Password (Optional)
                NeobrutalTextField(
                  controller: _passwordController,
                  label: 'New Password (Optional)',
                  hint: 'Leave blank to keep current password',
                  obscureText: true,
                  validator: (val) {
                    if (val != null && val.isNotEmpty && val.length < 6) {
                      return 'Password must be at least 6 characters';
                    }
                    return null;
                  },
                ),

                const SizedBox(height: 24),

                // Submit Button
                NeobrutalButton(
                  text: 'SAVE PROFILE',
                  icon: Icons.check,
                  isLoading: _saving,
                  backgroundColor: AppColors.creditFill,
                  textColor: Colors.black,
                  onPressed: _saving ? null : _saveProfile,
                ),

                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
