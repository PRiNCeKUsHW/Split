import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/category.dart';
import '../models/expense.dart';
import '../models/settlement.dart';
import '../models/user.dart';
import '../services/api_client.dart';

class AppState extends ChangeNotifier {
  final ApiClient _client = ApiClient();
  ApiClient get client => _client;

  User? _currentUser;
  bool _isLoading = false;
  String? _errorMessage;
  ThemeMode _themeMode = ThemeMode.system;

  // Dashboard state
  String _myBalance = '0.00';
  String _myBalanceMagnitude = '0.00';
  String _myPaid = '0.00';
  String _myOwed = '0.00';
  bool _isOwed = false;
  bool _owes = false;
  bool _isSettled = true;
  String _monthTotal = '0.00';
  String _myMonthShare = '0.00';
  List<Transfer> _transfers = [];
  List<Map<String, dynamic>> _drafts = [];
  List<Map<String, dynamic>> _recentActivity = [];

  // Lists
  List<Expense> _expenses = [];
  List<Category> _categories = [];
  List<User> _members = [];

  // Settlements
  List<BalanceSummary> _balanceRows = [];
  List<Transfer> _simplifiedSettlements = [];
  List<SettlementItem> _awaitingConfirmation = [];
  List<SettlementItem> _myPendingSent = [];
  List<SettlementItem> _settlementHistory = [];

  // Recurring & Away
  List<Map<String, dynamic>> _recurringTemplates = [];
  List<Map<String, dynamic>> _awayPeriods = [];
  Map<String, dynamic>? _summary;

  // Getters
  User? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  ThemeMode get themeMode => _themeMode;
  String get serverUrl => _client.baseUrl;
  String get flatName => 'FlatSplit';
  Map<String, dynamic>? get summary => _summary;

  String get myBalance => _myBalance;
  String get myBalanceMagnitude => _myBalanceMagnitude;
  String get myPaid => _myPaid;
  String get myOwed => _myOwed;
  bool get isOwed => _isOwed;
  bool get owes => _owes;
  bool get isSettled => _isSettled;
  String get monthTotal => _monthTotal;
  String get myMonthShare => _myMonthShare;
  List<Transfer> get transfers => _transfers;
  List<Map<String, dynamic>> get drafts => _drafts;
  List<Map<String, dynamic>> get recentActivity => _recentActivity;

  List<Expense> get expenses => _expenses;
  List<Category> get categories => _categories;
  List<User> get members => _members;

  List<BalanceSummary> get balanceRows => _balanceRows;
  List<Transfer> get simplifiedSettlements => _simplifiedSettlements;
  List<SettlementItem> get awaitingConfirmation => _awaitingConfirmation;
  List<SettlementItem> get myPendingSent => _myPendingSent;
  List<SettlementItem> get settlementHistory => _settlementHistory;
  List<Map<String, dynamic>> get recurringTemplates => _recurringTemplates;
  List<Map<String, dynamic>> get awayPeriods => _awayPeriods;

  Future<void> init() async {
    await _client.init();
    final prefs = await SharedPreferences.getInstance();
    final savedTheme = prefs.getString('theme_mode');
    if (savedTheme == 'light') _themeMode = ThemeMode.light;
    if (savedTheme == 'dark') _themeMode = ThemeMode.dark;

    // Check if session exists
    await checkAuth();
  }

