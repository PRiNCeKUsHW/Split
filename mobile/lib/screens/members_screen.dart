import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class MembersScreen extends StatelessWidget {
  const MembersScreen({super.key});

  void _showAddMemberModal(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    final usernameCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    final passwordCtrl = TextEditingController();
    final upiCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();

    bool isSubmitting = false;
    String? formError;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            final bottomInset = MediaQuery.of(context).viewInsets.bottom;
            final navPadding = MediaQuery.of(context).padding.bottom;

            return SafeArea(
              bottom: true,
              child: Container(
                padding: EdgeInsets.fromLTRB(20, 20, 20, 20 + bottomInset + (navPadding > 0 ? navPadding : 8)),
                decoration: BoxDecoration(
                  border: Border(top: BorderSide(color: inkColor, width: AppColors.borderWidth)),
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              'ADD A FLATMATE',
                              style: TextStyle(
                                fontWeight: FontWeight.w900,
                                fontSize: 16,
                                letterSpacing: 0.5,
                                color: inkColor,
                              ),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close),
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            onPressed: () => Navigator.of(ctx).pop(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),

                      if (formError != null) ...[
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppColors.debitFill,
                            border: Border.all(color: Colors.black, width: AppColors.thinBorderWidth),
                          ),
                          child: Text(
                            formError!,
                            style: const TextStyle(
                              color: Colors.black,
                              fontWeight: FontWeight.w700,
                              fontSize: 12,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                      ],

                      NeobrutalTextField(
                        controller: usernameCtrl,
                        label: 'USERNAME',
                        hint: 'e.g. priya (lowercase, no spaces)',
                      ),
                      const SizedBox(height: 12),

                      NeobrutalTextField(
                        controller: nameCtrl,
                        label: 'FULL NAME',
                        hint: 'e.g. Priya Sharma',
                      ),
                      const SizedBox(height: 12),

                      NeobrutalTextField(
                        controller: passwordCtrl,
                        label: 'PASSWORD (OPTIONAL)',
                        hint: 'Leave blank to generate invite link',
                        obscureText: true,
                      ),
                      const SizedBox(height: 12),

                      NeobrutalTextField(
                        controller: upiCtrl,
                        label: 'UPI ID (OPTIONAL)',
                        hint: 'e.g. priya@okhdfcbank',
                      ),
                      const SizedBox(height: 12),

                      NeobrutalTextField(
                        controller: phoneCtrl,
                        label: 'PHONE (OPTIONAL)',
                        hint: 'e.g. 9876543210',
                        keyboardType: TextInputType.phone,
                      ),
                      const SizedBox(height: 18),

                      NeobrutalButton(
                        text: isSubmitting ? 'ADDING...' : 'CREATE FLATMATE',
                        backgroundColor: AppColors.action,
                        textColor: Colors.black,
                        onPressed: isSubmitting
                            ? () {}
                            : () async {
                                final username = usernameCtrl.text.trim().toLowerCase();
                                final name = nameCtrl.text.trim();
                                if (username.isEmpty) {
                                  setModalState(() => formError = 'Please enter a username.');
                                  return;
                                }
                                if (name.isEmpty) {
                                  setModalState(() => formError = 'Please enter the flatmate\'s name.');
                                  return;
                                }

                                setModalState(() {
                                  isSubmitting = true;
                                  formError = null;
                                });

                                final appState = Provider.of<AppState>(context, listen: false);
                                final res = await appState.createMember(
                                  username: username,
                                  displayName: name,
                                  password: passwordCtrl.text,
                                  upiId: upiCtrl.text,
                                  phone: phoneCtrl.text,
                                );

                                if (res != null && res['ok'] == true) {
                                  if (context.mounted) {
                                    Navigator.of(ctx).pop();
                                    final link = res['invite_link'] as String?;
                                    if (link != null && passwordCtrl.text.trim().isEmpty) {
                                      _showInviteLinkDialog(context, name, link);
                                    } else {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text('$name added successfully!'),
                                          backgroundColor: AppColors.creditText,
                                        ),
                                      );
                                    }
                                  }
                                } else {
                                  setModalState(() {
                                    isSubmitting = false;
                                    formError = res?['error']?.toString() ?? 'Failed to add flatmate.';
                                  });
                                }
                              },
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showInviteLinkDialog(BuildContext context, String name, String inviteLink) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
        shape: RoundedRectangleBorder(
          side: BorderSide(color: inkColor, width: AppColors.borderWidth),
          borderRadius: BorderRadius.zero,
        ),
        title: Text(
          'INVITE LINK CREATED',
          style: TextStyle(fontWeight: FontWeight.w900, color: inkColor, fontSize: 16),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Share this link with $name so they can set their password and join:',
              style: TextStyle(color: inkColor, fontSize: 13),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              color: isDark ? const Color(0xFF282535) : const Color(0xFFF3F4F6),
              child: SelectableText(
                inviteLink,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: inviteLink));
              Navigator.of(ctx).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Invite link copied to clipboard!')),
              );
            },
            child: const Text('COPY LINK', style: TextStyle(fontWeight: FontWeight.w900, color: Colors.black)),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('DONE', style: TextStyle(color: inkColor)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final inkColor = isDark ? AppColors.darkInk : AppColors.ink;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'FLATMATES',
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
        ),
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12.0, top: 10.0, bottom: 10.0),
            child: GestureDetector(
              onTap: () => _showAddMemberModal(context),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.action,
                  border: Border.all(color: inkColor, width: AppColors.thinBorderWidth),
                  boxShadow: [
                    BoxShadow(
                      color: inkColor,
                      offset: const Offset(AppColors.smallShadowOffset, AppColors.smallShadowOffset),
                    ),
                  ],
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.person_add, size: 14, color: Colors.black),
                    SizedBox(width: 4),
                    Text(
                      'ADD',
                      style: TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 11,
                        color: Colors.black,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: Container(color: inkColor, height: 3),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () => appState.fetchMembers(),
        color: Colors.black,
        backgroundColor: AppColors.action,
        child: ListView(
          padding: const EdgeInsets.all(16.0),
          children: [
            // Top action bar matching web: + Add flatmate button
            NeobrutalButton(
              text: '+ ADD FLATMATE',
              icon: Icons.person_add,
              backgroundColor: AppColors.action,
              textColor: Colors.black,
              onPressed: () => _showAddMemberModal(context),
            ),
            const SizedBox(height: 16),

            NeobrutalCard(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              child: appState.members.isEmpty
                  ? Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16.0),
                      child: Center(
                        child: Text(
                          'No flatmates found.',
                          style: TextStyle(
                            color: isDark ? AppColors.darkMuted : AppColors.muted,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    )
                  : Column(
                      children: appState.members.asMap().entries.map((entry) {
                        final idx = entry.key;
                        final m = entry.value;
                        final isLast = idx == appState.members.length - 1;

                        return Container(
                          padding: const EdgeInsets.symmetric(vertical: 12.0),
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
                              AvatarChipWidget(
                                initials: m.initials,
                                size: 36,
                                hasShadow: false,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      m.name,
                                      style: TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 15,
                                        color: inkColor,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      m.upiId.isNotEmpty ? m.upiId : '@${m.username}',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontFamily: 'monospace',
                                        color: isDark ? AppColors.darkMuted : AppColors.muted,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              if (m.isStaff)
                                const NeobrutalBadge(
                                  label: 'ADMIN',
                                  backgroundColor: AppColors.action,
                                  textColor: Colors.black,
                                ),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
