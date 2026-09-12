import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../theme/colors.dart';
import '../theme/neobrutalism.dart';

class ServerConfigScreen extends StatefulWidget {
  const ServerConfigScreen({super.key});

  @override
  State<ServerConfigScreen> createState() => _ServerConfigScreenState();
}

class _ServerConfigScreenState extends State<ServerConfigScreen> {
  late TextEditingController _urlController;
  bool _testing = false;
  String? _statusMessage;
  bool? _isSuccess;

  @override
  void initState() {
    super.initState();
    final appState = Provider.of<AppState>(context, listen: false);
    _urlController = TextEditingController(text: appState.serverUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  void _testAndSave() async {
    setState(() {
      _testing = true;
      _statusMessage = null;
    });

    final appState = Provider.of<AppState>(context, listen: false);
    final url = _urlController.text.trim();
    final success = await appState.setServerUrl(url);

    setState(() {
      _testing = false;
      _isSuccess = success;
      _statusMessage = success
          ? 'Connected successfully to FlatSplit server!'
          : 'Could not connect. Check the IP and make sure server is running on port 8000.';
    });

    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Server URL saved!')),
      );
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'SERVER CONFIGURATION',
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.5),
        ),
        elevation: 0,
        backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: Container(color: isDark ? AppColors.darkInk : AppColors.ink, height: 3),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            NeobrutalCard(
              backgroundColor: AppColors.infoFill,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    'LAN SERVER (TERMUX / WI-FI)',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Colors.black),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'FlatSplit runs on your local Wi-Fi. The default server is your phone\'s Termux instance:\n\n'
                    '• Termux (Default): http://192.168.1.4:8000\n'
                    '• PC Wi-Fi Server: http://192.168.1.11:8000\n'
                    '• Android Emulator: http://10.0.2.2:8000',
                    style: TextStyle(fontSize: 13, color: Colors.black, height: 1.4, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'QUICK PRESETS',
              style: TextStyle(
                fontWeight: FontWeight.w900,
                fontSize: 12,
                letterSpacing: 0.8,
                color: isDark ? AppColors.darkMuted : AppColors.muted,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _presetChip('Termux (Default)', 'http://192.168.1.4:8000', isPrimary: true),
                _presetChip('PC Server', 'http://192.168.1.11:8000'),
                _presetChip('Emulator', 'http://10.0.2.2:8000'),
                _presetChip('Localhost', 'http://127.0.0.1:8000'),
              ],
            ),
            const SizedBox(height: 20),
            NeobrutalTextField(
              controller: _urlController,
              label: 'Host Address',
              hint: 'http://192.168.1.4:8000',
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 8),
            NeobrutalButton(
              text: 'TEST & SAVE CONNECTION',
              onPressed: _testAndSave,
              isLoading: _testing,
              backgroundColor: AppColors.action,
            ),
            if (_statusMessage != null) ...[
              const SizedBox(height: 16),
              NeobrutalCard(
                backgroundColor: _isSuccess == true ? AppColors.creditFill : AppColors.debitFill,
                child: Row(
                  children: [
                    Icon(
                      _isSuccess == true ? Icons.check_circle : Icons.error,
                      color: Colors.black,
                      size: 24,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _statusMessage!,
                        style: const TextStyle(fontWeight: FontWeight.w800, color: Colors.black, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _presetChip(String label, String url, {bool isPrimary = false}) {
    final isCurrent = _urlController.text.trim() == url;
    return GestureDetector(
      onTap: () {
        setState(() {
          _urlController.text = url;
          _statusMessage = null;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isCurrent
              ? AppColors.action
              : (isPrimary ? AppColors.infoFill : Colors.transparent),
          border: Border.all(color: Colors.black, width: 2),
          boxShadow: [
            if (isCurrent)
              const BoxShadow(color: Colors.black, offset: Offset(2, 2), blurRadius: 0),
          ],
        ),
        child: Text(
          label,
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 12,
            color: isCurrent ? Colors.black : (isPrimary ? Colors.black : null),
          ),
        ),
      ),
    );
  }
}