  void setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    if (mode == ThemeMode.light) await prefs.setString('theme_mode', 'light');
    if (mode == ThemeMode.dark) await prefs.setString('theme_mode', 'dark');
    if (mode == ThemeMode.system) await prefs.remove('theme_mode');
  }

  Future<bool> setServerUrl(String url) async {
    await _client.setBaseUrl(url);
    notifyListeners();
    return await _client.testConnection();
  }

  Future<bool> checkAuth() async {
    try {
      final res = await _client.get('/api/auth/me');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (data['authenticated'] == true && data['user'] != null) {
          _currentUser = User.fromJson(data['user']);
          notifyListeners();
          await refreshAll();
          return true;
        }
      }
    } catch (_) {}
    _currentUser = null;
    notifyListeners();
    return false;
  }

  Future<bool> login(String username, String? password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final payload = <String, dynamic>{'username': username};
      if (password != null && password.isNotEmpty) {
        payload['password'] = password;
      }
      final res = await _client.post('/api/auth/login', data: payload);
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (data['ok'] == true && data['user'] != null) {
          _currentUser = User.fromJson(data['user']);
          _isLoading = false;
          notifyListeners();
          await refreshAll();
          return true;
        }
      }
      final err = json.decode(res.body)['error'] ?? 'Login failed';
      _errorMessage = err.toString();
    } catch (e) {
      _errorMessage = 'Could not reach server: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
    return false;
  }

  Future<void> logout() async {
    try {
      await _client.post('/api/auth/logout');
    } catch (_) {}
    await _client.clearSession();
    _currentUser = null;
    notifyListeners();
  }

  Future<Map<String, dynamic>> updateProfile({
    required String displayName,
    required String phone,
    required String upiId,
    String? password,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final payload = <String, dynamic>{
        'display_name': displayName,
        'phone': phone,
        'upi_id': upiId,
        if (password != null && password.isNotEmpty) 'password': password,
      };

      final res = await _client.post('/api/auth/profile', data: payload);
      final data = json.decode(res.body);

      if (res.statusCode == 200 && data['ok'] == true && data['user'] != null) {
        _currentUser = User.fromJson(data['user']);
        _isLoading = false;
        notifyListeners();
        await fetchMembers();
        return {'ok': true};
      } else {
        _isLoading = false;
        _errorMessage = data['error'] ?? 'Failed to update profile';
        notifyListeners();
        return {'ok': false, 'error': _errorMessage};
      }
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Network error: $e';
      notifyListeners();
      return {'ok': false, 'error': _errorMessage};
    }
  }

  Future<void> refreshAll() async {
    await Future.wait([
      fetchMembers(),
      fetchCategories(),
      fetchDashboard(),
      fetchExpenses(),
      fetchSettlements(),
      fetchRecurring(),
      fetchAwayPeriods(),
      fetchSummary(),
    ]);
  }

  Future<void> fetchMembers() async {
    try {
      final res = await _client.get('/api/members');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final list = (data['members'] as List).map((m) => User.fromJson(m)).toList();
        _members = list;
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<Map<String, dynamic>?> createMember({
    required String username,
    required String displayName,
    String? password,
    String? phone,
    String? upiId,
  }) async {
    try {
      final payload = <String, dynamic>{
        'username': username,
        'display_name': displayName,
      };
      if (password != null && password.trim().isNotEmpty) {
        payload['password'] = password.trim();
      }
      if (phone != null && phone.trim().isNotEmpty) {
        payload['phone'] = phone.trim();
      }
      if (upiId != null && upiId.trim().isNotEmpty) {
        payload['upi_id'] = upiId.trim();
      }

      final res = await _client.post('/api/members/create', data: payload);
      if (res.statusCode == 200) {
        await fetchMembers();
        return json.decode(res.body) as Map<String, dynamic>;
      } else {
        final data = json.decode(res.body);
        return {'error': data['error'] ?? 'Failed to add flatmate'};
      }
    } catch (e) {
      return {'error': e.toString()};
    }
  }

  Future<void> fetchCategories() async {
    try {
      final res = await _client.get('/api/categories');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final list = (data['categories'] as List).map((c) => Category.fromJson(c)).toList();
        _categories = list;
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> fetchDashboard() async {
    try {
      final res = await _client.get('/api/dashboard');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        _myBalance = data['my_balance']?.toString() ?? '0.00';
        _myBalanceMagnitude = data['my_balance_magnitude']?.toString() ?? '0.00';
        _myPaid = data['paid']?.toString() ?? '0.00';
        _myOwed = data['owed']?.toString() ?? '0.00';
        _isOwed = data['is_owed'] as bool? ?? false;
        _owes = data['owes'] as bool? ?? false;
        _isSettled = data['is_settled'] as bool? ?? false;
        _monthTotal = data['month_total']?.toString() ?? '0.00';
        _myMonthShare = data['my_month_share']?.toString() ?? '0.00';

        _transfers = (data['transfers'] as List)
            .map((t) => Transfer.fromJson(t as Map<String, dynamic>))
            .toList();

        _drafts = (data['drafts'] as List).map((d) => d as Map<String, dynamic>).toList();
        _recentActivity = (data['recent_activity'] as List)
            .map((a) => a as Map<String, dynamic>)
            .toList();

        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> fetchExpenses({int? year, int? month, int? categoryId, String? query}) async {
    try {
      String path = '/api/expenses';
      final params = <String>[];
      if (year != null && month != null) {
        params.add('year=$year');
        params.add('month=$month');
      }
      if (categoryId != null) params.add('category=$categoryId');
      if (query != null && query.isNotEmpty) params.add('q=${Uri.encodeComponent(query)}');

      if (params.isNotEmpty) path += '?${params.join('&')}';

      final res = await _client.get(path);
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        _expenses = (data['expenses'] as List).map((e) => Expense.fromJson(e)).toList();
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<Expense?> getExpenseDetail(int id) async {
    try {
      final res = await _client.get('/api/expenses/$id');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        return Expense.fromJson(data);
      }
    } catch (_) {}
    return null;
  }

  Future<bool> createExpense(Map<String, dynamic> data) async {
    try {
      final res = await _client.post('/api/expenses/create', data: data);
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
      final err = json.decode(res.body);
      _errorMessage = err['error'] ?? 'Failed to create expense';
    } catch (e) {
      _errorMessage = e.toString();
    }
    notifyListeners();
    return false;
  }

  Future<bool> updateExpense(int id, Map<String, dynamic> data) async {
    try {
      final res = await _client.post('/api/expenses/$id/edit', data: data);
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
      final err = json.decode(res.body);
      _errorMessage = err['error'] ?? 'Failed to update expense';
    } catch (e) {
      _errorMessage = e.toString();
    }
    notifyListeners();
    return false;
  }

  Future<bool> deleteExpense(int id) async {
    try {
      final res = await _client.post('/api/expenses/$id/delete');
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<bool> fillDraftAmount(int id, String amount) async {
    try {
      final res = await _client.post('/api/expenses/$id/amount', data: {'amount': amount});
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<List<ExpenseShare>> previewSplit(Map<String, dynamic> data) async {
    try {
      final res = await _client.post('/api/expenses/preview', data: data);
      if (res.statusCode == 200) {
        final jsonResult = json.decode(res.body);
        final list = (jsonResult['shares'] as List)
            .map((s) => ExpenseShare.fromJson(s as Map<String, dynamic>))
            .toList();
        return list;
      }
    } catch (_) {}
    return [];
  }

  Future<bool> addComment(int expenseId, String body) async {
    try {
      final res = await _client.post('/api/expenses/$expenseId/comment', data: {'body': body});
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<void> fetchSettlements() async {
    try {
      final res = await _client.get('/api/settlements');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        _balanceRows = (data['balance_rows'] as List)
            .map((b) => BalanceSummary.fromJson(b as Map<String, dynamic>))
            .toList();
        _simplifiedSettlements = (data['transfers'] as List)
            .map((t) => Transfer.fromJson(t as Map<String, dynamic>))
            .toList();
        _awaitingConfirmation = (data['awaiting_confirmation'] as List)
            .map((s) => SettlementItem.fromJson(s as Map<String, dynamic>))
            .toList();
        _myPendingSent = (data['my_pending_sent'] as List)
            .map((s) => SettlementItem.fromJson(s as Map<String, dynamic>))
            .toList();
        _settlementHistory = (data['history'] as List)
            .map((h) => SettlementItem.fromJson(h as Map<String, dynamic>))
            .toList();
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<bool> recordSettlement({
    required int toUserId,
    required String amount,
    String method = 'UPI',
    String note = '',
  }) async {
    try {
      final res = await _client.post('/api/settlements/create', data: {
        'to_user': toUserId,
        'amount': amount,
        'method': method,
        'note': note,
      });
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
      final err = json.decode(res.body);
      _errorMessage = err['error'] ?? 'Settlement failed';
    } catch (e) {
      _errorMessage = e.toString();
    }
    notifyListeners();
    return false;
  }

  Future<bool> confirmSettlement(int id) async {
    try {
      final res = await _client.post('/api/settlements/$id/confirm');
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<bool> rejectSettlement(int id) async {
    try {
      final res = await _client.post('/api/settlements/$id/reject');
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<Map<String, dynamic>?> getSettlementQr(int id) async {
    try {
      final res = await _client.get('/api/settlements/$id/qr');
      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  Future<void> fetchRecurring() async {
    try {
      final res = await _client.get('/api/recurring');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        _recurringTemplates = (data['templates'] as List)
            .map((t) => t as Map<String, dynamic>)
            .toList();
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<bool> generateRecurring() async {
    try {
      final res = await _client.post('/api/recurring/generate');
      if (res.statusCode == 200) {
        await refreshAll();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<void> fetchAwayPeriods() async {
    try {
      final res = await _client.get('/api/away');
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        _awayPeriods = (data['away_periods'] as List)
            .map((p) => p as Map<String, dynamic>)
            .toList();
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<bool> createAwayPeriod(String startDate, String endDate) async {
    try {
      final res = await _client.post('/api/away/create', data: {
        'start_date': startDate,
        'end_date': endDate,
      });
      if (res.statusCode == 200) {
        await fetchAwayPeriods();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<bool> deleteAwayPeriod(int id) async {
    try {
      final res = await _client.post('/api/away/$id/delete');
      if (res.statusCode == 200) {
        await fetchAwayPeriods();
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<void> fetchSummary({int? year, int? month}) async {
    try {
      String path = '/api/summary';
      if (year != null && month != null) {
        path += '?year=$year&month=$month';
      }
      final res = await _client.get(path);
      if (res.statusCode == 200) {
        _summary = json.decode(res.body) as Map<String, dynamic>;
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<bool> toggleMonth({required int year, required int month, required bool reopen}) async {
    try {
      final res = await _client.post('/api/month/toggle', data: {
        'year': year,
        'month': month,
        'action': reopen ? 'reopen' : 'close',
      });
      if (res.statusCode == 200) {
        await fetchSummary(year: year, month: month);
        await refreshAll();
        return true;
      }
    } catch (_) {}
    return false;
  }
}
