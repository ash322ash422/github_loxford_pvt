#!/usr/bin/env python3
"""Handwritten Notes Generator v1.2
Markdown / text-PDF -> ruled notebook PNG/JPG.
Preserves Markdown **bold**, uses exact baseline anchors, and adds subtle natural variation.
"""
from __future__ import annotations
import argparse, random, re
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
try:
    import pymupdf
except ImportError:
    pymupdf = None

@dataclass
class Run:
    text: str
    bold: bool = False

@dataclass
class Block:
    kind: str
    runs: list[Run]
    level: int = 0
    indent: int = 0
    checked: bool | None = None

@dataclass
class Config:
    width:int=1240; height:int=1754; left_margin:int=145; right_margin:int=80
    top_margin:int=95; bottom_margin:int=80; rule_gap:int=48
    body_size:int=34; heading_size:int=40; seed:int=42
    ink:tuple=(25,60,165); paper:tuple=(247,244,235); rule:tuple=(164,196,224)
    margin_rule:tuple=(214,126,133); texture:bool=True; binder_holes:bool=True
    # The visible bottoms of most letters should sit just above the blue rule.
    baseline_lift:int=2
    # Natural variation is intentionally sub-pixel/small so alignment remains exact.
    max_x_jitter:float=0.55
    max_baseline_jitter:float=0.35

INLINE_TOKEN = re.compile(r'(\*\*.+?\*\*)')

def parse_inline(s:str)->list[Run]:
    """Preserve **bold** while cleaning a small Markdown subset."""
    s=re.sub(r'!\[([^]]*)\]\([^)]*\)',r'[Image: \1]',s)
    s=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',s)
    parts=INLINE_TOKEN.split(s)
    runs=[]
    for part in parts:
        if not part: continue
        bold=part.startswith('**') and part.endswith('**') and len(part)>=4
        t=part[2:-2] if bold else part
        t=re.sub(r'(`{1,3}|__|~~|(?<!\*)\*(?!\*))','',t)
        if t: runs.append(Run(t,bold))
    return runs or [Run('')]

def plain(runs): return ''.join(r.text for r in runs)

