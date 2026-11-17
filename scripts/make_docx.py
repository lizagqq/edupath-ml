"""Build coursework DOCX with real embedded figures, tables, TOC and styles.
Uses OOXML and Python stdlib; never builds the ML project or modifies data.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
import re, struct, json
ROOT=Path(__file__).resolve().parents[1]
NS='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
lines=(ROOT/'docs/coursework_draft.md').read_text().splitlines()
rels=[('rId1','footer','footer1.xml'),('rId2','styles','styles.xml'),('rId3','settings','settings.xml')]
media={};headings=[];figures=[];tables=[]
def clean(s):return s.replace('`','').replace('**','')
def run(t,bold=False,mono=False):
    rpr=('<w:b/>' if bold else '')+('<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="24"/>' if mono else '')
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(clean(t))}</w:t></w:r>'
def p(t='',style='Normal',extra='',bold=False,mono=False):
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{extra}</w:pPr>{run(t,bold,mono)}</w:p>'
def field(instr,cache=''):
    return '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve">'+escape(instr)+'</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'+run(cache)+'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
def heading(t,level):
    n=len(headings)+1;headings.append((level,t,n))
    return f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr><w:bookmarkStart w:id="{n}" w:name="sec{n}"/>{run(t)}<w:bookmarkEnd w:id="{n}"/></w:p>'
def image_line(caption,path):
    file=ROOT/'docs'/path;data=file.read_bytes();width,height=struct.unpack('>II',data[16:24]);name=file.name
    rid=f'rId{len(rels)+1}';rels.append((rid,'image','media/'+name));media[name]=data
    cx=5750000;cy=round(cx*height/width)
    if cy>7200000:cx=round(cx*7200000/cy);cy=7200000
    num=len(figures)+1;figures.append(caption)
    drawing=f'''<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{num}" name="{escape(caption)}" descr="{escape(caption)}"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="{num}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'''
    return '<w:p><w:pPr><w:pStyle w:val="Figure"/></w:pPr>'+drawing+'</w:p>'+p(caption,'Caption')
def table(block):
    rows=[[clean(c.strip()) for c in line.strip('|').split('|')] for line in block]
    rows=[r for r in rows if not all(re.fullmatch(':?-+:?',v) for v in r)]
    n=len(rows[0]);width=9071
    if n==2:widths=[3300,width-3300]
    elif n==3:widths=[1900,5100,2071]
    elif n==5:widths=[2900,1100,1690,1690,1691]
    elif n==4:widths=[2800,2090,2090,2091]
    else:widths=[width//n]*n
    grid=''.join(f'<w:gridCol w:w="{v}"/>' for v in widths)
    borders=''.join(f'<w:{side} w:val="single" w:sz="4" w:color="444444"/>' for side in ['top','left','bottom','right','insideH','insideV'])
    result=f'<w:tbl><w:tblPr><w:tblW w:w="{width}" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders>{borders}</w:tblBorders><w:tblCellMar><w:top w:w="55" w:type="dxa"/><w:bottom w:w="55" w:type="dxa"/><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>'
    for i,row in enumerate(rows):
        result+='<w:tr><w:trPr><w:cantSplit/><w:trHeight w:val="454" w:hRule="atLeast"/>'+('<w:tblHeader/>' if i==0 else '')+'</w:trPr>'
        for j,value in enumerate(row):
            # Soft wrapping of long identifiers/hashes is intentional, no content changes.
            result+=f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/>'+('<w:shd w:fill="EEEEEE"/>' if i==0 else '')+'</w:tcPr>'+p(value,'TableText',bold=i==0)+'</w:tc>'
        result+='</w:tr>'
    return result+'</w:tbl>'+p('','TableText')
parts=[];i=0;title=False
while i<len(lines):
    line=lines[i].strip();i+=1
    if line==':::title':title=True;continue
    if line==':::endtitle':title=False;continue
    if not line:continue
    if title:
        parts.append(p(line,'TitleText',extra='<w:spacing w:before="100" w:after="100"/>',bold=line=='КУРСОВАЯ РАБОТА'));continue
    if line==':::toc':parts.append('TOC_MARKER');continue
    if line.startswith('#'):
        level=len(line)-len(line.lstrip('#'));parts.append(heading(line[level:].strip(),level));continue
    if line.startswith('```'):
        code=[]
        while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
        i+=1
        parts.extend(p(c,'Code',extra='<w:keepNext/>' if j<len(code)-1 else '',mono=True) for j,c in enumerate(code));continue
    match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
    if match:parts.append(image_line(*match.groups()));continue
    if line.startswith('|'):
        block=[line]
        while i<len(lines) and lines[i].startswith('|'):block.append(lines[i]);i+=1
        parsed=[l for l in block if not re.fullmatch(r'[| :\-]+',l)]
        # Long catalog is explicitly split with the required continued heading.
        if len(parsed)>14:
            head=parsed[0];body=parsed[1:]
            for start in range(0,len(body),11):
                if start:parts.append(p('Продолжение таблицы Г.1','TableCaption',extra='<w:pageBreakBefore/>'))
                parts.append(table([head]+body[start:start+11]))
        else:parts.append(table(block))
        continue
    if line.startswith('$$ '):parts.append(p(line[3:],'Equation'));continue
    if re.match(r'^Таблица [0-9А-Я]+\.\d+ — ',line):tables.append(line);parts.append(p(line,'TableCaption'));continue
    parts.append(p(line))
# Real Word TOC field with cached, hyperlinked heading entries and dynamic page references.
toc=['<w:p><w:pPr><w:pStyle w:val="TOC1"/></w:pPr><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r></w:p>']
for level,t,n in headings:
    if level>2 or t in ['СОДЕРЖАНИЕ','ЛИСТ ЗАДАНИЯ']:continue
    toc.append(f'<w:p><w:pPr><w:pStyle w:val="TOC{level}"/></w:pPr><w:hyperlink w:anchor="sec{n}">{run(t)}</w:hyperlink><w:r><w:tab/></w:r>'+field(f' PAGEREF sec{n} \\h ','')+'</w:p>')
toc.append('<w:p><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
body=''.join(parts).replace('TOC_MARKER',''.join(toc))
body+='''<w:sectPr><w:footerReference w:type="default" r:id="rId1"/><w:titlePg/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1701" w:header="567" w:footer="567"/></w:sectPr>'''
header=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>'''
def style(id,ppr='',rpr='',based='Normal'):
 return f'<w:style w:type="paragraph" w:styleId="{id}"><w:name w:val="{id}"/>'+ (f'<w:basedOn w:val="{based}"/>' if id!='Normal' else '')+f'<w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>'
normalp='<w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/><w:ind w:firstLine="709"/><w:jc w:val="both"/><w:widowControl/>'
normalr='<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="28"/><w:lang w:val="ru-RU"/>'
styles=[style('Normal',normalp,normalr)]
for n in range(1,4):
 styles.append(style(f'Heading{n}',f'<w:keepNext/><w:keepLines/><w:outlineLvl w:val="{n-1}"/><w:spacing w:before="240" w:after="180"/>'+('<w:pageBreakBefore/>' if n==1 else ''),'<w:b/>'))
for n in range(1,3):
 styles.append(style(f'TOC{n}',f'<w:ind w:firstLine="0" w:left="{(n-1)*350}"/><w:jc w:val="left"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9070"/></w:tabs><w:spacing w:line="360" w:after="0"/>'))
styles+=[style('TitleText','<w:ind w:firstLine="0"/><w:jc w:val="center"/><w:spacing w:line="300"/>'),style('TableText','<w:ind w:firstLine="0"/><w:jc w:val="left"/><w:spacing w:line="360" w:before="0" w:after="0"/>'),style('TableCaption','<w:ind w:firstLine="0"/><w:jc w:val="left"/><w:keepNext/><w:spacing w:before="180" w:after="100"/>'),style('Caption','<w:ind w:firstLine="0"/><w:jc w:val="center"/><w:keepLines/><w:spacing w:after="280"/>'),style('Figure','<w:ind w:firstLine="0"/><w:jc w:val="center"/><w:keepNext/><w:spacing w:line="240" w:before="100" w:after="100"/>'),style('Code','<w:ind w:firstLine="0"/><w:jc w:val="left"/><w:spacing w:line="240"/>','<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="24"/>'),style('Equation','<w:ind w:firstLine="0"/><w:jc w:val="center"/><w:keepLines/><w:spacing w:before="140" w:after="140"/>')]
footer=f'<w:ftr xmlns:w="{NS}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>{field(" PAGE ")}</w:p></w:ftr>'
ct='''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'''
for part,typ in [('document','document.main'),('styles','styles'),('settings','settings'),('footer1','footer')]:ct+=f'<Override PartName="/word/{part}.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.{typ}+xml"/>'
ct+='</Types>'
relroot='http://schemas.openxmlformats.org/package/2006/relationships'
rs=f'<Relationships xmlns="{relroot}">'+''.join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{typ}" Target="{path}"/>' for rid,typ,path in rels)+'</Relationships>'
rootrels=f'<Relationships xmlns="{relroot}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
path=ROOT/'docs/coursework_draft.docx'
with ZipFile(path,'w',ZIP_DEFLATED) as z:
 for name,data in {'[Content_Types].xml':ct,'_rels/.rels':rootrels,'word/document.xml':header+body+'</w:body></w:document>','word/styles.xml':f'<w:styles xmlns:w="{NS}">'+''.join(styles)+'</w:styles>','word/footer1.xml':footer,'word/settings.xml':f'<w:settings xmlns:w="{NS}"><w:updateFields w:val="true"/><w:defaultTabStop w:val="709"/></w:settings>','word/_rels/document.xml.rels':rs}.items():z.writestr(name,data)
 for name,data in media.items():z.writestr('word/media/'+name,data)
print(json.dumps({'file':str(path),'figures':len(figures),'tables':len(tables),'headings':len(headings),'bytes':path.stat().st_size},ensure_ascii=False))
