import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:image_picker/image_picker.dart';

const Color kGreen = Color(0xFF0B5D3F);
String userEmail = '';
ValueNotifier<int> refreshNotifier = ValueNotifier<int>(0);

void main() {
  runApp(const EIFMApp());
}

class EIFMApp extends StatelessWidget {
  const EIFMApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'EIFM Report & Complaint Registrar',
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
  int _currentIndex = 0;
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
      return LoginScreen(onLoginSuccess: _checkLoginStatus);
    }

    final List<Widget> pages = [
      HomeDashboard((index) => setState(() => _currentIndex = index)),
      const WccFormWizardPage(),
      const PpmFormWizardPage(),
      const RecordsPage(),
      MorePage(onLogout: logout),
    ];

    return Scaffold(
      body: pages[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        backgroundColor: Colors.white,
        indicatorColor: const Color(0x260B5D3F),
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
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
}

// ---------------- LOGIN / AUTHENTICATION ----------------
class LoginScreen extends StatefulWidget {
  final VoidCallback onLoginSuccess;
  const LoginScreen({super.key, required this.onLoginSuccess});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isSignUp = false;

  Future<void> _handleAuth() async {
    if (_emailController.text.trim().isEmpty || _passwordController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Kripya Email aur Password bharein')));
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
              Image.asset('EIFM_logo.jpg', height: 110, fit: BoxFit.contain, errorBuilder: (c, e, s) => const Icon(Icons.business, size: 80, color: kGreen)),
              const SizedBox(height: 30),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(_isSignUp ? "Create Account" : "Login", style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
              ),
              const SizedBox(height: 16),
              TextField(controller: _emailController, decoration: const InputDecoration(labelText: "Username or Email", border: OutlineInputBorder())),
              const SizedBox(height: 16),
              TextField(controller: _passwordController, obscureText: true, decoration: const InputDecoration(labelText: "Password", border: OutlineInputBorder())),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: kGreen, foregroundColor: Colors.white),
                  onPressed: _handleAuth,
                  child: Text(_isSignUp ? "Sign Up" : "Login", style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------- DASHBOARD ----------------
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
            boxShadow: const [BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 3))],
          ),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(icon, color: kGreen, size: 34),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            const SizedBox(height: 2),
            Text(sub, textAlign: TextAlign.center, style: const TextStyle(color: Colors.black54, fontSize: 11)),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: refreshNotifier,
      builder: (_, __, ___) => ListView(padding: const EdgeInsets.all(16), children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Welcome,', style: TextStyle(color: Colors.black54, fontSize: 14)),
              Text(userEmail.isEmpty ? 'EIFM User' : userEmail.split('@').first, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
            ]),
          ),
          SizedBox(height: 56, width: 56, child: Image.asset('EIFM_logo.jpg', fit: BoxFit.contain, errorBuilder: (c, e, s) => const Icon(Icons.business, color: kGreen))),
        ]),
        const SizedBox(height: 20),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.3,
          children: [
            card(Icons.note_add_outlined, 'New WCC', 'Create Certificate', () => goTab(1)),
            card(Icons.build_outlined, 'New PPM', 'PPM Service Report', () => goTab(2)),
            card(Icons.description_outlined, 'My Records', 'View Saved PDF/Excel', () => goTab(3)),
            card(Icons.settings_outlined, 'Settings', 'App Settings', () => goTab(4)),
          ],
        ),
        const SizedBox(height: 24),
        const Text('Recent Activity', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        const SavedRecordsListWidget(limit: 3),
      ]),
    );
  }
}

// ---------------- WCC FORM WIZARD (WITH BEFORE/AFTER PICTURES) ----------------
class WccFormWizardPage extends StatefulWidget {
  const WccFormWizardPage({super.key});

  @override
  State<WccFormWizardPage> createState() => _WccFormWizardPageState();
}

class _WccFormWizardPageState extends State<WccFormWizardPage> {
  final _projectNameController = TextEditingController();
  final _contractNoController = TextEditingController();
  String? _beforeImagePath;
  String? _afterImagePath;

  final ImagePicker _picker = ImagePicker();

