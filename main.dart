import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_cropper/image_cropper.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'pages.dart';

const String kServer = 'https://eifm-wcc-api.onrender.com';
String api = kServer;
String? token;
final refresh = ValueNotifier<int>(0);
Map<String, String> get h => {'Authorization': 'Bearer ${token ?? ''}'};
void msg(BuildContext c, String t) =>
    ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(t)));

Future<void> shareZip(int id) async {
  final r = await http.get(Uri.parse('$api/records/$id/package'), headers: h);
  final d = await getTemporaryDirectory();
  final f = File('${d.path}/EIFM_$id.zip')..writeAsBytesSync(r.bodyBytes);
  await Share.shareXFiles([XFile(f.path)]);
}

// Wakes up the free Render server in the background so login is faster.
void wake() async {
  try {
    await http.get(Uri.parse(api)).timeout(const Duration(seconds: 100));
  } catch (_) {}
}

// After generating a record: share the real files (Word / Excel / PDF ...) one by one.
// If the server gives no separate file, fall back to the zip package.
Future<void> shareResult(int id) async {
  final d = await getTemporaryDirectory();
  final files = <XFile>[];
  for (final field in ['file', 'checklist']) {
    try {
      final r = await http
          .get(Uri.parse('$api/records/$id/$field'), headers: h)
          .timeout(const Duration(seconds: 120));
      if (r.statusCode != 200 || r.bodyBytes.isEmpty) continue;
      final cd = r.headers['content-disposition'] ?? '';
      final n = RegExp(r'filename="?([^";]+)').firstMatch(cd)?.group(1) ?? 'EIFM_${id}_$field';
      final dir = Directory('${d.path}/$field')..createSync(recursive: true);
      final f = File('${dir.path}/$n')..writeAsBytesSync(r.bodyBytes);
      files.add(XFile(f.path));
    } catch (_) {}
  }
  if (files.isEmpty) {
    final r = await http.get(Uri.parse('$api/records/$id/package'), headers: h);
    final f = File('${d.path}/EIFM_$id.zip')..writeAsBytesSync(r.bodyBytes);
    files.add(XFile(f.path));
  }
  await Share.shareXFiles(files);
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  token = prefs.getString('token');
  final custom = prefs.getString('api_custom');
  api = (custom != null && custom.isNotEmpty) ? custom : kServer;
  wake();
  runApp(MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      scaffoldBackgroundColor: Colors.white,
      primaryColor: const Color(0xFF0F5A3B), // EIFM Green
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF0F5A3B),
        primary: const Color(0xFF0F5A3B),
      ),
      useMaterial3: true,
    ),
    home: token == null ? const Login() : const Home(),
  ));
}

class Login extends StatefulWidget {
  const Login({super.key});
  @override
  State<Login> createState() => _LoginState();
}

class _LoginState extends State<Login> {
  final e = TextEditingController(),
      p = TextEditingController(),
      sv = TextEditingController(text: api);
  bool busy = false;
  bool showServer = false; // Long press logo/title to toggle server input

