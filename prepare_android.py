from pathlib import Path
from xml.etree import ElementTree as ET

manifest = Path('android/app/src/main/AndroidManifest.xml')
if not manifest.exists():
    raise SystemExit('Android project was not generated')
text = manifest.read_text()
permission = '<uses-permission android:name="android.permission.INTERNET" />'
if 'android.permission.INTERNET' not in text:
    text = text.replace('<application', permission + '\n    <application', 1)
# Image cropper on Android requires the native UCrop activity.
if 'com.yalantis.ucrop.UCropActivity' not in text:
    activity = '<activity android:name="com.yalantis.ucrop.UCropActivity" android:screenOrientation="portrait" android:theme="@style/Theme.AppCompat.Light.NoActionBar" />'
    text = text.replace('</application>', '    ' + activity + '\n    </application>', 1)
manifest.write_text(text)
ET.parse(manifest)
print('Android manifest permissions and image cropper activity configured')
