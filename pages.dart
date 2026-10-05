import 'dart:convert';
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_cropper/image_cropper.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:signature/signature.dart';
import 'main.dart';

Future<dynamic> get(String p) async {
  final r = await http.get(Uri.parse('$api/$p'), headers: h);
  return r.statusCode == 200 ? jsonDecode(r.body) : [];
}

Future<void> shareFile(int id, String field) async {
  final r = await http.get(Uri.parse('$api/records/$id/$field'), headers: h);
  final cd = r.headers['content-disposition'] ?? '';
  final n = RegExp(r'filename="?([^";]+)').firstMatch(cd)?.group(1) ?? 'EIFM_$id';
  final f = File('${(await getTemporaryDirectory()).path}/$n')..writeAsBytesSync(r.bodyBytes);
  await Share.shareXFiles([XFile(f.path)]);
}

class F {
  final m = <String, TextEditingController>{};
  TextEditingController call(String k, [String v = '']) => m.putIfAbsent(k, () => TextEditingController(text: v));
  Map<String, String> get vals => {for (final e in m.entries) e.key: e.value.text};
}

Widget tf(F f, String k, String label, {int lines = 1, String v = ''}) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: TextField(controller: f(k, v), maxLines: lines, decoration: InputDecoration(labelText: label, border: const OutlineInputBorder())));

Widget dd(String label, List<String> o, String v, ValueChanged<String> on) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: DropdownButtonFormField<String>(
        value: o.contains(v) ? v : o.first,
        isExpanded: true,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
        items: o.map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
        onChanged: (x) => on(x!)));

String today() { final d = DateTime.now(); return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}'; }
const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const ppmNos = ['1st PPM', '2nd PPM', '3rd PPM', '4th PPM'];

// ---------- equipment select + checklist editor (OK / Not OK / Remarks / Follow-up) ----------
final taskFut = <String, Future<dynamic>>{};

class EqSelect extends StatefulWidget {
  final List<String> sel; final VoidCallback changed;
  const EqSelect(this.sel, this.changed, {super.key});
  @override State<EqSelect> createState() => _EqSelectState();
}
class _EqSelectState extends State<EqSelect> {
  late final Future<dynamic> fut = get('equipment');
  @override
  Widget build(BuildContext c) => FutureBuilder(future: fut, builder: (_, s) {
        if (!s.hasData) return const LinearProgressIndicator();
        return Wrap(spacing: 6, children: [
          for (final e in (s.data as List).cast<String>())
            FilterChip(label: Text(e), selected: widget.sel.contains(e), onSelected: (v) {
              v ? widget.sel.add(e) : widget.sel.remove(e); widget.changed();
            })
        ]);
      });
}

class EquipEditor extends StatefulWidget {
  final List<String> sel; final Map<String, Map<String, dynamic>> store;
  const EquipEditor(this.sel, this.store, {super.key});
  @override State<EquipEditor> createState() => _EEState();
}
class _EEState extends State<EquipEditor> {
  Widget row(String eq, int n, String t) {
    final m = widget.store.putIfAbsent('$eq|$n', () => {'ok': false, 'no': false, 'rem': '', 'fol': ''});
    return Card(child: Padding(padding: const EdgeInsets.all(8), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('$n. $t'),
      Row(children: [
        Checkbox(value: m['ok'], onChanged: (v) => setState(() => m['ok'] = v)), const Text('OK'),
        Checkbox(value: m['no'], onChanged: (v) => setState(() => m['no'] = v)), const Text('Not OK')]),
      TextFormField(initialValue: m['rem'], decoration: const InputDecoration(labelText: 'Remarks'), onChanged: (v) => m['rem'] = v),
      TextFormField(initialValue: m['fol'], decoration: const InputDecoration(labelText: 'Follow-up WO'), onChanged: (v) => m['fol'] = v),
    ])));
  }

  @override
  Widget build(BuildContext c) => Column(children: [
        for (final eq in widget.sel)
          ExpansionTile(initiallyExpanded: true, title: Text('📋 $eq — checklist details'), children: [
            FutureBuilder(future: taskFut.putIfAbsent(eq, () => get('tasks?equipment=${Uri.encodeComponent(eq)}')), builder: (_, s) {
              if (!s.hasData) return const LinearProgressIndicator();
              final t = (s.data as List).cast<String>();
              if (t.isEmpty) return Text('No checklist rows found for $eq.');
              return Column(children: [for (var n = 1; n <= t.length; n++) row(eq, n, t[n - 1])]);
            })
          ])
      ]);
}

