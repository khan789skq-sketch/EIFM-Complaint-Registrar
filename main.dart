import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:excel/excel.dart' as ex;

const Color kGreen = Color(0xFF0B5D3F);
String userEmail = '';
ValueNotifier<int> refreshNotifier = ValueNotifier<int>(0);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
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
      return GreenEIFMLoginScreen(onLoginSuccess: _checkLoginStatus);
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

// ---------------- LOGIN SCREEN ----------------
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
    if (_emailController.text.trim().isEmpty || _passwordController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please enter Username/Email and Password')));
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
              Image.asset('EIFM_logo.jpg', height: 120, fit: BoxFit.contain, errorBuilder: (c, e, s) => const Icon(Icons.business, size: 70, color: kGreen)),
              const SizedBox(height: 30),
              Align(alignment: Alignment.centerLeft, child: Text(_isSignUp ? "Create Account" : "Login", style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)))),
              const SizedBox(height: 16),
              TextField(controller: _emailController, decoration: const InputDecoration(labelText: "Username or Email", prefixIcon: Icon(Icons.person_outline, color: kGreen), border: OutlineInputBorder())),
              const SizedBox(height: 16),
              TextField(controller: _passwordController, obscureText: true, decoration: const InputDecoration(labelText: "Password", prefixIcon: Icon(Icons.lock_outline, color: kGreen), border: OutlineInputBorder())),
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
              Text(userEmail.isEmpty ? 'EIFM User' : userEmail.split('@').first, style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
            ]),
          ),
          SizedBox(height: 56, width: 56, child: Image.asset('EIFM_logo.jpg', fit: BoxFit.contain, errorBuilder: (c, e, s) => const Icon(Icons.business, color: kGreen))),
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
            card(Icons.note_add_outlined, 'New WCC', 'Create New Certificate', () => goTab(1)),
            card(Icons.manage_search, 'My WCCs', 'View All Certificates', () => goTab(3)),
            card(Icons.file_download_outlined, 'Export', 'Share Excel / Word files', () => goTab(3)),
            card(Icons.settings_outlined, 'Settings', 'App Settings', () => goTab(4)),
            card(Icons.build_outlined, 'New PPM', 'Create PPM Service Report', () => goTab(2)),
            card(Icons.apartment, 'Library', 'Building Checklists', () => goTab(4)),
          ],
        ),
        const SizedBox(height: 20),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          const Text('Recent Activity', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          TextButton(onPressed: () => goTab(3), child: const Text('View All', style: TextStyle(color: kGreen))),
        ]),
        const SavedReportsListWidget(limit: 3),
      ]),
    );
  }
}

// ---------------- WCC FORM WIZARD WITH REAL BEFORE/AFTER PICTURES & PDF/EXCEL EXPORT ----------------
class WccPage extends StatefulWidget {
  const WccPage({super.key});

  @override
  State<WccPage> createState() => _WccPageState();
}

class _WccPageState extends State<WccPage> {
  final _projController = TextEditingController();
  final _contractController = TextEditingController();
  final _employerController = TextEditingController();
  final _contractorController = TextEditingController();
  
  File? _beforeImage;
  File? _afterImage;
  final ImagePicker _picker = ImagePicker();

  Future<void> _takePhoto(bool isBefore) async {
    final XFile? photo = await _picker.pickImage(source: ImageSource.camera, imageQuality: 80);
    if (photo != null) {
      setState(() {
        if (isBefore) {
          _beforeImage = File(photo.path);
        } else {
          _afterImage = File(photo.path);
        }
      });
    }
  }

