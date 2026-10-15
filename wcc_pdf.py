"""EIFM WCC/PPM PDF from the supplied, unchanged original PDF page."""
from pathlib import Path
from io import BytesIO
import fitz
from PIL import Image, ImageOps

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE / 'WCC_original.pdf'
LOGO = BASE / 'EIFM_logo.jpg'
PPM_TEXT = 'Planned Preventive Maintenance Service Complete as per attached Check List'

def _photo_bytes(path):
    if not path or not Path(path).is_file():
        return None
    with Image.open(path) as original:
        img = ImageOps.exif_transpose(original).convert('RGB')
        img.thumbnail((1800, 1800))
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=88)
        return buf.getvalue()

def _put_fit(page, rect, content):
    if content:
        page.insert_image(rect, stream=content, keep_proportion=True, overlay=True)

def _text(page, value, x, baseline, max_width, size=8.5, center=False):
    value = str(value or '').strip()
    if not value: return
    while size > 6 and fitz.get_text_length(value, fontname='hebo', fontsize=size) > max_width:
        size -= .25
    if center:
        x += (max_width - fitz.get_text_length(value, fontname='hebo', fontsize=size))/2
    page.insert_text((x, baseline), value, fontsize=size, fontname='hebo', color=(0,0,0), overlay=True)

def make_wcc_pdf(data, before=None, after=None, out=None, site_sig=None, hod_sig=None, client_sig=None):
    if out is None: raise ValueError('Output path required')
    ppm = data.get('mode') == 'PPM WCC'
    doc = fitz.open(str(ORIGINAL))
    page = doc[0]
    w,h = page.rect.width,page.rect.height
    # Original logo, printed lines, sections, signature labels, footer remain from original.
    # Original first-row dotted line at y~222. The text sits just above it.
    for key,x,y,width in [
        ('job',216,142,175),('client',216,158,300),('project',216,174,300),
        ('location',216,190,205),('tel',470,190,105)]:
        val=data.get(key)
        if key=='job' and ppm:
            val = f"{data.get('ppm_number','')} PPM Service {data.get('ppm_year','')}".strip()
        _text(page,val,x,y,width,8.0)
    # Move only the six Details dotted rows down slightly to leave a clear
    # heading-to-text gap, while keeping the original row count and endpoints.
    page.draw_rect(fitz.Rect(99,211,536,344),color=None,fill=(1,1,1),overlay=True)
    for yy in (241,261,281,301,321,341):
        for n in range(132):
            xx=100+n*(434/131)
            page.draw_circle(fitz.Point(xx,yy),.47,color=(.12,.12,.12),fill=(.12,.12,.12),overlay=True)
    details = PPM_TEXT if ppm else str(data.get('details') or '').strip()
    if details:
        # White-out only the typed text region immediately above first dotted row;
        # leave the original dotted rows intact. Font sits above y=~222.
        _text(page, details.splitlines()[0],100,231,434,8.5,center=ppm)
        for idx,line in enumerate(details.splitlines()[1:5],1):
            _text(page,line,100,231+20*idx,434,8.5)
    for key,x,y,width in [
        ('completion',275,357,220),('site_name',355,402,160),
        ('hod_name',355,442,160),('client_name',355,590,160)]:
        # Only overlay if matching original form's section can be located later.
        # No guessed positions: these values remain in DOCX output otherwise.
        pass
    # Signatures are confined to the original printed signature underlines.
    # Keep all other fields, dotted lines, photos and form content unchanged.
    signature_slots = [
        (site_sig,   (247, 358, 330, 376)),  # Site In Charge
        (hod_sig,    (208, 393, 325, 412)),  # HOD
        (client_sig, (185, 505, 310, 521)),  # Client Signature
        (client_sig, (145, 709, 241, 729)),  # Client Signature (bottom)
    ]
    for path, rect in signature_slots:
        content = _photo_bytes(path)
        if content:
            _put_fit(page, fitz.Rect(rect), content)
    if not ppm:
        p=doc.new_page(width=w,height=h)
        # Actual EIFM logo is displayed on the photo page, not a text placeholder.
        logo=_photo_bytes(LOGO)
        _put_fit(p,fitz.Rect(w-137,24,w-40,103),logo)
        p.insert_text((45,65),'WORK COMPLETION CERTIFICATE',fontname='hebo',fontsize=13)
        p.insert_text((45,93),'BEFORE & AFTER PHOTOGRAPHS',fontname='hebo',fontsize=11)
        p.draw_line((45,110),(w-45,110),color=(0,0,0),width=.8)
        for label,img,top in [('BEFORE',before,130),('AFTER',after,475)]:
            p.insert_text((49,top),label,fontname='hebo',fontsize=11)
            rect=fitz.Rect(48,top+12,w-48,top+318)
            p.draw_rect(rect,color=(.25,.25,.25),width=.8)
            _put_fit(p,fitz.Rect(rect.x0+7,rect.y0+7,rect.x1-7,rect.y1-7),_photo_bytes(img))
        # Original footer reproduced as PDF content (not retyped).
        p.show_pdf_page(fitz.Rect(0,800,w,h),fitz.open(str(ORIGINAL)),0,clip=fitz.Rect(0,800,w,h))
    if not ppm:
        for i, pg in enumerate(doc):
            pg.draw_rect(fitz.Rect(39,816,106,834),color=None,fill=(1,1,1),overlay=True)
            pg.insert_text((40.5,827.2),f'Page {i+1} of 2',fontname='hebo',fontsize=9.96)
    out=Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    doc.save(str(out),garbage=4,deflate=True)
    doc.close()
    return out
