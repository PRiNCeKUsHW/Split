import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String defaultServerUrl = 'http://192.168.1.4:8000';
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  String _baseUrl = defaultServerUrl;
  final Map<String, String> _cookies = {};

  String get baseUrl => _baseUrl;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final savedUrl = prefs.getString('server_url');
    if (savedUrl != null && savedUrl.isNotEmpty) {
      _baseUrl = savedUrl.endsWith('/') ? savedUrl.substring(0, savedUrl.length - 1) : savedUrl;
    }
    final savedCookies = prefs.getString('session_cookies');
    if (savedCookies != null) {
      try {
        final decoded = json.decode(savedCookies) as Map<String, dynamic>;
        decoded.forEach((k, v) => _cookies[k] = v.toString());
      } catch (_) {}
    }
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', _baseUrl);
  }

  String _buildCookieHeader() {
    return _cookies.entries.map((e) => '${e.key}=${e.value}').join('; ');
  }

  void _saveCookies(http.Response response) {
    final rawCookies = response.headers['set-cookie'];
    if (rawCookies != null) {
      // Split cookies (handling standard HTTP comma/semicolon)
      final parts = rawCookies.split(RegExp(r',(?=\s*[A-Za-z0-9_-]+=)'));
      for (var part in parts) {
        final cookiePair = part.split(';')[0].trim();
        final equalIndex = cookiePair.indexOf('=');
        if (equalIndex != -1) {
          final key = cookiePair.substring(0, equalIndex).trim();
          final val = cookiePair.substring(equalIndex + 1).trim();
          _cookies[key] = val;
        }
      }
      SharedPreferences.getInstance().then((prefs) {
        prefs.setString('session_cookies', json.encode(_cookies));
      });
    }
  }

  Map<String, String> _headers({bool isJson = true}) {
    final map = <String, String>{
      'Accept': 'application/json',
    };
    if (isJson) {
      map['Content-Type'] = 'application/json';
    }
    final cookieStr = _buildCookieHeader();
    if (cookieStr.isNotEmpty) {
      map['Cookie'] = cookieStr;
    }
    return map;
  }

  Future<http.Response> get(String endpoint) async {
    final uri = Uri.parse('$_baseUrl$endpoint');
    final response = await http.get(uri, headers: _headers()).timeout(const Duration(seconds: 10));
    _saveCookies(response);
    return response;
  }

  Future<http.Response> post(String endpoint, {Map<String, dynamic>? data}) async {
    final uri = Uri.parse('$_baseUrl$endpoint');
    final body = data != null ? json.encode(data) : null;
    final response = await http
        .post(uri, headers: _headers(isJson: true), body: body)
        .timeout(const Duration(seconds: 12));
    _saveCookies(response);
    return response;
  }

  Future<http.Response> delete(String endpoint) async {
    final uri = Uri.parse('$_baseUrl$endpoint');
    final response = await http.delete(uri, headers: _headers()).timeout(const Duration(seconds: 10));
    _saveCookies(response);
    return response;
  }

  Future<bool> testConnection() async {
    try {
      final res = await get('/api/categories');
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<void> clearSession() async {
    _cookies.clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('session_cookies');
  }
}
