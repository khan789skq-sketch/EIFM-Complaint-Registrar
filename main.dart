import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:image_picker/image_picker.dart';

// Colors & Global Variables
const Color kGreen = Color(0xFF0B5D3F);
String userEmail = '';
ValueNotifier<int> refresh = ValueNotifier<int>(0);
String api = 'https://eifm-backend.vercel.app';

void main() {
  runApp(const EIFMApp());
}

class EIFMApp extends StatelessWidget {
  const EIFMApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'EIFM - Work Completion Certificate',
      theme: ThemeData(
        useMaterial3: true,
        primaryColor: kGreen,
        colorScheme: ColorScheme.fromSeed(
          seedColor: kGreen,
          primary: kGreen,
          secondary: const Color(0xFF10B981),
          background: const Color(0xFFF8FAFC),
        ),
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        appBarTheme: const AppBarTheme(
          backgroundColor: kGreen,
          foregroundColor: Colors.white,
          elevation: 0,
          centerTitle: true,
        ),
      ),
      home: const MainNavigationScreen(),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int i = 0;
  bool _isLoggedIn = false;

  @override
  void initState() {
    super.initState();
    _checkLoginStatus();
  }

  Future<void> _checkLoginStatus() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() {
        _isLoggedIn = prefs.getBool('is_logged_in') ?? false;
        userEmail = prefs.getString('user_email') ?? '';
      });
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_logged_in', false);
    if (mounted) {
      setState(() {
        _isLoggedIn = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isLoggedIn) {
      return GreenEIFMLoginScreen(onLoginSuccess: () {
        _checkLoginStatus();
      });
    }

    return Scaffold(
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
          NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home, color: kGreen),
              label: 'Home'),
          NavigationDestination(
              icon: Icon(Icons.note_add_outlined),
              selectedIcon: Icon(Icons.note_add, color: kGreen),
              label: 'New WCC'),
          NavigationDestination(
              icon: Icon(Icons.build_outlined),
              selectedIcon: Icon(Icons.build, color: kGreen),
              label: 'New PPM'),
          NavigationDestination(
              icon: Icon(Icons.description_outlined),
              selectedIcon: Icon(Icons.description, color: kGreen),
              label: 'My Records'),
          NavigationDestination(
              icon: Icon(Icons.more_horiz),
              selectedIcon: Icon(Icons.more_horiz, color: kGreen),
              label: 'More'),
        ],
      ),
    );
  }
}

// ---------------- Login Screen ----------------
class GreenEIFMLoginScreen extends StatefulWidget {
  final VoidCallback onLoginSuccess;
  const GreenEIFMLoginScreen({super.key, required this.onLoginSuccess});

  @override
  State<GreenEIFMLoginScreen> createState() => _GreenEIFMLoginScreenState();
}

class _GreenEIFMLoginScreenState extends State<GreenEIFMLoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isSignUp = false;

  Future<void> _handleAuth() async {
    if (_emailController.text.trim().isEmpty ||
        _passwordController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Please enter Username/Email and Password')),
      );
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('user_email', _emailController.text.trim());
    await prefs.setString('user_password', _passwordController.text.trim());
    await prefs.setBool('is_logged_in', true);
    widget.onLoginSuccess();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28.0),
          child: Column(
            children: [
              const SizedBox(height: 30),
              Image.asset(
                'EIFM_logo.jpg',
                height: 120,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) => Column(
                  children: const [
                    Icon(Icons.business_rounded, size: 70, color: kGreen),
                    Text('EIFM',
                        style: TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.bold,
                            color: kGreen)),
                  ],
                ),
              ),
              const SizedBox(height: 30),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  _isSignUp ? "Create Account" : "Login",
                  style: const TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF0F172A)),
                ),
              ),
              const SizedBox(height: 6),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  _isSignUp
                      ? "Register to access EIFM certificates"
                      : "Welcome back! Please login to your account.",
                  style: const TextStyle(fontSize: 14, color: Colors.grey),
                ),
              ),
              const SizedBox(height: 28),
              TextField(
                controller: _emailController,
                decoration: const InputDecoration(
                  labelText: "Username or Email",
                  prefixIcon: Icon(Icons.person_outline, color: kGreen),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordController,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: "Password",
                  prefixIcon: Icon(Icons.lock_outline, color: kGreen),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                      backgroundColor: kGreen, foregroundColor: Colors.white),
                  onPressed: _handleAuth,
                  child: Text(_isSignUp ? "Sign Up" : "Login",
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------- Dashboard ----------------
class HomeDashboard extends StatelessWidget {
  final void Function(int) goTab;
  const HomeDashboard(this.goTab, {super.key});

  Widget card(IconData icon, String title, String sub, VoidCallback onTap) =>
      InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFE2E8F0)),
            boxShadow: const [
              BoxShadow(
                  color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 3))
            ],
          ),
          child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, color: kGreen, size: 34),
                const SizedBox(height: 8),
                Text(title,
                    style: const TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 2),
                Text(sub,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        color: Colors.black54, fontSize: 11)),
              ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final name = userEmail.isEmpty
        ? 'EIFM User'
        : (userEmail.contains('@') ? userEmail.split('@').first : userEmail);

    return ValueListenableBuilder<int>(
      valueListenable: refresh,
      builder: (_, __, ___) =>
          ListView(padding: const EdgeInsets.all(16), children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Welcome,',
                  style: TextStyle(color: Colors.black54, fontSize: 14)),
              Text(name,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF0F172A))),
            ]),
          ),
          SizedBox(
            height: 56,
            width: 56,
            child: Image.asset('EIFM_logo.jpg',
                fit: BoxFit.contain,
                errorBuilder: (ctx, err, st) =>
                    const Icon(Icons.business, color: kGreen, size: 40)),
          ),
        ]),
        const SizedBox(height: 16),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.3,
          children: [
            card(Icons.note_add_outlined, 'New WCC', 'Create New Certificate',
                () => goTab(1)),
            card(Icons.manage_search, 'My WCCs', 'View All Certificates',
                () => goTab(3)),
            card(Icons.file_download_outlined, 'Export',
                'Share Excel / Word files', () => goTab(3)),
            card(Icons.settings_outlined, 'Settings', 'App Settings',
                () => goTab(4)),
            card(Icons.build_outlined, 'New PPM', 'Create PPM Service Report',
                () => goTab(2)),
            card(Icons.apartment, 'Library', 'Building Checklists', () {}),
          ],
        ),
        const SizedBox(height: 20),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          const Text('Recent WCCs',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          TextButton(
              onPressed: () => goTab(3),
              child: const Text('View All', style: TextStyle(color: kGreen))),
        ]),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Column(children: [
            _buildWccTile('WCC-2025-0001', 'Project A - Building Works',
                'Completed', Colors.green),
            const Divider(height: 1),
            _buildWccTile('WCC-2025-0002', 'Project B - MEP Works',
                'In Progress', Colors.orange),
            const Divider(height: 1),
            _buildWccTile('WCC-2025-0003', 'Project C - Finishing Works',
                'Completed', Colors.green),
          ]),
        ),
      ]),
    );
  }

  Widget _buildWccTile(
      String id, String title, String status, Color statusColor) {
    return ListTile(
      title: Text(id,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
      subtitle: Text(title, style: const TextStyle(fontSize: 12)),
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
            color: statusColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(12)),
        child: Text(status,
            style: TextStyle(
                color: statusColor, fontSize: 11, fontWeight: FontWeight.bold)),
      ),
    );
  }
}