def parse_markdown(text):
    blocks=[]; para=[]; code=[]; in_code=False
    def flush():
        if para:
            blocks.append(Block('paragraph',parse_inline(' '.join(x.strip() for x in para))))
            para.clear()
    for raw in text.replace('\r','').split('\n'):
        line=raw.rstrip()
        if line.strip().startswith('```'):
            flush()
            if in_code: blocks.append(Block('code',[Run('\n'.join(code))])); code.clear()
            in_code=not in_code; continue
        if in_code: code.append(line); continue
        if not line.strip(): flush(); blocks.append(Block('spacer',[])); continue
        m=re.match(r'^(#{1,6})\s+(.+)$',line)
        if m: flush(); blocks.append(Block('heading',parse_inline(m.group(2)),len(m.group(1)))); continue
        m=re.match(r'^(\s*)[-*+]\s+\[([ xX])\]\s+(.+)$',line)
        if m: flush(); blocks.append(Block('task',parse_inline(m.group(3)),indent=len(m.group(1))//2,checked=m.group(2).lower()=='x')); continue
        m=re.match(r'^(\s*)[-*+]\s+(.+)$',line)
        if m: flush(); blocks.append(Block('bullet',parse_inline(m.group(2)),indent=len(m.group(1))//2)); continue
        m=re.match(r'^(\s*)\d+[.)]\s+(.+)$',line)
        if m: flush(); blocks.append(Block('numbered',parse_inline(m.group(2)),indent=len(m.group(1))//2)); continue
        m=re.match(r'^>\s?(.*)$',line)
        if m: flush(); blocks.append(Block('quote',parse_inline(m.group(1)))); continue
        if re.match(r'^\s*([-*_])(?:\s*\1){2,}\s*$',line): flush(); blocks.append(Block('rule',[])); continue
        para.append(line)
    flush()
    out=[]
    for b in blocks:
        if b.kind=='spacer' and (not out or out[-1].kind=='spacer'): continue
        out.append(b)
    return out

def extract_pdf(path):
    if pymupdf is None: raise RuntimeError('PDF input requires PyMuPDF')
    out=[]
    with pymupdf.open(path) as doc:
        for page in doc:
            for line in page.get_text('text',sort=True).splitlines():
                line=' '.join(line.split())
                if not line: continue
                if len(line)<=70 and (line.endswith(':') or line.isupper()): out.append(Block('heading',[Run(line.rstrip(':'))],2))
                elif re.match(r'^[•●▪*-]\s+',line): out.append(Block('bullet',[Run(re.sub(r'^[•●▪*-]\s+','',line))]))
                elif re.match(r'^\d+[.)]\s+',line): out.append(Block('numbered',[Run(re.sub(r'^\d+[.)]\s+','',line))]))
                else: out.append(Block('paragraph',[Run(line)]))
    return out

def find_fonts(user=None,bold_user=None):
    regular_candidates=[user,'C:/Windows/Fonts/segoepr.ttf','C:/Windows/Fonts/comic.ttf','/System/Library/Fonts/Noteworthy.ttc','/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Oblique.ttf']
    regular=next((p for p in regular_candidates if p and Path(p).exists()),None)
    if not regular: raise FileNotFoundError('Pass --font with a handwriting .ttf/.otf font')
    bold_candidates=[bold_user]
    # Known pairs for built-in fallbacks. For an arbitrary custom font, stroke fallback is used.
    if regular.endswith('DejaVuSans-Oblique.ttf'): bold_candidates.append('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-BoldOblique.ttf')
    if regular.lower().endswith('comic.ttf'): bold_candidates.append('C:/Windows/Fonts/comicbd.ttf')
    bold=next((p for p in bold_candidates if p and Path(p).exists()),regular)
    return regular,bold

def font_set(path,bold_path,size):
    return ImageFont.truetype(path,size),ImageFont.truetype(bold_path,size)

def measure_runs(draw,runs,fonts):
    reg,bold=fonts
    return sum(draw.textlength(r.text,font=bold if r.bold else reg) for r in runs)

def tokenize_runs(runs):
    tokens=[]
    for r in runs:
        for piece in re.findall(r'\S+\s*',r.text):
            tokens.append(Run(piece,r.bold))
    return tokens

def wrap_runs(draw,runs,fonts,max_width):
    tokens=tokenize_runs(runs); lines=[]; cur=[]; width=0
    reg,bold=fonts
    for tok in tokens:
        f=bold if tok.bold else reg; w=draw.textlength(tok.text,font=f)
        if cur and width+w>max_width:
            lines.append(cur); cur=[]; width=0
            tok=Run(tok.text.lstrip(),tok.bold); w=draw.textlength(tok.text,font=f)
        cur.append(tok); width+=w
    if cur: lines.append(cur)
    return lines or [[Run('')]]

def make_paper(cfg,n):
    rng=random.Random(cfg.seed+n*997); img=Image.new('RGB',(cfg.width,cfg.height),cfg.paper)
    if cfg.texture:
        noise=Image.new('L',(cfg.width//3,cfg.height//3)); noise.putdata([rng.randint(112,144) for _ in range(noise.width*noise.height)])
        noise=noise.resize(img.size).filter(ImageFilter.GaussianBlur(1.2)); img=Image.blend(img,Image.merge('RGB',(noise,noise,noise)),.05)
    d=ImageDraw.Draw(img)
    for y in range(cfg.top_margin+cfg.rule_gap,cfg.height-cfg.bottom_margin+1,cfg.rule_gap): d.line((0,y,cfg.width,y),fill=cfg.rule,width=2)
    d.line((cfg.left_margin-35,0,cfg.left_margin-35,cfg.height),fill=cfg.margin_rule,width=2)
    if cfg.binder_holes:
        for y in (180,cfg.height//2,cfg.height-180):
            d.ellipse((22,y-19,60,y+19),fill=(218,216,208),outline=(168,168,164),width=2); d.ellipse((29,y-12,53,y+12),fill=(242,240,232))
    return img

def draw_run_line(draw,runs,x,rule_y,fonts,ink,rng,cfg,underline=False,prefix=''):
    reg,bold=fonts; cursor=float(x); baseline=rule_y-cfg.baseline_lift+rng.uniform(-cfg.max_baseline_jitter,cfg.max_baseline_jitter)
    if prefix:
        draw.text((cursor,baseline),prefix,font=reg,fill=ink,anchor='ls'); cursor+=draw.textlength(prefix,font=reg)
    for run in runs:
        font=bold if run.bold else reg
        shade=tuple(max(0,min(255,c+rng.randint(-4,4))) for c in ink)
        # Draw complete styled runs, not individual words. This preserves kerning and a smooth handwritten flow.
        stroke=0 if (not run.bold or bold.path!=reg.path) else 1
        draw.text((cursor+rng.uniform(-cfg.max_x_jitter,cfg.max_x_jitter),baseline),run.text,font=font,fill=shade,anchor='ls',stroke_width=stroke,stroke_fill=shade)
        cursor+=draw.textlength(run.text,font=font)
    if underline: draw.line((x,rule_y+4,cursor,rule_y+4),fill=ink,width=2)

def render(blocks,outdir,stem,cfg,regular_path,bold_path,fmt):
    outdir.mkdir(parents=True,exist_ok=True); body=font_set(regular_path,bold_path,cfg.body_size)
    hs={i:font_set(regular_path,bold_path,{1:46,2:41,3:38,4:36,5:35,6:34}[i]) for i in range(1,7)}
    usable=cfg.width-cfg.left_margin-cfg.right_margin; pages=[]; n=1
    img=make_paper(cfg,n); draw=ImageDraw.Draw(img); rng=random.Random(cfg.seed+n); y=cfg.top_margin+cfg.rule_gap; counter=0
    def save():
        ext=fmt; p=outdir/f'{stem}_page_{len(pages)+1:02d}.{ext}'; img.save(p,'PNG' if ext=='png' else 'JPEG',quality=94); pages.append(p)
    def newpage():
        nonlocal img,draw,rng,y,n
        save(); n+=1; img=make_paper(cfg,n); draw=ImageDraw.Draw(img); rng=random.Random(cfg.seed+n); y=cfg.top_margin+cfg.rule_gap
    for b in blocks:
        if y>cfg.height-cfg.bottom_margin-cfg.rule_gap:newpage()
        if b.kind=='spacer': y+=cfg.rule_gap; continue
        if b.kind=='rule': draw.line((cfg.left_margin,y,cfg.width-cfg.right_margin,y),fill=cfg.ink,width=2); y+=cfg.rule_gap; continue
        x=cfg.left_margin+b.indent*40; fonts=hs.get(b.level,hs[2]) if b.kind=='heading' else body; prefix=''; underline=False
        if b.kind=='heading': prefix='• ' if b.level>=2 else ''; underline=True
        elif b.kind=='bullet': prefix='• '
        elif b.kind=='numbered': counter+=1; prefix=f'{counter}. '
        elif b.kind=='task': prefix='[x] ' if b.checked else '[ ] '
        elif b.kind=='quote': prefix='| '
        if b.kind=='code':
            for raw in plain(b.runs).splitlines():
                if y>cfg.height-cfg.bottom_margin-cfg.rule_gap:newpage()
                draw_run_line(draw,[Run(raw)],x+25,y,body,cfg.ink,rng,cfg); y+=cfg.rule_gap
            continue
        pw=draw.textlength(prefix,font=fonts[0]) if prefix else 0
        lines=wrap_runs(draw,b.runs,fonts,usable-(x-cfg.left_margin)-pw)
        for i,line in enumerate(lines):
            if y>cfg.height-cfg.bottom_margin-cfg.rule_gap:newpage()
            lx=x if i==0 else x+pw
            draw_run_line(draw,line,lx,y,fonts,cfg.ink,rng,cfg,underline and i==0,prefix if i==0 else '')
            y+=cfg.rule_gap
        if b.kind=='heading': y+=cfg.rule_gap//5
    save(); return pages

def main():
    a=argparse.ArgumentParser(description='Convert Markdown/PDF notes to handwritten notebook images.')
    a.add_argument('input',type=Path); a.add_argument('-o','--output-dir',type=Path,default=Path('output')); a.add_argument('--format',choices=['png','jpg'],default='png')
    a.add_argument('--font'); a.add_argument('--bold-font'); a.add_argument('--seed',type=int,default=42); a.add_argument('--baseline-lift',type=int,default=2)
    args=a.parse_args(); blocks=extract_pdf(args.input) if args.input.suffix.lower()=='.pdf' else parse_markdown(args.input.read_text(encoding='utf-8'))
    reg,bold=find_fonts(args.font,args.bold_font); cfg=Config(seed=args.seed,baseline_lift=args.baseline_lift)
    pages=render(blocks,args.output_dir,args.input.stem,cfg,reg,bold,args.format)
    print(f'Created {len(pages)} page(s)'); [print(p) for p in pages]
if __name__=='__main__': main()