  Future<void> go(String path) async {
    setState(() => busy = true);
    final prefs = await SharedPreferences.getInstance();
    if (showServer) {
      final v = sv.text.trim().replaceAll(RegExp(r'/+$'), '');
      if (v.isNotEmpty) {
        api = v;
        await prefs.setString('api_custom', v);
      } else {
        api = kServer;
        await prefs.remove('api_custom');
      }
    }
    try {
      final r = await http
          .post(Uri.parse('$api/$path'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({'email': e.text.trim(), 'password': p.text}))
          .timeout(const Duration(seconds: 90));
      final j = jsonDecode(r.body);
      if (r.statusCode == 200) {
        token = j['token'];
        await prefs.setString('token', token!);
        if (mounted) {
          Navigator.pushReplacement(
              context, MaterialPageRoute(builder: (_) => const Home()));
        }
        return;
      }
      if (mounted) msg(context, '${j['detail']}');
    } catch (_) {
      if (mounted) {
        msg(context,
            'Internet / server error. Server may be waking up - wait 1 minute and try again.');
      }
    }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.white,
        body: SafeArea(
          child: ListView(padding: const EdgeInsets.all(24), children: [
            const SizedBox(height: 40),

            // EIFM Logo Header (logo is bundled inside the app, no server needed)
            GestureDetector(
              onLongPress: () => setState(() => showServer = !showServer),
              child: Column(
                children: [
                  SizedBox(
                    height: 150,
                    width: 150,
                    child: Image.asset(
                      'assets/logo.png',
                      fit: BoxFit.contain,
                      errorBuilder: (context, error, stackTrace) => Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Icon(Icons.apartment, size: 60, color: Color(0xFF0F5A3B)),
                          Text('EIFM', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: Color(0xFF0F5A3B))),
                          Text('إيفم', style: TextStyle(color: Color(0xFF0F5A3B))),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'EIFM WCC & PPM',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF0F5A3B),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 30),
            TextField(
              controller: e,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(
                labelText: 'Email',
                prefixIcon: const Icon(Icons.email, color: Color(0xFF0F5A3B)),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: p,
              obscureText: true,
              decoration: InputDecoration(
                labelText: 'Password',
                prefixIcon: const Icon(Icons.lock, color: Color(0xFF0F5A3B)),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 12),
            if (showServer) ...[
              TextField(
                controller: sv,
                decoration: InputDecoration(
                  labelText: 'Server link',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 12),
            ],
            const SizedBox(height: 12),
            SizedBox(
              height: 50,
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF0F5A3B),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: busy ? null : () => go('login'),
                child: Text(busy ? 'Please wait...' : 'Sign in'),
              ),
            ),
            if (busy)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Server may take up to 1 minute to wake up the first time. Please wait...',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.black54),
                ),
              ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: busy ? null : () => go('signup'),
              child: const Text(
                'Create account',
                style: TextStyle(color: Color(0xFF0F5A3B), fontWeight: FontWeight.bold),
              ),
            ),
          ]),
        ),
      );
}

class Home extends StatefulWidget {
  const Home({super.key});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int i = 0;
  @override
  Widget build(BuildContext c) => Scaffold(
        appBar: AppBar(
          title: Row(children: [
            Container(
              height: 34,
              width: 34,
              padding: const EdgeInsets.all(2),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
              child: Image.asset(
                'assets/logo.png',
                fit: BoxFit.contain,
                errorBuilder: (ctx, err, st) => const Icon(Icons.apartment, size: 22, color: Color(0xFF0F5A3B)),
              ),
            ),
            const SizedBox(width: 10),
            const Flexible(child: Text('EIFM WCC & PPM', overflow: TextOverflow.ellipsis)),
          ]),
          backgroundColor: const Color(0xFF0F5A3B),
          foregroundColor: Colors.white,
          actions: [
            IconButton(
                icon: const Icon(Icons.logout),
                onPressed: () async {
                  (await SharedPreferences.getInstance()).remove('token');
                  token = null;
                  if (c.mounted) {
                    Navigator.pushAndRemoveUntil(
                        c,
                        MaterialPageRoute(builder: (_) => const Login()),
                        (_) => false);
                  }
                })
          ],
        ),
        body: IndexedStack(
            index: i,
            children: const [
              DashboardPage(),
              LibraryPage(),
              PpmPage(),
              WccPage(),
              RecordsPage()
            ]),
        bottomNavigationBar: NavigationBar(
          selectedIndex: i,
          onDestinationSelected: (v) => setState(() => i = v),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.dashboard), label: 'Home'),
            NavigationDestination(icon: Icon(Icons.apartment), label: 'Library'),
            NavigationDestination(icon: Icon(Icons.build), label: 'New PPM'),
            NavigationDestination(icon: Icon(Icons.description), label: 'New WCC'),
            NavigationDestination(icon: Icon(Icons.folder), label: 'My Records'),
          ],
        ),
      );
}
