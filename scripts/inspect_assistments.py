"""Reproducible streaming audit of the user-supplied ASSISTments CSV."""
import csv
import hashlib
import json
import math
import statistics
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'data/raw/skill_builder_data_corrected_collapsed.csv'
with path.open('rb') as f:sha256=hashlib.file_digest(f,'sha256').hexdigest()
with path.open('rb') as f:bad_utf8_bytes=sum(chunk.count(b'\x80') for chunk in iter(lambda:f.read(1024*1024),b''))
missing=Counter();targets=Counter();clean_targets=Counter();skill_counts=Counter();names=Counter();users=Counter()
rejected=Counter();seen_order=set();seen_user_problem=set();duplicate_order=0;repeat_user_problem=0;row_count=0
null={'','na','nan','null','none'}
with path.open(encoding='utf-8-sig',errors='replace',newline='') as f:
    reader=csv.DictReader(f);columns=reader.fieldnames
    for r in reader:
        row_count+=1
        for k in ['user_id','skill_id','skill_name','problem_id','correct','order_id','attempt_count','hint_count','opportunity']:
            if str(r.get(k,'')).strip().lower() in null:missing[k]+=1
        targets[r.get('correct')]+=1
        u=r.get('user_id','').strip();s=r.get('skill_id','').strip();name=r.get('skill_name','').strip();o=r.get('order_id','').strip();problem=r.get('problem_id','').strip()
        if (u,o) in seen_order:duplicate_order+=1
        else:seen_order.add((u,o))
        if (u,problem) in seen_user_problem:repeat_user_problem+=1
        else:seen_user_problem.add((u,problem))
        try:
            y=float(r.get('correct',''));order=float(o)
            if u.lower() in null or s.lower() in null or y not in (0.,1.) or not math.isfinite(order):raise ValueError
        except (ValueError,TypeError):rejected['missing_skill_or_invalid_required_field']+=1;continue
        users[u]+=1;skill_counts[s]+=1;names[name if name.lower() not in null else s]+=1;clean_targets[str(int(y))]+=1
report={'file':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha256,
        'download_metadata_id':'1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE',
        'download_metadata_matches_official_id':'1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE' in Path(str(path)+':Zone.Identifier').read_text(errors='replace'),
        'columns':columns,'rows':row_count,'valid_rows':sum(users.values()),'rejected':dict(rejected),
        'missing_by_column':dict(missing),'target_counts_before_filter':dict(targets),
        'target_counts_after_filter':dict(clean_targets),'students_after_filter':len(users),'skills_after_filter':len(skill_counts),
        'skill_name_values_after_filter':len(names),'malformed_utf8_byte_0x80_count':bad_utf8_bytes,
        'duplicate_user_order_pairs':duplicate_order,'repeated_user_problem_pairs':repeat_user_problem,
        'responses_per_student_after_filter':{'min':min(users.values()),'median':statistics.median(users.values()),'max':max(users.values())},
        'top_skills':[{'skill_id':s,'count':n} for s,n in skill_counts.most_common(20)]}
(ROOT/'reports/raw_eda.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:report[k] for k in ['bytes','sha256','rows','valid_rows','rejected','students_after_filter','skills_after_filter','malformed_utf8_byte_0x80_count','duplicate_user_order_pairs','repeated_user_problem_pairs']},ensure_ascii=False,indent=2))
