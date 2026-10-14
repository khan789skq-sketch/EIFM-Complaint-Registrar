from pathlib import Path
from io import BytesIO
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageOps

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE / 'WCC_original.pdf'
LOGO = BASE / 'EIFM_logo.jpg'

def _image(c, image_path, x, y, w, h):
    if not image_path or not Path(image_path).exists(): return
    with Image.open(image_path) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
        im.thumbnail((1600, 1600))
        iw, ih = im.size
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        c.drawImage(ImageReader(im), x+(w-dw)/2, y+(h-dh)/2, dw, dh)

def make_wcc_pdf(data, before, after, out):
    original = PdfReader(str(ORIGINAL))
    page = original.pages[0]
    w, h = float(page.mediabox.width), float(page.mediabox.height)
    # Use original PDF as the first page; overlay entries without changing its printed lines.
    src = fitz.open(str(ORIGINAL)); pg = src[0]
    lines = [s.strip() for s in str(data.get('details') or '').splitlines() if s.strip()]
    fields = [
        ('job', 180, 0), ('client', 180, 1), ('project', 180, 2),
        ('location', 180, 3), ('tel', 490, 3),
        ('completion', 260, 0),
    ]
    buff=BytesIO(); c=canvas.Canvas(buff,pagesize=(w,h));c.setFillColorRGB(0,0,0)
    def at(label, value, x, fallback_top):
        if not value:return
        matches=pg.search_for(label)
        top = matches[0].y0 if matches else fallback_top
        c.setFont('Helvetica', 9)
        c.drawString(x, h-top-10, str(value)[:70])
    at('Job Order Number',data.get('job',''),180,65)
    at('Client',data.get('client',''),180,83)
    at('Project',data.get('project',''),180,102)
    at('Location',data.get('location',''),180,121)
    at('Tel. No.',data.get('tel',''),480,121)
    at('Date & Time of Completion',data.get('completion',''),275,310)
    at('Signature of Site in Charge',data.get('site_name',''),400,340)
    at('Signature of HOD',data.get('hod_name',''),400,375)
    # Write complaint directly over the original dotted rows, keeping the rows visible.
    dotted=[]
    for line in pg.get_text('dict')['blocks']:
        if 'lines' not in line:continue
        for row in line['lines']:
            txt=''.join(span['text'] for span in row['spans'])
            if txt.count('…')>=5 or txt.count('.')>=12: dotted.append(row['bbox'][1])
    if not dotted:
        det=pg.search_for('Details of Work')
        start=det[0].y1+14 if det else 160
        dotted=[start+i*18 for i in range(6)]
    c.setFont('Helvetica',9)
    for i,t in enumerate(lines[:len(dotted)]):c.drawString(88,h-dotted[i]-9,t[:105])
    c.save();buff.seek(0)
    page.merge_page(PdfReader(buff).pages[0])
    outpdf=PdfWriter();outpdf.add_page(page)
    # Photo page with EIFM identity and the same address / version footer.
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=(w,h))
    _image(c, LOGO, w-112,h-96,72,72)
    c.setFont('Helvetica-Bold',15);c.drawCentredString(w/2,h-58,'BEFORE & AFTER PHOTOGRAPHS')
    c.setFont('Helvetica-Bold',11)
    for title,img,y in [('BEFORE',before,h-390),('AFTER',after,h-695)]:
        c.drawString(55,y+260,title)
        c.rect(55,y, w-110,250,stroke=1,fill=0)
        _image(c,img,60,y+5,w-120,240)
    c.setFont('Helvetica',8)
    c.drawCentredString(w/2,49,'P.O Box 2286, Abu Dhabi – United Arab Emirates - Tel: +971-2-6436663, Fax: +971-2-6436660')
    c.drawCentredString(w/2,37,'E-mail: eifm@eifm.ae     Website: www.eifm.ae')
    c.drawString(38,18,'Page 2 of 2');c.drawCentredString(w/2,18,'EIFMEN08');c.drawRightString(w-38,18,'Version R3')
    c.save();buf.seek(0);outpdf.add_page(PdfReader(buf).pages[0])
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('wb') as f:outpdf.write(f)
    return out
