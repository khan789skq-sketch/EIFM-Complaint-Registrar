import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'pages.dart';

const String kServer = 'https://eifm-wcc-api.onrender.com';
const Color kGreen = Color(0xFF0B5D3F);
String api = kServer;
String? token;
String userEmail = '';
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

// After generating a record: share the real files (Word / Excel ...) one by one.
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
  userEmail = prefs.getString('user_email') ?? '';
  final custom = prefs.getString('api_custom');
  api = (custom != null && custom.isNotEmpty) ? custom : kServer;
  wake();
  runApp(MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'EIFM',
    theme: ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: Colors.white,
      colorScheme: ColorScheme.fromSeed(seedColor: kGreen, primary: kGreen),
      appBarTheme: const AppBarTheme(
        backgroundColor: kGreen,
        foregroundColor: Colors.white,
        centerTitle: false,
        elevation: 0,
      ),
    ),
    home: const Splash(),
  ));
}

// ---------------- Wave decoration (login + splash) ----------------
class WavePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final light = Paint()..color = const Color(0x669DBFAE);
    final dark = Paint()
      ..shader = const LinearGradient(
        colors: [Color(0xFF5E9A80), kGreen],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
    final p1 = Path()
      ..moveTo(0, size.height * 0.55)
      ..quadraticBezierTo(size.width * 0.30, size.height * 0.05, size.width * 0.65, size.height * 0.30)
      ..quadraticBezierTo(size.width * 0.88, size.height * 0.48, size.width, size.height * 0.15)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    canvas.drawPath(p1, light);
    final p2 = Path()
      ..moveTo(0, size.height * 0.85)
      ..quadraticBezierTo(size.width * 0.50, size.height * 0.40, size.width, size.height * 0.62)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    canvas.drawPath(p2, dark);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ---------------- Splash screen (logo + waves), then Login or Home ----------------
class Splash extends StatefulWidget {
  const Splash({super.key});
  @override
  State<Splash> createState() => _SplashState();
}

class _SplashState extends State<Splash> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(milliseconds: 1500), () {
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => token == null ? const Login() : const Home()),
      );
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.white,
        body: Column(children: [
          Expanded(
            child: Center(
              child: SizedBox(
                height: 230,
                width: 230,
                child: Image.asset(
                  'assets/logo.png',
                  fit: BoxFit.contain,
                  errorBuilder: (ctx, err, st) => const Icon(Icons.apartment, size: 90, color: kGreen),
                ),
              ),
            ),
          ),
          SizedBox(
            height: 220,
            width: double.infinity,
            child: CustomPaint(painter: WavePainter()),
          ),
        ]),
      );
}

void openLibrary(BuildContext context) => Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text('Checklist Library')),
          body: const LibraryPage(),
        ),
      ),
    );

// ---------------- Login / Sign up ----------------
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
  bool signUp = false;
  bool hide = true;
  bool showServer = false; // long-press the logo to show/hide the server link box

  Widget _field(TextEditingController c, String hint, IconData icon,
          {bool obscure = false, Widget? suffix, TextInputType? type}) =>
      Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: const [BoxShadow(color: Color(0x1A000000), blurRadius: 10, offset: Offset(0, 3))],
        ),
        child: TextField(
          controller: c,
          obscureText: obscure,
          keyboardType: type,
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(color: Colors.black45),
            prefixIcon: Icon(icon, color: kGreen),
            suffixIcon: suffix,
            filled: true,
            fillColor: Colors.white,
            contentPadding: const EdgeInsets.symmetric(vertical: 18),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: const BorderSide(color: Color(0xFFE8EDF2)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: const BorderSide(color: Color(0xFFE8EDF2)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(16),
              borderSide: const BorderSide(color: kGreen, width: 2),
            ),
          ),
        ),
      );

  void forgot() => showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Forgot Password?', style: TextStyle(color: kGreen, fontWeight: FontWeight.bold)),
          content: const Text('Password reset by email is not available yet. Please contact your EIFM admin.'),
          actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK'))],
        ),
      );

  Future<void> go() async {
    if (e.text.trim().isEmpty || p.text.isEmpty) {
      msg(context, 'Please enter Email and Password');
      return;
    }
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
          .post(Uri.parse('$api/${signUp ? 'signup' : 'login'}'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({'email': e.text.trim(), 'password': p.text}))
          .timeout(const Duration(seconds: 90));
      final j = jsonDecode(r.body);
      if (r.statusCode == 200) {
        token = j['token'];
        userEmail = e.text.trim();
        await prefs.setString('token', token!);
        await prefs.setString('user_email', userEmail);
        if (mounted) {
          Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const Home()));
        }
        return;
      }
      if (mounted) msg(context, '${j['detail']}');
    } catch (_) {
      if (mounted) {
        msg(context, 'Internet / server error. Server may be waking up - wait 1 minute and try again.');
      }
    }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final keyboardOpen = MediaQuery.of(context).viewInsets.bottom > 0;
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(28, 28, 28, 12),
              child: Column(children: [
                GestureDetector(
                  onLongPress: () => setState(() => showServer = !showServer),
                  child: SizedBox(
                    height: 190,
                    width: 190,
                    child: Image.asset(
                      'assets/logo.png',
                      fit: BoxFit.contain,
                      errorBuilder: (ctx, err, st) => const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.apartment, size: 60, color: kGreen),
                          Text('EIFM', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: kGreen)),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    signUp ? 'Create Account' : 'Login',
                    style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                  ),
                ),
                const SizedBox(height: 6),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    signUp ? 'Register to access EIFM certificates' : 'Welcome back! Please login to your account.',
                    style: const TextStyle(fontSize: 14, color: Colors.black54),
                  ),
                ),
                const SizedBox(height: 24),
                _field(e, 'Email', Icons.person_outline, type: TextInputType.emailAddress),
                const SizedBox(height: 18),
                _field(
                  p,
                  'Password',
                  Icons.lock_outline,
                  obscure: hide,
                  suffix: IconButton(
                    icon: Icon(hide ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: Colors.black45),
                    onPressed: () => setState(() => hide = !hide),
                  ),
                ),
                if (showServer) ...[
                  const SizedBox(height: 18),
                  _field(sv, 'Server link', Icons.cloud_outlined),
                ],
                if (!signUp)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: forgot,
                      child: const Text('Forgot Password?', style: TextStyle(color: kGreen, fontWeight: FontWeight.w600)),
                    ),
                  )
                else
                  const SizedBox(height: 12),
                const SizedBox(height: 4),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: kGreen,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    onPressed: busy ? null : go,
                    child: Text(
                      busy ? 'Please wait...' : (signUp ? 'Sign Up' : 'Login'),
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                    ),
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
                const SizedBox(height: 16),
                const Row(children: [
                  Expanded(child: Divider()),
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: 12),
                    child: Text('or', style: TextStyle(color: Colors.black45)),
                  ),
                  Expanded(child: Divider()),
                ]),
                const SizedBox(height: 10),
                Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Text(
                    signUp ? 'Already have an account? ' : "Don't have an account? ",
                    style: const TextStyle(color: Colors.black54),
                  ),
                  GestureDetector(
                    onTap: () => setState(() => signUp = !signUp),
                    child: Text(
                      signUp ? 'Login' : 'Sign Up',
                      style: const TextStyle(color: kGreen, fontWeight: FontWeight.bold),
                    ),
                  ),
                ]),
              ]),
            ),
          ),
          if (!keyboardOpen)
            SizedBox(
              height: 110,
              width: double.infinity,
              child: CustomPaint(painter: WavePainter()),
            ),
        ]),
      ),
    );
  }
}