List items(Map<String, Map<String, dynamic>> st) => [
      for (final e in st.entries)
        {'eq': e.key.split('|')[0], 'i': int.parse(e.key.split('|')[1]), 'ok': e.value['ok'], 'no': e.value['no'], 'rem': e.value['rem'], 'fol': e.value['fol']}
    ];

// ---------- Dashboard ----------
class DashboardPage extends StatelessWidget {
  const DashboardPage({super.key});
  @override
  Widget build(BuildContext c) => FutureBuilder(
      future: Future.wait([get('records'), get('equipment'), get('checklists')]),
      builder: (_, s) {
        if (!s.hasData) return const Center(child: CircularProgressIndicator());
        final d = s.data as List;
        Widget m(String t, int n) => Expanded(child: Card(child: Padding(padding: const EdgeInsets.all(14), child: Column(children: [Text('$n', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold)), Text(t, textAlign: TextAlign.center)]))));
        return ListView(padding: const EdgeInsets.all(16), children: [
          const Text('📋 EIFM WCC & PPM Generator', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Row(children: [m('My Records', (d[0] as List).length), m('Equipment Templates', (d[1] as List).length), m('Building Checklists', (d[2] as List).length)]),
          const SizedBox(height: 12),
          const Text('PPM = Planned Preventive Maintenance Service.'),
          const SizedBox(height: 8),
          Text('Equipment available: ${(d[1] as List).join(', ')}'),
        ]);
      });
}

// ---------- Checklist Library ----------
class LibraryPage extends StatefulWidget {
  const LibraryPage({super.key});
  @override State<LibraryPage> createState() => _LibState();
}
class _LibState extends State<LibraryPage> {
  final f = F(); String? path;
  @override
  Widget build(BuildContext c) => FutureBuilder(future: get('checklists'), builder: (_, s) => ListView(padding: const EdgeInsets.all(16), children: [
        const Text('🏢 Building Checklist Library', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const Text('Save one Excel checklist per building (any number of sheets).'),
        for (final n in (s.data as List? ?? [])) Text('• $n.xlsx'),
        const SizedBox(height: 12),
        tf(f, 'building', 'Building / Project Name'),
        OutlinedButton(onPressed: () async {
          final r = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['xlsx']);
          if (r != null) setState(() => path = r.files.single.path);
        }, child: Text(path == null ? 'Attach Excel Checklist (.xlsx)' : path!.split('/').last)),
        FilledButton(onPressed: () async {
          if (f('building').text.trim().isEmpty || path == null) return msg(c, 'Building name and Excel checklist are required.');
          final q = http.MultipartRequest('POST', Uri.parse('$api/checklists'))..headers.addAll(h);
          q.fields['building'] = f('building').text;
          q.files.add(await http.MultipartFile.fromPath('file', path!));
          await q.send();
          if (c.mounted) { msg(c, 'Saved checklist for ${f('building').text}.'); setState(() => path = null); }
        }, child: const Text('Save Building Checklist')),
      ]));
}

// ---------- New PPM ----------
class PpmPage extends StatefulWidget {
  const PpmPage({super.key});
  @override State<PpmPage> createState() => _PpmState();
}
class _PpmState extends State<PpmPage> {
  final f = F(); final sel = <String>[]; final store = <String, Map<String, dynamic>>{};
  String freq = 'Monthly', ppmNo = '1st PPM', month = months[DateTime.now().month - 1], cl = 'Use original All-3.xlsx';
  bool busy = false;