  Future<void> _pickImage(bool isBefore) async {
    final XFile? photo = await _picker.pickImage(source: ImageSource.camera);
    if (photo != null) {
      setState(() {
        if (isBefore) {
          _beforeImagePath = photo.path;
        } else {
          _afterImagePath = photo.path;
        }
      });
    }
  }

  Future<void> _saveWccReport() async {
    if (_projectNameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Project Name likhna zaroori hai')));
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    List<String> records = prefs.getStringList('saved_reports') ?? [];

    Map<String, dynamic> report = {
      'type': 'WCC',
      'title': _projectNameController.text,
      'contractNo': _contractNoController.text,
      'date': DateTime.now().toString().split(' ')[0],
      'beforeImage': _beforeImagePath ?? '',
      'afterImage': _afterImagePath ?? '',
    };

    records.add(jsonEncode(report));
    await prefs.setStringList('saved_reports', records);

    refreshNotifier.value++;
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('WCC Report Safe Saved!')));

    _projectNameController.clear();
    _contractNoController.clear();
    setState(() {
      _beforeImagePath = null;
      _afterImagePath = null;
    });
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
            TextField(controller: _projectNameController, decoration: const InputDecoration(labelText: 'Project Name *', border: OutlineInputBorder())),
            const SizedBox(height: 12),
            TextField(controller: _contractNoController, decoration: const InputDecoration(labelText: 'Contract Number', border: OutlineInputBorder())),
            const SizedBox(height: 20),
            const Text('Work Pictures (Before & After)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: kGreen),
                    onPressed: () => _pickImage(true),
                    icon: const Icon(Icons.camera_alt),
                    label: Text(_beforeImagePath == null ? 'Before Pic' : 'Captured ✓'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: kGreen),
                    onPressed: () => _pickImage(false),
                    icon: const Icon(Icons.camera_alt),
                    label: Text(_afterImagePath == null ? 'After Pic' : 'Captured ✓'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 30),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: kGreen, foregroundColor: Colors.white),
                onPressed: _saveWccReport,
                child: const Text('Save & Export WCC Report', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------- PPM FORM WIZARD ----------------
class PpmFormWizardPage extends StatelessWidget {
  const PpmFormWizardPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New PPM Service Report')),
      body: const Center(child: Text('PPM Checklist & Maintenance Details')),
    );
  }
}

// ---------------- MY RECORDS (EXCEL / PDF SAVED FILES) ----------------
class RecordsPage extends StatelessWidget {
  const RecordsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Saved Reports')),
      body: const Padding(
        padding: EdgeInsets.all(16.0),
        child: SavedRecordsListWidget(),
      ),
    );
  }
}

class SavedRecordsListWidget extends StatelessWidget {
  final int? limit;
  const SavedRecordsListWidget({super.key, this.limit});

  Future<List<Map<String, dynamic>>> _loadRecords() async {
    final prefs = await SharedPreferences.getInstance();
    List<String> records = prefs.getStringList('saved_reports') ?? [];
    List<Map<String, dynamic>> parsedList = records.map((r) => jsonDecode(r) as Map<String, dynamic>).toList();
    if (limit != null && parsedList.length > limit!) {
      return parsedList.reversed.take(limit!).toList();
    }
    return parsedList.reversed.toList();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _loadRecords(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        final list = snapshot.data!;
        if (list.isEmpty) return const Center(child: Text('Koi report save nahi hai.'));

        return ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: list.length,
          itemBuilder: (context, index) {
            final item = list[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                leading: const Icon(Icons.picture_as_pdf, color: kGreen),
                title: Text(item['title'] ?? 'Report', style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text('Type: ${item['type']} | Date: ${item['date']}'),
                trailing: const Icon(Icons.download, color: kGreen),
              ),
            );
          },
        );
      },
    );
  }
}

// ---------------- MORE / SETTINGS ----------------
class MorePage extends StatelessWidget {
  final VoidCallback onLogout;
  const MorePage({super.key, required this.onLogout});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        ListTile(
          leading: const Icon(Icons.person, color: kGreen),
          title: Text(userEmail.isEmpty ? 'Logged User' : userEmail),
          subtitle: const Text('Account Persistent'),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.logout, color: Colors.red),
          title: const Text('Logout'),
          onTap: onLogout,
        ),
      ],
    );
  }
}