  Future<void> _generatePdfAndExcel() async {
    if (_projController.text.isEmpty || _contractController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Kripya Project Name aur Contract No. bharein')));
      return;
    }

    // 1. Generate Real PDF Document
    final pdf = pw.Document();
    pw.MemoryImage? beforePwImg;
    pw.MemoryImage? afterPwImg;

    if (_beforeImage != null) {
      beforePwImg = pw.MemoryImage(_beforeImage!.readAsBytesSync());
    }
    if (_afterImage != null) {
      afterPwImg = pw.MemoryImage(_afterImage!.readAsBytesSync());
    }

    pdf.addPage(
      pw.Page(
        pageFormat: PdfPageFormat.a4,
        build: (pw.Context context) {
          return pw.Column(
            cross: pw.CrossAxisAlignment.start,
            children: [
              pw.Text('EIFM - Work Completion Certificate', style: pw.TextStyle(fontSize: 22, fontWeight: pw.FontWeight.bold, color: PdfColors.green900)),
              pw.SizedBox(height: 10),
              pw.Divider(),
              pw.SizedBox(height: 10),
              pw.Text('Project Name: ${_projController.text}', style: const pw.TextStyle(fontSize: 14)),
              pw.Text('Contract No: ${_contractController.text}', style: const pw.TextStyle(fontSize: 14)),
              pw.Text('Employer: ${_employerController.text}', style: const pw.TextStyle(fontSize: 14)),
              pw.Text('Contractor: ${_contractorController.text}', style: const pw.TextStyle(fontSize: 14)),
              pw.SizedBox(height: 20),
              pw.Text('Work Execution Photos:', style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold)),
              pw.SizedBox(height: 10),
              pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                children: [
                  if (beforePwImg != null) pw.Column(children: [pw.Text('Before Work'), pw.SizedBox(height: 5), pw.Image(beforePwImg, width: 200, height: 150)]),
                  if (afterPwImg != null) pw.Column(children: [pw.Text('After Work'), pw.SizedBox(height: 5), pw.Image(afterPwImg, width: 200, height: 150)]),
                ],
              ),
            ],
          );
        },
      ),
    );

    // 2. Generate Real Excel Document
    var excel = ex.Excel.createExcel();
    ex.Sheet sheetObject = excel['WCC_Report'];
    excel.setDefaultSheet('WCC_Report');

    sheetObject.appendRow([ex.TextCellValue('EIFM WORK COMPLETION CERTIFICATE')]);
    sheetObject.appendRow([ex.TextCellValue('Project Name'), ex.TextCellValue(_projController.text)]);
    sheetObject.appendRow([ex.TextCellValue('Contract No'), ex.TextCellValue(_contractController.text)]);
    sheetObject.appendRow([ex.TextCellValue('Employer'), ex.TextCellValue(_employerController.text)]);
    sheetObject.appendRow([ex.TextCellValue('Contractor'), ex.TextCellValue(_contractorController.text)]);

    final directory = await getApplicationDocumentsDirectory();
    final excelPath = "${directory.path}/WCC_${DateTime.now().millisecondsSinceEpoch}.xlsx";
    List<int>? fileBytes = excel.save();
    if (fileBytes != null) {
      File(excelPath)
        ..createSync(recursive: true)
        ..writeAsBytesSync(fileBytes);
    }

    // Save Record to Local SharedPreferences
    final prefs = await SharedPreferences.getInstance();
    List<String> list = prefs.getStringList('saved_reports') ?? [];
    Map<String, dynamic> record = {
      'type': 'WCC',
      'project': _projController.text,
      'contract': _contractController.text,
      'excelPath': excelPath,
      'date': DateTime.now().toString().split(' ')[0],
    };
    list.add(jsonEncode(record));
    await prefs.setStringList('saved_reports', list);

    refreshNotifier.value++;

    // Open PDF Preview & Print
    await Printing.layoutPdf(onLayout: (PdfPageFormat format) async => pdf.save());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New WCC Certificate')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(controller: _projController, decoration: const InputDecoration(labelText: 'Project Name *', border: OutlineInputBorder())),
            const SizedBox(height: 12),
            TextField(controller: _contractController, decoration: const InputDecoration(labelText: 'Contract Number *', border: OutlineInputBorder())),
            const SizedBox(height: 12),
            TextField(controller: _employerController, decoration: const InputDecoration(labelText: 'Employer', border: OutlineInputBorder())),
            const SizedBox(height: 12),
            TextField(controller: _contractorController, decoration: const InputDecoration(labelText: 'Contractor', border: OutlineInputBorder())),
            const SizedBox(height: 20),
            const Text('Work Completion Pictures', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: kGreen),
                    onPressed: () => _takePhoto(true),
                    icon: const Icon(Icons.camera_alt),
                    label: Text(_beforeImage == null ? 'Before Photo' : 'Captured ✓'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: kGreen),
                    onPressed: () => _takePhoto(false),
                    icon: const Icon(Icons.camera_alt),
                    label: Text(_afterImage == null ? 'After Photo' : 'Captured ✓'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: kGreen, foregroundColor: Colors.white),
                onPressed: _generatePdfAndExcel,
                child: const Text('Save & Export PDF / Excel Report', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
            )
          ],
        ),
      ),
    );
  }
}

// ---------------- PPM FORM PAGE ----------------
class PpmPage extends StatelessWidget {
  const PpmPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New PPM Service Report')),
      body: const Center(child: Text('PPM Service Checklists & Maintenance Logs')),
    );
  }
}

// ---------------- MY RECORDS (REAL LOCAL REPORT RETENTION) ----------------
class RecordsPage extends StatelessWidget {
  const RecordsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Saved Reports & Exports')),
      body: const Padding(
        padding: EdgeInsets.all(16.0),
        child: SavedReportsListWidget(),
      ),
    );
  }
}

class SavedReportsListWidget extends StatelessWidget {
  final int? limit;
  const SavedReportsListWidget({super.key, this.limit});

  Future<List<Map<String, dynamic>>> _getReports() async {
    final prefs = await SharedPreferences.getInstance();
    List<String> list = prefs.getStringList('saved_reports') ?? [];
    List<Map<String, dynamic>> parsed = list.map((e) => jsonDecode(e) as Map<String, dynamic>).toList();
    if (limit != null && parsed.length > limit!) {
      return parsed.reversed.take(limit!).toList();
    }
    return parsed.reversed.toList();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _getReports(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        final reports = snapshot.data!;
        if (reports.isEmpty) return const Center(child: Text('No saved reports found.'));

        return ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: reports.length,
          itemBuilder: (context, index) {
            final item = reports[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                leading: const Icon(Icons.picture_as_pdf, color: kGreen),
                title: Text(item['project'] ?? 'WCC Report', style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text('Contract: ${item['contract']} | Date: ${item['date']}'),
                trailing: const Icon(Icons.file_download_outlined, color: kGreen),
              ),
            );
          },
        );
      },
    );
  }
}

// ---------------- MORE & SETTINGS PAGE ----------------
class MorePage extends StatelessWidget {
  final Vo