// ---------------- Home with bottom navigation ----------------
class Home extends StatefulWidget {
  const Home({super.key});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int i = 0;
  static const titles = ['Dashboard', 'New WCC', 'New PPM', 'My Records', 'More'];

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    token = null;
    if (mounted) {
      Navigator.pushAndRemoveUntil(
          context, MaterialPageRoute(builder: (_) => const Login()), (_) => false);
    }
  }

  Widget _drawerItem(BuildContext c, IconData icon, String text, VoidCallback onTap) => ListTile(
        leading: Icon(icon, color: kGreen),
        title: Text(text),
        onTap: () {
          Navigator.pop(c);
          onTap();
        },
      );

  @override
  Widget build(BuildContext c) => Scaffold(
        drawer: Drawer(
          child: ListView(padding: EdgeInsets.zero, children: [
            Container(
              color: kGreen,
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 20),
              child: Row(children: [
                Container(
                  height: 56,
                  width: 56,
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                  child: Image.asset('assets/logo.png', fit: BoxFit.contain, errorBuilder: (ctx, err, st) => const SizedBox()),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    userEmail.isEmpty ? 'EIFM User' : userEmail,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ]),
            ),
            _drawerItem(c, Icons.home_outlined, 'Dashboard', () => setState(() => i = 0)),
            _drawerItem(c, Icons.note_add_outlined, 'New WCC', () => setState(() => i = 1)),
            _drawerItem(c, Icons.build_outlined, 'New PPM', () => setState(() => i = 2)),
            _drawerItem(c, Icons.description_outlined, 'My Records', () => setState(() => i = 3)),
            _drawerItem(c, Icons.apartment, 'Checklist Library', () => openLibrary(c)),
            const Divider(),
            _drawerItem(c, Icons.logout, 'Logout', logout),
          ]),
        ),
        appBar: AppBar(
          title: Text(titles[i], style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          actions: i == 0
              ? [IconButton(icon: const Icon(Icons.notifications_none), onPressed: () => msg(c, 'No new notifications'))]
              : null,
        ),
        body: IndexedStack(
          index: i,
          children: [
            HomeDashboard((v) => setState(() => i = v)),
            const WccPage(),
            const PpmPage(),
            const RecordsPage(),
            MorePage(onLogout: logout),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: i,
          backgroundColor: Colors.white,
          indicatorColor: const Color(0x260B5D3F),
          onDestinationSelected: (v) => setState(() => i = v),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home, color: kGreen), label: 'Home'),
            NavigationDestination(icon: Icon(Icons.note_add_outlined), selectedIcon: Icon(Icons.note_add, color: kGreen), label: 'New WCC'),
            NavigationDestination(icon: Icon(Icons.build_outlined), selectedIcon: Icon(Icons.build, color: kGreen), label: 'New PPM'),
            NavigationDestination(icon: Icon(Icons.description_outlined), selectedIcon: Icon(Icons.description, color: kGreen), label: 'My Records'),
            NavigationDestination(icon: Icon(Icons.more_horiz), selectedIcon: Icon(Icons.more_horiz, color: kGreen), label: 'More'),
          ],
        ),
      );
}

// ---------------- Dashboard ----------------
class HomeDashboard extends StatelessWidget {
  final void Function(int) goTab;
  const HomeDashboard(this.goTab, {super.key});

  Widget card(IconData icon, String title, String sub, VoidCallback onTap) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFE2E8F0)),
            boxShadow: const [BoxShadow(color: Color(0x14