  Future<void> gen() async {
    if (f('project').text.trim().isEmpty || sel.isEmpty) return msg(context, 'Building / Project and at least one equipment are required.');
    setState(() => busy = true);
    try {
      final r = await http.post(Uri.parse('$api/ppm'), headers: {...h, 'Content-Type': 'application/json'},
          body: jsonEncode({...f.vals, 'frequency': freq, 'ppm_number': ppmNo, 'month': month, 'checklist': cl, 'equipment': sel, 'items': items(store)}));
      if (r.statusCode == 200) { refresh.value++; await shareFile(jsonDecode(r.body)['id'], 'package'); } else if (mounted) { msg(context, 'Error: ${r.body}'); }
    } catch (e) { if (mounted) msg(context, 'Error: $e'); }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext c) => FutureBuilder(future: get('checklists'), builder: (_, s) => ListView(padding: const EdgeInsets.all(16), children: [
        const Text('🛠️ New PPM', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 10),
        tf(f, 'project', 'Building / Project Name'), tf(f, 'location', 'Location'), tf(f, 'unit', 'Unit Number'),
        dd('Frequency', ['Monthly', 'Quarterly', 'Semi-Annual', 'Annual', 'Corrective / Complaint'], freq, (v) => setState(() => freq = v)),
        tf(f, 'category', 'Category'),
        tf(f, 'fiscal_year', 'Fiscal Year', v: '${DateTime.now().year}'), tf(f, 'wo', 'WO Number'),
        dd('PPM Number', ppmNos, ppmNo, (v) => setState(() => ppmNo = v)),
        dd('Scheduled Month', months, month, (v) => setState(() => month = v)),
        tf(f, 'service_date', 'Date of Service (dd/mm/yyyy)', v: today()), tf(f, 'start', 'Time Start (HH:MM)', v: '08:00'), tf(f, 'finish', 'Time Finish (HH:MM)', v: '17:00'),
        dd('Building Checklist to attach', ['Use original All-3.xlsx', 'Use original All.xlsx', for (final n in (s.data as List? ?? [])) 'Building checklist: $n'], cl, (v) => setState(() => cl = v)),
        const Text('Equipment — select ONE or MANY', style: TextStyle(fontWeight: FontWeight.bold)),
        EqSelect(sel, () => setState(() {})),
        if (sel.isEmpty) const Text('Select one or more equipment.') else EquipEditor(sel, store),
        const SizedBox(height: 10),
        tf(f, 'technician', 'Technician Name / Sign'), tf(f, 'engineer', 'Engineer / Supervisor Name / Sign'), tf(f, 'summary', 'REPORT SUMMARY', lines: 3),
        FilledButton(onPressed: busy ? null : gen, child: Text(busy ? 'Please wait...' : 'Generate PPM')),
        const SizedBox(height: 30),
      ]));
}

// ---------- New WCC ----------
SignatureController sc() => SignatureController(penStrokeWidth: 3, penColor: Colors.black, exportBackgroundColor: Colors.white);

class SigPad extends StatelessWidget {
  final String label; final SignatureController ctl;
  const SigPad(this.label, this.ctl, {super.key});
  @override
  Widget build(BuildContext c) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$label — sign with finger/stylus below'),
        Container(decoration: BoxDecoration(border: Border.all()), child: Signature(controller: ctl, height: 130, backgroundColor: Colors.white)),
        TextButton(onPressed: ctl.clear, child: const Text('Clear signature')),
      ]);
}

class WccPage extends StatefulWidget {
  const WccPage({super.key});
  @override State<WccPage> createState() => _WccState();
}
class _WccState extends State<WccPage> {
  final f = F(); final sel = <String>[]; final docs = <String>{'Job Completion'};
  final sigs = {'site_sig': sc(), 'hod_sig': sc(), 'client_sig': sc()};
  final pics = <String, File?>{'before': null, 'after': null}; final origs = <String, String>{};
  String mode = 'Normal WCC', sat = '3. Good', ppmNo = '1st PPM'; bool busy = false;

