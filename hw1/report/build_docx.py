"""Export the report's shared content as editable Word paragraphs and tables."""
import ast
from html.parser import HTMLParser
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'assets'
CW = 595.276 - 96
body, small, caption = 'Normal', 'Small Text', 'Caption'
doc = Document()
section = doc.sections[0]
section.page_width, section.page_height = Pt(595.276), Pt(841.89)
section.top_margin = section.bottom_margin = Pt(48)
section.left_margin = section.right_margin = Pt(48)
for name, size, leading in [('Normal',9.65,13.8),('Small Text',8.1,11.1),('Caption',8,10.7),('Title',19,24),('Heading 1',19,24),('Heading 2',11,15)]:
    style = doc.styles[name] if name in doc.styles else doc.styles.add_style(name, 1)
    style.font.name = 'DejaVu Sans'
    for key in list(style.element.rPr.rFonts.attrib):
        if 'Theme' in key or 'theme' in key: del style.element.rPr.rFonts.attrib[key]
    for border in style.element.xpath('./w:pPr/w:pBdr'): border.getparent().remove(border)
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor(0,0,0)
    style.font.bold = name in ('Title','Heading 1','Heading 2')
    style.font.italic = False
    fmt = style.paragraph_format
    fmt.line_spacing = Pt(leading)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(6)
    fmt.widow_control = False
    fmt.keep_with_next = name in ('Title','Heading 1','Heading 2')
    fmt.keep_together = False

class Inline(HTMLParser):
    def __init__(self, p):
        super().__init__(convert_charrefs=True)
        self.p, self.bold, self.italic = p, False, False
        self.link = None
    def handle_starttag(self, tag, attrs):
        if tag == 'b': self.bold = True
        elif tag == 'i': self.italic = True
        elif tag == 'link': self.link = dict(attrs).get('href')
    def handle_endtag(self, tag):
        if tag == 'b': self.bold = False
        elif tag == 'i': self.italic = False
        elif tag == 'link': self.link = None
    def handle_data(self, text):
        run = self.p.add_run(text)
        if self.bold: run.bold = True
        if self.italic: run.italic = True
        if self.link:
            from docx.opc.constants import RELATIONSHIP_TYPE
            rel = self.p.part.relate_to(self.link, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
            link = OxmlElement('w:hyperlink')
            link.set(qn('r:id'), rel)
            self.p._p.remove(run._r)
            link.append(run._r)
            self.p._p.append(link)

def paragraph(text, style=body, gap=6):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(gap)
    Inline(p).feed(text)
    return p

page_count = 0
def page(title):
    global page_count
    p = doc.add_paragraph(title, style='Title' if page_count == 0 else 'Heading 1')
    p.paragraph_format.page_break_before = page_count > 0
    p.paragraph_format.space_after = Pt(15)
    page_count += 1

def heading(text):
    p=paragraph(text, 'Heading 2', 5)
    for run in p.runs: run.bold=True

def table(headers, rows, widths):
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    for column, width in zip(t.columns, widths): column.width = Pt(width)
    props = t._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for side in ['top','bottom','left','right','insideH','insideV']:
        b = OxmlElement('w:'+side)
        b.set(qn('w:val'), 'single' if side in ('top','bottom') else 'nil')
        b.set(qn('w:sz'),'4')
        b.set(qn('w:color'),'000000')
        borders.append(b)
    props.append(borders)
    margins = OxmlElement('w:tblCellMar')
    for side, value in [('top',100),('bottom',100),('left',120),('right',120)]:
        e=OxmlElement('w:'+side);e.set(qn('w:w'),str(value));e.set(qn('w:type'),'dxa');margins.append(e)
    props.append(margins)
    for i, values in enumerate([headers]+rows):
        row = t.rows[0] if i == 0 else t.add_row()
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        if i == 0: row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for cell, text, width in zip(row.cells,values,widths):
            cell.width = Pt(width)
            p=cell.paragraphs[0];p.style='Small Text'
            p.paragraph_format.line_spacing=Pt(11)
            p.paragraph_format.space_after=Pt(0)
            Inline(p).feed(str(text))
            if i == 0:
                for run in p.runs: run.bold=True
                cb=OxmlElement('w:tcBorders'); b=OxmlElement('w:bottom')
                for k,v in [('val','single'),('sz','4'),('color','000000')]:b.set(qn('w:'+k),v)
                cb.append(b);cell._tc.get_or_add_tcPr().append(cb)
    p=doc.add_paragraph();p.paragraph_format.line_spacing=Pt(1);p.paragraph_format.space_after=Pt(8)
    p.paragraph_format.space_before=Pt(0);p.add_run().font.size=Pt(1)

def picture(p,path,width,maxheight):
    with Image.open(path) as im: iw,ih=im.size
    scale=min(width/iw,maxheight/ih)
    p.add_run().add_picture(str(path),width=Pt(iw*scale),height=Pt(ih*scale))

def image(path,width=CW,maxheight=1000,cap=None):
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing=1
    p.paragraph_format.space_after=Pt(5)
    p.paragraph_format.keep_with_next=bool(cap)
    picture(p,path,width,maxheight)
    if cap:paragraph(cap,caption,7)

def pair(left,right,cap):
    t=doc.add_table(rows=1,cols=2)
    t.autofit=False
    width=(CW-30)/2
    for column in t.columns:column.width=Pt(CW/2)
    for cell,path in zip(t.rows[0].cells,[left,right]):
        cell.width=Pt(CW/2)
        p=cell.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing=1
        p.paragraph_format.space_after=Pt(5);p.paragraph_format.keep_with_next=True
        picture(p,path,width,width)
    paragraph(cap,caption,7)

source=(HERE/'build_report.py').read_text()
content=source.split('# Page 1\n',1)[1].split('assert page_num==4',1)[0]
exec(compile(ast.parse(content),str(HERE/'build_report.py'),'exec'))
doc.core_properties.title='HW1 3D Scene Reconstruction'
doc.core_properties.author='115062519'
output=ROOT/'report.docx'
doc.save(output)
print(f'Wrote {output}')
