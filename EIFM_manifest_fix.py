from pathlib import Path
from xml.etree import ElementTree as ET

manifest = Path('android/app/src/main/AndroidManifest.xml')
if not manifest.is_file():
    raise SystemExit('AndroidManifest.xml missing')

ANDROID = 'http://schemas.android.com/apk/res/android'
ET.register_namespace('android', ANDROID)
root = ET.parse(manifest).getroot()
if root.tag != 'manifest':
    raise SystemExit('Invalid Android manifest root')

permission_name = f'{{{ANDROID}}}name'
if not any(x.tag == 'uses-permission' and x.get(permission_name) == 'android.permission.INTERNET' for x in root):
    root.insert(0, ET.Element('uses-permission', {permission_name: 'android.permission.INTERNET'}))

app = root.find('application')
if app is None:
    raise SystemExit('Android application element missing')
app.set(f'{{{ANDROID}}}label', 'EIFM WCC & PPM')

if not any(x.get(permission_name) == 'com.yalantis.ucrop.UCropActivity' for x in app.findall('activity')):
    ET.SubElement(app, 'activity', {
        permission_name: 'com.yalantis.ucrop.UCropActivity',
        f'{{{ANDROID}}}screenOrientation': 'portrait',
        f'{{{ANDROID}}}theme': '@android:style/Theme.Material.Light.NoActionBar',
    })

ET.indent(root, space='    ')
ET.ElementTree(root).write(manifest, encoding='utf-8', xml_declaration=True)
ET.parse(manifest)
print('AndroidManifest.xml validated successfully')