  Future<void> pick(String k) async {
    String? p = origs[k];
    if (p == null) {
      final src = await showModalBottomSheet<ImageSource>(context: context, builder: (_) => SafeArea(child: Wrap(children: [
        ListTile(leading: const Icon(Icons.photo_camera), title: const Text('Camera'), onTap: () => Navigator.pop(context, ImageSource.camera)),
        ListTile(leading: const Icon(Icons.photo_library), title: const Text('Gallery'), onTap: () => Navigator.pop(context, ImageSource.gallery))])));
      if (src == null) return;
      final x = await ImagePicker().pickImage(source: src);
      if (x == null) return;
      p = x.path; origs[k] = p;
    }
    final cr = await ImageCropper().cropImage(sourcePath: p, aspectRatio: const CropAspectRatio(ratioX: 4, ratioY: 3), maxWidth: 900, maxHeight: 675,
        uiSettings: [AndroidUiSettings(toolbarTitle: 'Adjust ${k.toUpperCase()} picture', lockAspectRatio: true)]);
    if (cr != null) setState(() => pics[k] = File(cr.path));
  }

  Widget tile(String k, String t) => Expanded(child: Column(children: [
        Text(t, style: const TextStyle(fontWeight: FontWeight.bold)),
        GestureDetector(onTap: () => pick(k), child: AspectRatio(aspectRatio: 4 / 3, child: Container(
            margin: const EdgeInsets.all(4), decoration: BoxDecoration(border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
            child: pics[k] == null ? const Icon(Icons.add_a_photo, size: 40) : Image.file(pics[k]!, fit: BoxFit.cover)))),
        if (pics[k] != null) TextButton(onPressed: () { origs.remove(k); pick(k); }, child: const Text('Change photo')),
      ]));

  Future<void> gen() async {
    final ppm = mode == 'PPM WCC';
    if (f('client').text.trim().isEmpty || f('project').text.trim().isEmpty) return msg(context, 'Client and Building / Project are required.');
    if (!ppm && (pics['before'] == null || pics['after'] == null)) return msg(context, 'Normal WCC requires both Before and After pictures.');
    if (ppm && sel.isEmpty) return msg(context, 'Select at least one equipment for the PPM WCC checklist.');
    setState(() => busy = true);
    try {
      final q = http.MultipartRequest('POST', Uri.parse('$api/wcc'))..headers.addAll(h);
      q.fields['data'] = jsonEncode({...f.vals, 'mode': mode, 'equipment': sel.join(', '), 'docs': docs.toList(), 'satisfaction': sat,
          'ppm_number': ppm ? ppmNo : null, 'ppm_year': ppm ? int.tryParse(f('ppm_year').text) : null});
      if (!ppm) {
        q.files.add(await http.MultipartFile.fromPath('before', pics['before']!.path));
        q.files.add(await http.MultipartFile.fromPath('after', pics['after']!.path));
      }
      for (final e in sigs.entries) {
        if (e.value.isNotEmpty) q.files.add(http.MultipartFile.fromBytes(e.key, (await e.value.toPngBytes())!, filename: '${e.key}.png'));
      }
      final r = await http.Response.fromStream(await q.send());
      if (r.statusCode == 200) { refresh.value++; await shareFile(jsonDecode(r.body)['id'], 'package'); } else if (mounted) { msg(context, 'Error: ${r.body}'); }
    } catch (e) { if (mounted) msg(context, 'Error: $e'); }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext c) {
    final ppm = mode == 'PPM WCC';
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Text('📄 New Work Completion Certificate', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
      const SizedBox(height: 8),
      SegmentedButton<String>(segments: const [ButtonSegment(value: 'Normal WCC', label: Text('Normal WCC')), ButtonSegment(value: 'PPM WCC', label: Text('PPM WCC'))],
          selected: {mode}, onSelectionChanged: (v) => setState(() => mode = v.first)),
      const SizedBox(height: 10),
      tf(f, 'job', 'Job Order Number'), tf(f, 'client', 'Client'), tf(f, 'project', 'Building / Project'), tf(f, 'location', 'Location'), tf(f, 'tel', 'Tel. No.'),
      const Text('Equipment — select ONE or MANY', style: TextStyle(fontWeight: FontWeight.bold)),
      EqSelect(sel, () => setState(() {})),
      const SizedBox(height: 10),
      tf(f, 'details', 'Details of Work (blank = selected equipment details auto)', lines: 4), tf(f, 'completion', 'Date & Time of Completion'),
      tf(f, 'client_name', 'Client Name'), tf(f, 'client_phone', 'Client Phone No.'),
      dd('Satisfaction', ['1. Poor', '2. Satisfied', '3. Good', '4. Very Good', '5. Excellent'], sat, (v) => setState(() => sat = v)),
      tf(f, 'client_sign_date', 'Client Signature Date'), tf(f, 'remarks', 'Remarks / Suggestions', lines: 2),
      const Text('Enclosed documents', style: TextStyle(fontWeight: FontWeight.bold)),
      Wrap(spacing: 6, children: [for (final d in ['LPO', 'Invoice', 'Delivery Note', 'Petty Cash', 'Material Requisition', 'Job Completion'])
        FilterChip(label: Text(d), selected: docs.contains(d), onSelected: (v) => setState(() => v ? docs.add(d) : docs.remove(d)))]),
      const SizedBox(height: 10),
      if (ppm) ...[
        dd('PPM Number', ppmNos, ppmNo, (v) => setState(() => ppmNo = v)), tf(f, 'ppm_year', 'PPM Service Year', v: '${DateTime.now().year}'),
      ] else ...[
        const Text('Before / After Pictures (tap = size adjust)', style: TextStyle(fontWeight: FontWeight.bold)),
        Row(children: [tile('before', 'Before'), tile('after', 'After')]),
      ],
      const Text('Signatures — actual signature, not typed text', style: TextStyle(fontWeight: FontWeight.bold)),
      SigPad('Site in Charge Signature', sigs['site_sig']!), tf(f, 'site_name', 'Site in Charge Name'), tf(f, 'site_date', 'Site Date'), tf(f, 'site_id', 'Site ID'),
      SigPad('HOD Signature', sigs['hod_sig']!), tf(f, 'hod_name', 'HOD Name'), tf(f, 'hod_date', 'HOD Date'), tf(f, 'hod_id', 'HOD ID'),
      SigPad('Client Signature', sigs['client_sig']!),
      const SizedBox(height: 10),
      FilledButton(onPressed: busy ? null : gen, child: Text(busy ? 'Please wait...' : 'Generate WCC Package')),
      const SizedBox(height: 30),
    ]);
  }
}

