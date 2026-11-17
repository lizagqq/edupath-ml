"""Rebuild publication figures from saved reports and read-only Service; no training."""
from pathlib import Path
import json, math, sys
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'docs/figures';OUT.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
INK='#172d42';BLUE='#eaf1f7';TEAL='#dcefe9'
def canvas(w=1600,h=1500):
 global im,d
 im=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(im)
def text(x,y,t,size=29,anchor='mm',fill=INK):
 d.multiline_text((x,y),t,font=ImageFont.truetype(FONT,size),fill=fill,anchor=anchor,align='center',spacing=9)
def box(x,y,w,h,t,kind='rect',fill=BLUE,size=29):
 if kind=='decision':d.polygon([(x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2)],fill=fill,outline=INK,width=3)
 elif kind=='end':d.rounded_rectangle((x,y,x+w,y+h),radius=h//2,fill=fill,outline=INK,width=3)
 else:d.rectangle((x,y,x+w,y+h),fill=fill,outline=INK,width=3)
 while max(d.textlength(line,font=ImageFont.truetype(FONT,size)) for line in t.split('\n'))>w-28: size-=1
 text(x+w/2,y+h/2,t,size)
def arrow(points,label=None):
 d.line(points,fill=INK,width=4)
 (x0,y0),(x,y)=points[-2:];a=math.atan2(y-y0,x-x0)
 d.polygon([(x,y),(x-17*math.cos(a-.45),y-17*math.sin(a-.45)),(x-17*math.cos(a+.45),y-17*math.sin(a+.45))],fill=INK)
 if label:
  x,y=points[len(points)//2];text(x+40,y-20,label,25)
def save(name):im.save(OUT/(name+'.png'),dpi=(240,240))
canvas(1600,1250)
box(50,60,480,150,'ASSISTments CSV\n346 860 исходных строк')
box(50,280,480,160,'Очистка и причинные признаки\n283 105 событий')
box(50,510,480,160,'Разделение по ученикам\nОбучение и offline-оценка')
box(50,750,480,150,'models/model.json\nreports/experiment.json',fill=TEAL)
box(700,280,800,160,'SQLite: события, навыки, ученики,\nматериалы и зависимости',fill=TEAL)
box(700,570,800,180,'Service: профиль → прогноз →\nперсональный маршрут и материалы')
box(700,850,800,110,'FastAPI: семь маршрутов GET')
box(700,1070,800,110,'Streamlit: четыре раздела')
arrow([(290,210),(290,280)]);arrow([(290,440),(290,510)]);arrow([(290,670),(290,750)])
arrow([(530,360),(700,360)]);arrow([(1100,440),(1100,570)])
arrow([(530,825),(620,825),(620,660),(700,660)])
arrow([(1100,750),(1100,850)]);arrow([(1100,960),(1100,1070)])
text(290,1130,'Сборка и обучение — отдельно.\nЗапуск читает готовые артефакты.',26)
save('architecture')
canvas(1600,1700)
box(500,30,600,85,'Начало: подготовка данных','end')
box(400,165,800,110,'Чтение CSV и проверка столбцов')
box(450,330,700,180,'Корректны ID,\ncorrect и order_id?','decision')
box(40,360,320,110,'Учёт отклонённой\nстроки',size=25)
box(400,565,800,120,'Сортировка: user_id, order_id,\nисходный номер строки')
box(400,745,800,130,'Признаки события из прошлых счётчиков\nЗатем обновление счётчиков ответом')
box(450,935,700,170,'Все события\nобработаны?','decision')
box(400,1170,800,120,'Разделение учеников: seed=42\n3330 train / 833 test')
box(400,1350,800,110,'Baseline, Logistic SGD и оценка test')
box(400,1520,800,110,'Сохранение SQLite, JSON и отчётов','end')
arrow([(800,115),(800,165)]);arrow([(800,275),(800,330)])
arrow([(450,420),(360,420)],'нет');arrow([(200,470),(200,620),(400,620)])
arrow([(800,510),(800,565)],'да');arrow([(800,685),(800,745)])
arrow([(800,875),(800,935)]);arrow([(1150,1020),(1390,1020),(1390,810),(1200,810)],'нет')
arrow([(800,1105),(800,1170)],'да');arrow([(800,1290),(800,1350)]);arrow([(800,1460),(800,1520)])
save('data_flow')
canvas(1600,1800)
box(400,30,800,90,'Начало: профиль ученика и 23 материала','end')
box(400,175,800,125,'Диагностика: n ≥ 3 и p < 0,50\nСортировка: p ↑, n ↓, ID ↑')
box(400,355,800,115,'Сохранить все затруднения; отдельно\nвыделить навыки без материалов')
box(400,525,800,125,'Выбрать до 4 тем с материалами\nБез повторения исходного названия')
box(450,705,700,160,'Есть выбранные\nосновные темы?','decision')
box(30,730,310,110,'Пустой маршрут\nи пояснение',size=25)
box(400,925,800,140,'Добавить предварительные темы:\np < 0,70 или n < 3; материал есть')
box(400,1120,800,125,'Проверить DAG; рассчитать приоритеты\nВыбирать максимум среди доступных')
box(400,1300,800,125,'Связать шаги с материалами по ID\nДобавить роль и основание вывода')
box(400,1480,800,120,'До 3 отложенных слабых ID\nвывести в закрепление')
box(400,1660,800,90,'Ответ API: маршрут и полная диагностика','end')
for a,b in [(120,175),(300,355),(470,525),(650,705),(865,925),(1065,1120),(1245,1300),(1425,1480),(1600,1660)]:arrow([(800,a),(800,b)])
text(860,895,'да',25);arrow([(450,785),(340,785)],'нет')
arrow([(185,840),(185,1705),(400,1705)])
save('recommendation_flow')
canvas(1600,1320)
box(40,60,550,150,'students\nPK user_id TEXT',size=31)
box(900,60,650,190,'skills\nPK skill_id TEXT\nskill_name TEXT NOT NULL',size=29)
box(40,420,720,300,'interactions\nPK id INTEGER\nFK user_id TEXT → students\nFK skill_id TEXT → skills\norder_id REAL; correct INTEGER',size=29)
box(900,430,650,260,'materials\nPK skill_id TEXT\ntitle; explanation; example\nsource; url (все TEXT)',size=29)
box(900,900,650,230,'prerequisites\nparent TEXT; child TEXT\nPK (parent, child)',size=29)
arrow([(315,210),(315,420)]);text(400,300,'1 : 0..N',26)
arrow([(900,160),(800,160),(800,500),(760,500)]);text(800,350,'1 : 0..N',26)
d.line([(1230,250),(1230,430)],fill=INK,width=3);text(1370,330,'1 : 0..1',25)
d.line([(1550,170),(1580,170),(1580,960),(1550,960)],fill=INK,width=3)
d.line([(900,170),(850,170),(850,1070),(900,1070)],fill=INK,width=3)
text(1225,820,'Две роли: parent / child\n1 : 0..N для каждой',26)
text(800,1240,'Стрелки — объявленные FOREIGN KEY. Простые линии — логические связи.\nВ materials и prerequisites внешние ключи в DDL не объявлены.',25)
save('sqlite_er')
canvas(1600,1100)
for y,a,b in [(60,'67 · Умножение дробей','61 · Деление дробей'),(300,'47 · Перевод дробей,\nдесятичных и процентов','77 · Нахождение процентов'),(650,'311 · Уравнения\nдо двух действий','312 · Уравнения\nболее двух действий'),(880,'39 · Площадь круга','299 · Поверхность цилиндра')]:
 box(40,y,650,140,a,size=29);box(930,y,630,140,b,size=29);arrow([(690,y+70),(930,y+70)])
box(930,485,630,110,'70 · Процент от числа',size=29)
arrow([(690,370),(810,370),(810,540),(930,540)])
save('skill_dag')
canvas(1600,1120)
box(40,40,1520,100,'EduPath ML — структурный макет, не снимок браузера',fill=TEAL,size=32)
box(40,190,360,840,'Боковая панель\n\nВыбор ученика\n79021\n\nОбзор ученика\nОценка знаний\nИндивидуальная\nтраектория\nКачество модели',size=27)
box(450,190,1110,190,'Обзор ученика\n1061 ответ · 93 наблюдавшихся навыка\n56 навыков с минимум 3 ответами',size=30)
box(450,440,1110,210,'Диагностика\nИсторическая точность / прогноз следующего ответа\nЧисло наблюдений и предварительный сигнал',size=29)
box(450,710,1110,320,'Траектория\nПовороты → отражение → круговые диаграммы\n→ площадь круга → поверхность цилиндра\n\nПричина · материал · самопроверка\nОтдельно: закрепление и навыки без материалов',size=28)
save('ui_structure')
# Plots use saved aggregate metrics only: no inferred ROC curves or confidence intervals.
exp=json.loads((ROOT/'reports/experiment.json').read_text());audit=json.loads((ROOT/'reports/integration_audit.json').read_text())
def bars(name,title,labels,values,maxval=1,fmt='.4f',xlabel='Значение метрики',colors=None):
 canvas(1600,850);text(800,65,title,37)
 left,right,top,bottom=520,1450,170,650
 for i in range(6):
  x=left+(right-left)*i/5;d.line((x,top,x,bottom),fill='#d3dce4',width=2)
  text(x,bottom+40,format(maxval*i/5,'.2f'),24)
 for j,(label,v) in enumerate(zip(labels,values)):
  y=top+45+j*135;text(left-25,y,label,28,anchor='rm')
  d.rectangle((left,y-35,left+(right-left)*v/maxval,y+35),fill=(colors or ['#36668a','#618c7e','#233f59'])[j%3])
  text(left+(right-left)*v/maxval+15,y,format(v,fmt).replace('.',','),27,anchor='lm')
 text(1000,755,xlabel,27);save(name)
models=['constant','history_rule','logistic_sgd'];labels=['Константа','Историческое правило','Logistic SGD']
for met,title in [('log_loss','Log Loss: меньше — лучше'),('roc_auc','ROC-AUC: больше — лучше'),('brier','Brier Score: меньше — лучше')]:
 bars(met,title,labels,[exp['metrics'][x][met] for x in models])
bars('coverage','Охват библиотеки: разные знаменатели',['ID навыков','Ответы','Ученики'],[23/149,125669/283105,3119/4163],xlabel='Доля соответствующей совокупности')
bars('target_distribution','Распределение correct после очистки',['Правильные','Ошибочные'],[186322,96783],maxval=220000,fmt=',.0f',xlabel='Количество ответов')
from src.api.service import Service
s=Service();examples={u:s.trajectory(u) for u in ['79021','75169','78970','21825']}
# Save only the evidence needed by the document, not an extra experiment report.
(OUT/'document_evidence.json').write_text(json.dumps({'examples':examples,'source':'Read-only Service over existing SQLite and model; no retraining.'},ensure_ascii=False,indent=2))
bars('route_forecasts','Ученик 79021: прогнозы в порядке маршрута',[x['skill_id'] for x in examples['79021']['trajectory']][:3],[x['predicted_probability'] for x in examples['79021']['trajectory']][:3])
# Dedicated 5-row version.
canvas(1600,1050);text(800,60,'Ученик 79021: прогнозы пяти шагов маршрута',36)
for j,x in enumerate(examples['79021']['trajectory']):
 y=190+j*145;label=f"{j+1}. {x['skill_id']}"+(' (подготовка)' if x['role']=='prerequisite' else '')
 text(460,y,label,30,anchor='rm');d.rectangle((510,y-30,510+850*x['predicted_probability'],y+30),fill='#3c697e' if x['role']=='focus' else '#69846a');text(530+850*x['predicted_probability'],y,f"{100*x['predicted_probability']:.2f}%",29,anchor='lm')
for i in range(6):text(510+850*i/5,960,f'{i*20}%',27)
text(900,1020,'Шкала вероятности от 0 до 100%; порядок учитывает зависимости',25)
save('route_forecasts')
print('Created',len(list(OUT.glob('*.png'))),'figures')
