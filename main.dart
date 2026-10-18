import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'pages.dart';

const kGreen = Color(0xFF0B5D3F);
String api = 'https://eifm-wcc-api.onrender.com';
String? token;
final refresh = ValueNotifier<int>(0);
final sessionExpired = ValueNotifier<bool>(false);
Map<String, String> get h => {'Authorization': 'Bearer ${token ?? ''}'};
void msg(BuildContext c, String text) { if (c.mounted) ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(text))); }
void main() { WidgetsFlutterBinding.ensureInitialized(); runApp(const EIFMApp()); }
class EIFMApp extends StatelessWidget {
  const EIFMApp({super.key});
  @override Widget build(BuildContext context) => MaterialApp(debugShowCheckedModeBanner: false, title: 'EIFM WCC & PPM', theme: ThemeData(useMaterial3: true, colorScheme: ColorScheme.fromSeed(seedColor: kGreen), scaffoldBackgroundColor: Colors.white), home: const AppRoot());
}
class AppRoot extends StatefulWidget { const AppRoot({super.key}); @override State<AppRoot> createState() => _AppRootState(); }
class _AppRootState extends State<AppRoot> {
  bool loading = true; int tab = 0;
  String? startupError;
  @override void initState() {
    super.initState();
    sessionExpired.addListener(onSessionExpired);
    restore();
  }
  Future<void> restore() async {
    try {
      api = 'https://eifm-wcc-api.onrender.com';
      // Loading a saved session must never leave the app on an endless spinner.
      final p = await SharedPreferences.getInstance()
          .timeout(const Duration(seconds: 10));
      token = p.getString('token');
      startupError = null;
    } catch (_) {
      // Do not delete the saved token or any user data on an I/O failure.
      startupError = 'Saved login could not be loaded. Tap Retry.';
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }
  void onSessionExpired() { if (sessionExpired.value && mounted) logout(); }
  @override void dispose() { sessionExpired.removeListener(onSessionExpired); super.dispose(); }
  Future<void> logout() async { final p = await SharedPreferences.getInstance(); await p.remove('token'); token = null; equipmentFuture = get('equipment'); taskFut.clear(); if (mounted) setState(() => tab = 0); }
  @override Widget build(BuildContext c) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (startupError != null) {
      return Scaffold(body: Center(child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.error_outline, color: kGreen, size: 48),
          const SizedBox(height: 12),
          Text(startupError!, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          FilledButton(onPressed: () {
            setState(() { loading = true; startupError = null; });
            restore();
          }, child: const Text('Retry')),
        ]),
      )));
    }
    if (token == null) return LoginPage(onDone: () => setState(() {}));
    final pages = [const DashboardPage(), const LibraryPage(), const PpmPage(), const WccPage(), const RecordsPage()];
    return Scaffold(appBar: AppBar(title: const Text('EIFM WCC & PPM'), actions: [IconButton(tooltip: 'Logout', onPressed: logout, icon: const Icon(Icons.logout))]), body: IndexedStack(index: tab, children: pages), bottomNavigationBar: NavigationBar(selectedIndex: tab, onDestinationSelected: (v) => setState(() => tab = v), destinations: const [NavigationDestination(icon: Icon(Icons.dashboard), label: 'Home'), NavigationDestination(icon: Icon(Icons.apartment), label: 'Library'), NavigationDestination(icon: Icon(Icons.build), label: 'New PPM'), NavigationDestination(icon: Icon(Icons.description), label: 'New WCC'), NavigationDestination(icon: Icon(Icons.folder), label: 'My Records')]));
  }
}
class LoginPage extends StatefulWidget { final VoidCallback onDone; const LoginPage({super.key, required this.onDone}); @override State<LoginPage> createState() => _LoginPageState(); }
class _LoginPageState extends State<LoginPage> {
  final email = TextEditingController(), password = TextEditingController(); bool signup = false, busy = false;
  Future<void> auth() async {
    if (busy) return;
    setState(() => busy = true);
    try {
      final r = await http.post(Uri.parse('$api/${signup ? 'signup' : 'login'}'), headers: {'Content-Type':'application/json'}, body: jsonEncode({'email': email.text.trim(), 'password': password.text})).timeout(const Duration(seconds: 90));
      if (r.statusCode < 200 || r.statusCode >= 300) {
        String detail = 'Request failed (${r.statusCode})';
        try { final body = jsonDecode(r.body); detail = (body is Map ? (body['detail'] ?? body['message']) : null)?.toString() ?? detail; } catch (_) {}
        throw Exception(detail);
      }
      final t = jsonDecode(r.body)['token'] as String;
      final p = await SharedPreferences.getInstance(); await p.setString('token', t); token = t; equipmentFuture = get('equipment'); taskFut.clear(); sessionExpired.value = false;
      widget.onDone();
    } catch (e) { if (mounted) msg(context, 'Login error: $e'); }
    if (mounted) setState(() => busy = false);
  }
  @override void dispose() { email.dispose(); password.dispose(); super.dispose(); }
  @override Widget build(BuildContext c) => Scaffold(body: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [Image.asset('EIFM_logo.jpg', height: 120, errorBuilder: (_,__,___) => const Icon(Icons.apartment, size: 80, color: kGreen)), const SizedBox(height: 24), Text(signup ? 'Create Account' : 'Sign In', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)), const SizedBox(height: 12), TextField(controller: email, decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder())), const SizedBox(height: 12), TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder())), const SizedBox(height: 14), FilledButton(onPressed: busy ? null : auth, child: Text(busy ? 'Please wait...' : signup ? 'Sign Up' : 'Login')), TextButton(onPressed: () => setState(() => signup = !signup), child: Text(signup ? 'Already registered? Login' : 'Create account'))]))));
}