// ---------- My Records ----------
class RecordsPage extends StatelessWidget {
  const RecordsPage({super.key});
  @override
  Widget build(BuildContext c) => ValueListenableBuilder<int>(valueListenable: refresh, builder: (_, __, ___) => FutureBuilder(future: get('records'), builder: (_, s) {
        if (!s.hasData) return const Center(child: CircularProgressIndicator());
        final l = s.data as List;
        if (l.isEmpty) return const Center(child: Text('No records yet.'));
        return ListView(children: [for (final r in l) ExpansionTile(
            title: Text('${r['kind']} | ${r['project'] ?? '-'}'), subtitle: Text('${r['number'] ?? '-'} | ${r['created_at']}'),
            children: [
              Align(alignment: Alignment.centerLeft, child: Padding(padding: const EdgeInsets.only(left: 16), child: Text('Equipment: ${r['equipment'] ?? '-'}'))),
              Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
                TextButton.icon(onPressed: () => shareFile(r['id'], 'package'), icon: const Icon(Icons.archive), label: const Text('Package')),
                TextButton.icon(onPressed: () => shareFile(r['id'], 'file'), icon: const Icon(Icons.description), label: const Text('Main File')),
                if (r['has_cl'] == 1) TextButton.icon(onPressed: () => shareFile(r['id'], 'checklist'), icon: const Icon(Icons.attach_file), label: const Text('Checklist')),
              ])])]);
      }));
}