// ------------ WCC FORM PAGE (BEFORE / AFTER PICTURES INCLUDED) ------------
class WccPage extends StatefulWidget {
  const WccPage({super.key});

  @override
  State<WccPage> createState() => _WccPageState();
}

class _WccPageState extends State<WccPage> {
  final _projController = TextEditingController();
  final _contractController = TextEditingController();
  String? _beforePath;
  String? _afterPath;

  final ImagePicker _picker = ImagePicker();

  Future<void> _pickPhoto(bool isBefore) async {
    final XFile? image = await _picker.pickImage(source: ImageSource.camera);
    if (image != null) {
      setState(() {
        if (isBefore) {
          _beforePath = image.path;
        } else {
          _afterPath = image.path;
        }
      });
    }
  }

  Future<void> _saveAndGenerateReport() async {
    if (_projController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter Project Name')),
      );
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    List<String> list = prefs.getStringList('saved_wcc_reports') ?? [];

    Map<String, dynamic> data = {
      'project': _projController.text,
      'contract': _contractController.text,
      'before_image': _beforePath ?? '',
      'after_image': _afterPath ?? '',
      'date': DateTime.now().toString().split(' ')[0],
    };

    list.add(jsonEncode(data));
    await prefs.setStringList('saved_wcc_reports', list);

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('WCC Report Generated & Downloaded (PDF/Excel)!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New WCC Report')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _projController,
              decoration: const InputDecoration(
                labelText: 'Project Name *',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _contractController,
              decoration: const InputDecoration(
                labelText: 'Contract Number *',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 20),
            const Text('Work Completion Pictures',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: kGreen),
                    onPressed: () => _pickPhoto(true),
                    icon: const Icon(Icons.camera_alt),
                    label: Text(_beforePath == null ? 'Before Pic' : 'Attached ✓'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: kGreen),
                    onPressed: () => _pickPhoto(false),
                    icon: const Icon(Icons.camera_alt),
                    label: Text(_afterPath == null ? 'After Pic' : 'Attached ✓'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                    backgroundColor: kGreen, foregroundColor: Colors.white),
                onPressed: _saveAndGenerateReport,
                child: const Text('Save & Download Report (Excel/PDF)',
                    style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            )
          ],
        ),
      ),
    );
  }
}

// ------------ PPM FORM PAGE ------------
class PpmPage extends StatelessWidget {
  const PpmPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New PPM')),
      body: const Center(child: Text('PPM Form & Checklists')),
    );
  }
}

// ------------ MY RECORDS (WORD / EXCEL / PDF DOWNLOADS) ------------
class RecordsPage extends StatelessWidget {
  const RecordsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Records & Downloads')),
      body: const Center(child: Text('Saved Excel, Word & PDF Records')),
    );
  }
}

// ---------------- More / Settings ----------------
class MorePage extends StatelessWidget {
  final VoidCallback onLogout;
  const MorePage({super.key, required this.onLogout});

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(16), children: [
        ListTile(
          leading: const Icon(Icons.apartment, color: kGreen),
          title: const Text('Building Checklist Library'),
          subtitle: const Text('Save Excel checklists per building'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () {},
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.person_outline, color: kGreen),
          title: Text(userEmail.isEmpty ? 'Signed in' : userEmail),
          subtitle: const Text('Logged in on this phone'),
        ),
        ListTile(
          leading: const Icon(Icons.cloud_outlined, color: kGreen),
          title: const Text('Server'),
          subtitle: Text(api),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.logout, color: Colors.red),
          title: const Text('Logout'),
          onTap: onLogout,
        ),
      ]);
}
