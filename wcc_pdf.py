"""EIFM WCC/PPM PDF from the supplied, unchanged original PDF page."""
from pathlib import Path
from datetime import datetime
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

def _signature_bytes(path):
    """Crop blank signature-pad space; keep the actual ink close to its underline."""
    if not path or not Path(path).is_file():
        return None
    with Image.open(path) as original:
        rgba = ImageOps.exif_transpose(original).convert('RGBA')
        white = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        white.alpha_composite(rgba)
        clean = white.convert('RGB')
        ink = clean.convert('L').point(lambda px: 255 if px < 238 else 0)
        bounds = ink.getbbox()
        if not bounds:
            return None
        margin = max(2, int(min(clean.size) * .015))
        x0, y0, x1, y1 = bounds
        clean = clean.crop((max(0, x0-margin), max(0, y0-margin),
                            min(clean.width, x1+margin), min(clean.height, y1+margin)))
        output = BytesIO()
        clean.save(output, format='PNG')
        return output.getvalue()

def _put_signature(page, rect, content):
    """Fit real ink inside the existing field, 3-4 pt above its printed line."""
    if not content:
        return
    with Image.open(BytesIO(content)) as sig:
        sw, sh = sig.size
    scale = min(rect.width / sw, rect.height / sh)
    draw_w, draw_h = sw * scale, sh * scale
    x0 = rect.x0 + (rect.width - draw_w) / 2
    page.insert_image(fitz.Rect(x0, rect.y1 - draw_h, x0 + draw_w, rect.y1),
                      stream=content, keep_proportion=True, overlay=True)

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
        ('location',216,190,205),('tel',420,190,73)]:
        val=data.get(key)
        if key=='job' and ppm:
            ppm_number = str(data.get('ppm_number') or '1st PPM').strip()
            ppm_year = str(data.get('ppm_year') or data.get('fiscal_year') or datetime.now().year).strip()
            val = f'{ppm_number} Service Year {ppm_year}'
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
        if ppm:
            equipment = data.get('equipment') or []
            if isinstance(equipment, str): equipment = [e.strip() for e in equipment.split(',') if e.strip()]
            if equipment: _text(page, ', '.join(equipment), 100, 251, 434, 8, center=True)
        for idx,line in enumerate(details.splitlines()[1:5],1):
            _text(page,line,100,231+20*idx,434,8.5)
    # Write the submitted WCC fields directly above the ORIGINAL printed underlines.
    # Keep the existing signature image slots and all template elements unchanged.
    for key, x, baseline, width in [
        ('completion', 254, 354, 112),
        ('site_name', 375, 383, 60), ('site_date', 470, 383, 53),
        ('site_id', 376, 401, 119),
        ('hod_name', 377, 419, 71), ('hod_date', 483, 419, 50),
        ('hod_id', 374, 437, 106),
        ('client_name', 128, 556, 172), ('client_phone', 149, 584, 148),
    ]:
        _text(page, data.get(key), x, baseline, width, 8)
    # Fill day/month/year in the original pre-printed date slots.
    import re
    date_parts = re.findall(r'\d+', str(data.get('client_sign_date') or ''))
    if len(date_parts) >= 3:
        for piece, x, width in zip(date_parts[:3], (319, 350, 385), (18, 19, 30)):
            _text(page, piece, x, 737, width, 7.5)
    if data.get('remarks'):
        remarks = str(data['remarks']).splitlines()
        for i, line in enumerate(remarks[:3]):
            _text(page, line, 67, 689 + i*15, 448, 8)
    # Tick only selected boxes, inside the original printed rectangles.
    checks = {'LPO': (153.4, 468.3, 176.6, 478.4),
              'Invoice': (253.0, 468.3, 276.1, 478.4),
              'Delivery Note': (377.7, 468.3, 400.9, 478.4),
              'Petty Cash': (491.6, 468.3, 514.8, 478.4),
              'Material Requisition': (244.9, 494.0, 268.0, 504.1),
              'Job Completion': (390.9, 494.0, 414.0, 504.1)}
    satisfaction_boxes = {
        'Poor': (102.8, 626.4, 117.8, 636.4),
        'Satisfied': (169.2, 626.4, 184.2, 636.4),
        'Good': (253.0, 626.4, 268.0, 636.4),
        'Very Good': (325.1, 626.4, 340.1, 636.4),
        'Excellent': (419.8, 626.4, 434.8, 636.4),
    }
    def tick_inside(rect):
        x0, y0, x1, y1 = rect
        cx, cy = (x0+x1)/2, (y0+y1)/2
        # Two short strokes form a tick entirely inside the original box.
        page.draw_line((cx-3.0, cy), (cx-0.6, cy+2.1), color=(0,0,0), width=1.25, overlay=True)
        page.draw_line((cx-0.6, cy+2.1), (cx+3.5, cy-2.8), color=(0,0,0), width=1.25, overlay=True)
    selected_docs = data.get('docs') or []
    if isinstance(selected_docs, str):
        selected_docs = [s.strip() for s in selected_docs.split(',')]
    for label in selected_docs:
        if label in checks:
            tick_inside(checks[label])
    selected_satisfaction = str(data.get('satisfaction') or '').strip()
    for label, rect in satisfaction_boxes.items():
        if selected_satisfaction == label or selected_satisfaction.endswith('. ' + label):
            tick_inside(rect)
            break
    # Signatures are confined to the original printed signature underlines.
    # Keep all other fields, dotted lines, photos and form content unchanged.
    signature_slots = [
        (site_sig,   (247, 369, 330, 384)),  # 3-4 pt above Site underline
        (hod_sig,    (208, 405, 325, 420)),  # 3-4 pt above HOD underline
        (client_sig, (185, 515, 310, 529)),  # Client underline (upper)
        (client_sig, (145, 717, 241, 734)),  # Client signature line (bottom)
    ]
    for path, rect in signature_slots:
        content = _signature_bytes(path)
        if content:
            _put_signature(page, fitz.Rect(rect), content)
    if not ppm:
        p=doc.new_page(width=w,height=h)
        # The photo page has no additional logo.
        p.draw_rect(fitz.Rect(24.25,24.25,w-24.25,h-24.25),color=(0,0,0),width=.5)
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
            # Restore the original bottom border after masking the old page count.
            pg.draw_line((24.25,818.85),(572.85,818.85),color=(0,0,0),width=.5)
    out=Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    doc.save(str(out),garbage=4,deflate=True)
    doc.close()
    return out
    
