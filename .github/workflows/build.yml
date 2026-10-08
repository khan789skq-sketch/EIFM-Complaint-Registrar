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

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  token = prefs.getString('token');
  final custom = prefs.getString('api_custom');
  api = (custom != null && custom.isNotEmpty) ? custom : kServer;
  runApp(MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
    home: token == null ? const Login() : const Home(),
  ));
}

class Login extends StatefulWidget {
  const Login({super.key});
  @override
  State<Login> createState() => _LoginState();
}

class _LoginState extends State<Login> {
  final e = TextEditingController(), p = TextEditingController(), sv = TextEditingController(text: api);
  bool busy = false;
  bool showServer = false; // hidden: long-press the title to show/hide the server link box

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
          Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const Home()));
        }
        return;
      }
      if (mounted) msg(context, '${j['detail']}');
    } catch (_) {
      if (mounted) msg(context, 'Internet / server error. Server may be waking up - wait 1 minute and try again.');
    }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: ListView(padding: const EdgeInsets.all(24), children: [
            const SizedBox(height: 60),
            GestureDetector(
              onLongPress: () => setState(() => showServer = !showServer),
              child: const Text('EIFM WCC & PPM', textAlign: TextAlign.center, style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 30),
            TextField(controller: e, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder())),
            const SizedBox(height: 12),
            TextField(controller: p, obscureText: true, decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder())),
            const SizedBox(height: 12),
            if (showServer) ...[
              TextField(controller: sv, decoration: const InputDecoration(labelText: 'Server link', border: OutlineInputBorder())),
              const SizedBox(height: 12),
            ],
            const SizedBox(height: 8),
            FilledButton(onPressed: busy ? null : () => go('login'), child: Text(busy ? 'Please wait...' : 'Sign in')),
            TextButton(onPressed: busy ? null : () => go('signup'), child: const Text('Create account')),
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
        appBar: AppBar(title: const Text('EIFM WCC & PPM'), actions: [
          IconButton(
              icon: const Icon(Icons.logout),
              onPressed: () async {
                (await SharedPreferences.getInstance()).remove('token');
                token = null;
                if (c.mounted) {
                  Navigator.pushAndRemoveUntil(c, MaterialPageRoute(builder: (_) => const Login()), (_) => false);
                }
              })
        ]),
        body: IndexedStack(index: i, children: const [DashboardPage(), LibraryPage(), PpmPage(), WccPage(), RecordsPage()]),
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
