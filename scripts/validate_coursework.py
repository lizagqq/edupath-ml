"""Validate generated coursework package and its agreement with saved ML evidence."""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import hashlib, json, re, posixpath
ROOT=Path(__file__).resolve().parents[1]
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
md=(ROOT/'docs/coursework_draft.md').read_text()
with ZipFile(ROOT/'docs/coursework_draft.docx') as z:
    assert z.testzip() is None
    for name in z.namelist():
        if name.endswith(('.xml','.rels')):ET.fromstring(z.read(name))
    doc=ET.fromstring(z.read('word/document.xml'))
    txt='\n'.join(x.text or '' for x in doc.findall('.//w:t',ns))
    media=[n for n in z.namelist() if n.startswith('word/media/')]
    assert len(media)==12==len(doc.findall('.//a:blip',ns))
    for entry in ET.fromstring(z.read('word/_rels/document.xml.rels')):
        assert posixpath.normpath('word/'+entry.attrib['Target']) in z.namelist()
    for model in json.loads((ROOT/'reports/experiment.json').read_text())['metrics'].values():
        for value in model.values():assert f'{value:.4f}'.replace('.',',') in txt
    for fragment in ['2 ТЕХНОЛОГИЯ РАЗРАБОТКИ ПРИЛОЖЕНИЯ','17/17','до четырёх','39 → 299']:
        assert fragment in txt,fragment
    assert 'TOC ' in z.read('word/document.xml').decode()
    assert not re.search('маршрут.{0,20}(из девяти|девять тем)',txt,re.I)
    sync=json.loads((ROOT/'reports/knowledge_base_sync.json').read_text())
    for path,key in [('models/model.json','model_sha256'),('reports/experiment.json','experiment_sha256')]:
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sync[key]
    report={'docx_xml':'valid','embedded_figures':len(media),
        'numbered_tables':len(re.findall(r'^Таблица [0-9А-Я]+\.\d+ — ',md,re.M)),
        'physical_table_parts':len(doc.findall('.//w:tbl',ns)),
        'headings':len(doc.findall('.//w:bookmarkStart',ns)),
        'all_saved_metrics_present':True,'model_and_experiment_hashes_unchanged':True,
        'word_count_md':len(md.split()),
        'pagination':'Not rendered; update TOC and page references in Word/LibreOffice',
        'application_tests':'Existing reports only; not rerun for documentation-only changes'}
(ROOT/'docs/coursework_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
