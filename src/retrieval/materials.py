"""Small original lesson notes, linked to verifiable open textbooks."""
import math
import re
from collections import Counter
from src.retrieval.lessons import enrich_lesson

MATERIALS = [
 {'skill_id':'fractions','title':'Дроби','explanation':'Числитель показывает взятые части, знаменатель — число равных частей целого. Для сложения дробей нужен общий знаменатель.','example':'1/4 + 2/4 = 3/4','source':'OpenStax Prealgebra 2e, 4.1','url':'https://openstax.org/books/prealgebra-2e/pages/4-1-visualize-fractions'},
 {'skill_id':'decimals','title':'Десятичные дроби','explanation':'При сложении десятичных дробей выровняйте разряды по запятой. Дробь 2/5 равна 0,4.','example':'0,25 + 0,40 = 0,65','source':'OpenStax Prealgebra 2e, 5.3','url':'https://openstax.org/books/prealgebra-2e/pages/5-3-decimals-and-fractions'},
 {'skill_id':'percent','title':'Проценты','explanation':'Процент означает одну сотую. Чтобы найти 20% от числа, умножьте число на 0,20.','example':'20% от 150 = 30','source':'OpenStax Prealgebra 2e, 6.1','url':'https://openstax.org/books/prealgebra-2e/pages/6-1-understand-percent'},
 {'skill_id':'ratio','title':'Отношения','explanation':'Отношение сравнивает две величины делением. Сокращайте обе части отношения на общий множитель.','example':'6:9 = 2:3','source':'OpenStax Prealgebra 2e, 6.5','url':'https://openstax.org/books/prealgebra-2e/pages/6-5-solve-proportions-and-their-applications'},
 {'skill_id':'proportion','title':'Пропорции','explanation':'Пропорция — равенство двух отношений. Для проверки равенства можно сравнить произведения крест-накрест.','example':'2/3 = 4/6, так как 2×6 = 3×4','source':'OpenStax Prealgebra 2e, 6.5','url':'https://openstax.org/books/prealgebra-2e/pages/6-5-solve-proportions-and-their-applications'},
 {'skill_id':'equations','title':'Линейные уравнения','explanation':'Сохраняйте равенство, выполняя одинаковое действие с обеими частями уравнения.','example':'x + 3 = 8 ⇒ x = 5','source':'OpenStax Elementary Algebra 2e, 2.1','url':'https://openstax.org/books/elementary-algebra-2e/pages/2-1-solve-equations-using-the-subtraction-and-addition-properties-of-equality'},
 {'skill_id':'geometry','title':'Геометрия','explanation':'Геометрия изучает фигуры и их свойства. У прямоугольника противоположные стороны равны, а углы прямые.','example':'Периметр прямоугольника 3×5 равен 2×(3+5)=16','source':'OpenStax Prealgebra 2e, 9.3','url':'https://openstax.org/books/prealgebra-2e/pages/9-3-use-properties-of-angles-triangles-and-the-pythagorean-theorem'},
 {'skill_id':'area','title':'Площадь фигур','explanation':'Площадь прямоугольника равна произведению длины и ширины. Ответ записывают в квадратных единицах.','example':'Площадь 3×5 = 15 квадратных единиц','source':'OpenStax Prealgebra 2e, 9.4','url':'https://openstax.org/books/prealgebra-2e/pages/9-4-use-properties-of-rectangles-triangles-and-trapezoids'},
]

# IDs and names checked against skill_builder_data_corrected_collapsed.csv.
# These short explanations are original; the links lead to related open lessons.
REAL_MATERIALS = [
 {'skill_id':'280','title':'Сложение и вычитание дробей','explanation':'Приведите дроби к общему знаменателю, затем сложите или вычтите числители. Знаменатель сохраняется.','example':'1/4 + 1/2 = 1/4 + 2/4 = 3/4','source':'OpenStax Prealgebra 2e, 4.5','url':'https://openstax.org/books/prealgebra-2e/pages/4-5-add-and-subtract-fractions-with-different-denominators'},
 {'skill_id':'67','title':'Умножение дробей','explanation':'Чтобы умножить дроби, перемножьте числители и знаменатели, затем сократите результат.','example':'2/3 × 3/4 = 6/12 = 1/2','source':'OpenStax Prealgebra 2e, 4.2','url':'https://openstax.org/books/prealgebra-2e/pages/4-2-multiply-and-divide-fractions'},
 {'skill_id':'61','title':'Деление дробей','explanation':'Деление на дробь заменяют умножением на обратную ей дробь.','example':'2/3 ÷ 4/5 = 2/3 × 5/4 = 5/6','source':'OpenStax Prealgebra 2e, 4.2','url':'https://openstax.org/books/prealgebra-2e/pages/4-2-multiply-and-divide-fractions'},
 {'skill_id':'47','title':'Перевод дробей, десятичных дробей и процентов','explanation':'Чтобы перевести дробь в процент, сначала разделите числитель на знаменатель, затем умножьте результат на 100.','example':'1/4 = 0,25 = 25%','source':'OpenStax Prealgebra 2e, 6.1','url':'https://openstax.org/books/prealgebra-2e/pages/6-1-understand-percent'},
 {'skill_id':'77','title':'Нахождение процентов','explanation':'Чтобы узнать, какой процент составляет часть от целого, разделите часть на целое и умножьте на 100.','example':'15 из 60 = 15/60 × 100% = 25%','source':'OpenStax Prealgebra 2e, 6.2','url':'https://openstax.org/books/prealgebra-2e/pages/6-2-solve-general-applications-of-percent'},
 {'skill_id':'70','title':'Процент от числа','explanation':'Замените процент десятичной дробью и умножьте на исходное число.','example':'20% от 150 = 0,20 × 150 = 30','source':'OpenStax Prealgebra 2e, 6.2','url':'https://openstax.org/books/prealgebra-2e/pages/6-2-solve-general-applications-of-percent'},
 {'skill_id':'79','title':'Пропорции','explanation':'Чтобы решить пропорцию, используйте равенство произведений крест-накрест.','example':'2/3 = 4/6, потому что 2 × 6 = 3 × 4','source':'OpenStax Prealgebra 2e, 6.5','url':'https://openstax.org/books/prealgebra-2e/pages/6-5-solve-proportions-and-their-applications'},
 {'skill_id':'311','title':'Линейные уравнения до двух действий','explanation':'Выполняйте одинаковые обратные действия с обеими частями равенства, пока неизвестное не останется одно.','example':'2x + 3 = 11 ⇒ 2x = 8 ⇒ x = 4','source':'OpenStax Elementary Algebra 2e, 2.1','url':'https://openstax.org/books/elementary-algebra-2e/pages/2-1-solve-equations-using-the-subtraction-and-addition-properties-of-equality'},
 {'skill_id':'312','title':'Линейные уравнения более двух действий','explanation':'Уравнение со скобками решайте так: сначала раскройте скобки и приведите подобные члены, затем перенесите неизвестные и свободные члены по разные стороны.','example':'2(x + 3) + 1 = 15 ⇒ 2x + 7 = 15 ⇒ x = 4','source':'OpenStax Elementary Algebra 2e, 2.4','url':'https://openstax.org/books/elementary-algebra-2e/pages/2-4-use-a-general-strategy-to-solve-linear-equations'},
]

# Additional real IDs selected from the observed difficulty audit. Distinct
# Circle Graph IDs intentionally remain distinct rows, even when the source
# dataset gives them the same label and the same introductory reading.
REAL_SOURCE_NAMES = {
 '292':'Rotations','290':'Reflection','299':'Surface Area Cylinder','39':'Area Circle',
 '2_37_70':'Circle Graph','2_37_48_77':'Circle Graph',
 '2_48_79':'Circle Graph','2_70':'Circle Graph',
 '9_12':'Stem and Leaf Plot','16_17':'Counting Methods',
 '17':'Probability of Two Distinct Events','294':'Area Irregular Figure',
 '277':'Addition and Subtraction Integers','81':'Unit Rate',
}
_circle_graph = {
 'title':'Круговые диаграммы',
 'explanation':'Каждый сектор показывает долю категории от целого. Сумма долей равна 100%; угол сектора равен доле, умноженной на 360°.',
 'example':'25% всех ответов соответствуют сектору 0,25 × 360° = 90°.',
 'source':'OpenStax Introductory Statistics 2e, 1.2',
 'url':'https://openstax.org/books/introductory-statistics-2e/pages/1-2-data-sampling-and-variation-in-data-and-sampling',
}
REAL_MATERIALS += [
 {'skill_id':'292','title':'Повороты фигур','explanation':'При повороте фигура перемещается вокруг выбранного центра на заданный угол, сохраняя форму и размеры. Отмечайте центр и направление поворота.','example':'Поворот точки (2; 1) на 90° против часовой стрелки вокруг начала координат даёт (−1; 2).','source':'OpenStax Contemporary Mathematics, 10.5','url':'https://openstax.org/books/contemporary-mathematics/pages/10-5-tessellations'},
 {'skill_id':'290','title':'Отражение фигур','explanation':'Отражение строит зеркальный образ относительно прямой: соответствующие точки находятся на одинаковом расстоянии от оси.','example':'Отражение точки (3; 2) относительно оси Oy даёт (−3; 2).','source':'OpenStax Contemporary Mathematics, 10.5','url':'https://openstax.org/books/contemporary-mathematics/pages/10-5-tessellations'},
 {'skill_id':'299','title':'Площадь поверхности цилиндра','explanation':'Полная поверхность состоит из двух кругов-оснований и боковой поверхности. Для радиуса r и высоты h: S = 2πr² + 2πrh.','example':'При r = 2 и h = 3 площадь S = 8π + 12π = 20π квадратных единиц.','source':'OpenStax Prealgebra 2e, 9.6','url':'https://openstax.org/books/prealgebra-2e/pages/9-6-solve-geometry-applications-volume-and-surface-area'},
 {'skill_id':'39','title':'Площадь круга','explanation':'Площадь круга зависит от квадрата его радиуса: A = πr². Перед вычислением проверьте, дан радиус или диаметр.','example':'Если радиус равен 3, то площадь равна 9π квадратных единиц.','source':'OpenStax Prealgebra 2e, 9.5','url':'https://openstax.org/books/prealgebra-2e/pages/9-5-solve-geometry-applications-circles-and-irregular-figures'},
 *({'skill_id':sid,**_circle_graph} for sid in ('2_37_70','2_37_48_77','2_48_79','2_70')),
 {'skill_id':'9_12','title':'Диаграмма «стебель и листья»','explanation':'Разделите каждое число на стебель (старшие разряды) и лист (последняя значащая цифра), затем расположите листья по возрастанию.','example':'Для 23, 25, 31: стебель 2 → листья 3, 5; стебель 3 → лист 1.','source':'OpenStax Introductory Statistics 2e, 2.1','url':'https://openstax.org/books/introductory-statistics-2e/pages/2-1-stem-and-leaf-graphs-stemplots-line-graphs-and-bar-graphs'},
 {'skill_id':'16_17','title':'Методы подсчёта','explanation':'Если первый выбор имеет n вариантов, а второй — m, число пар последовательных вариантов равно n × m.','example':'Для 3 блюд и 4 напитков есть 3 × 4 = 12 сочетаний.','source':'OpenStax Contemporary Mathematics, 7.1','url':'https://openstax.org/books/contemporary-mathematics/pages/7-1-the-multiplication-rule-for-counting'},
 {'skill_id':'17','title':'Вероятность двух событий','explanation':'Для двух последовательных событий вероятность совместного наступления равна P(A) × P(B|A). Если события независимы, P(B|A) = P(B).','example':'Две независимые честные монеты: P(два орла) = 1/2 × 1/2 = 1/4.','source':'OpenStax Contemporary Mathematics, 7.9','url':'https://openstax.org/books/contemporary-mathematics/pages/7-9-conditional-probability-and-the-multiplication-rule'},
 {'skill_id':'294','title':'Площадь фигуры неправильной формы','explanation':'Разбейте фигуру на знакомые части без наложений, найдите площади частей и сложите их.','example':'Фигура из прямоугольников 3 × 4 и 2 × 5 имеет площадь 12 + 10 = 22 квадратные единицы.','source':'OpenStax Prealgebra 2e, 9.5','url':'https://openstax.org/books/prealgebra-2e/pages/9-5-solve-geometry-applications-circles-and-irregular-figures'},
 {'skill_id':'277','title':'Сложение и вычитание целых чисел','explanation':'Вычитание целого числа замените сложением противоположного числа, затем учтите знаки слагаемых.','example':'−3 − (−5) = −3 + 5 = 2.','source':'OpenStax Elementary Algebra 2e, 1.3','url':'https://openstax.org/books/elementary-algebra-2e/pages/1-3-add-and-subtract-integers'},
 {'skill_id':'81','title':'Показатель на единицу','explanation':'Показатель на одну единицу получают делением общего результата на число единиц исходной величины.','example':'120 км за 2 часа = 60 км за 1 час.','source':'OpenStax Prealgebra 2e, 5.6','url':'https://openstax.org/books/prealgebra-2e/pages/5-6-ratios-and-rate'},
]

# Original short self-check prompts. They do not record or grade answers.
_circle_practice=('Какой угол занимает сектор, соответствующий 20% целого?','72°')
PRACTICE_BY_SKILL = {
 '292':('Точка (1; 2) повернута на 90° против часовой стрелки вокруг начала координат. Каковы новые координаты?','(−2; 1)'),
 '290':('Отразите точку (4; −1) относительно оси Oy.','(−4; −1)'),
 '299':('Найдите полную площадь поверхности цилиндра при r = 1 и h = 2.','6π квадратных единиц'),
 '39':('Найдите площадь круга радиуса 4.','16π квадратных единиц'),
 **{sid:_circle_practice for sid in ('2_37_70','2_37_48_77','2_48_79','2_70')},
 '9_12':('Запишите диаграмму «стебель и листья» для чисел 23, 27, 31.','2 | 3 7; 3 | 1'),
 '16_17':('Есть 2 варианта первого блюда и 3 варианта второго. Сколько возможных пар?','6 пар'),
 '17':('Какова вероятность получить шестёрку на обоих из двух независимых честных кубиков?','1/36'),
 '294':('Фигура без наложений состоит из прямоугольников 3 × 4 и 2 × 5. Чему равна площадь?','22 квадратные единицы'),
 '277':('Вычислите −4 − (−7).','3'),
 '81':('Автомобиль проехал 150 км за 3 часа. Сколько километров приходится на 1 час?','50 км/ч'),
}

def add_practice(materials):
    """Add optional self-check fields without changing the persisted schema."""
    return [enrich_lesson({**m, **({'practice_question':PRACTICE_BY_SKILL[m['skill_id']][0],
                      'practice_answer':PRACTICE_BY_SKILL[m['skill_id']][1]}
                     if m['skill_id'] in PRACTICE_BY_SKILL else {})}) for m in materials]

def tokenize(s):
    suffixes=('ениями','ениями','ениями','ение','ения','ений','иями','ями','ами','ить','ать','еть',
              'ого','ому','ыми','ыми','овых','ами','ями','ией','ией','цию','ций','ции',
              'ов','ев','ей','ий','ый','ая','ое','ые','ую','юю','ах','ях','ом','ем','ой',
              'ам','ям','ия','ие','ии','ью','ы','и','а','я','е','о','у','ю','ь','й')
    out=[]
    for word in re.findall(r'[\w]+',s.lower()):
        if re.search('[а-яё]',word) and len(word)>4:
            for end in suffixes:
                if word.endswith(end) and len(word)-len(end)>=3:
                    word=word[:-len(end)];break
        out.append(word)
    return out

def search(query='',skill=None,limit=3,materials=MATERIALS):
    docs=[m for m in materials if skill is None or m['skill_id']==skill]
    if not docs:return []
    q=Counter(tokenize(query));N=len(materials)
    df=Counter(t for m in materials for t in set(tokenize(m['title']+' '+m['explanation']+' '+m['skill_id'])))
    def score(m):
        t=Counter(tokenize(m['title']+' '+m['explanation']+' '+m['skill_id']))
        title=set(tokenize(m['title']))
        exact=4 if query.strip().lower()==m['title'].lower() else 0
        return sum(v*(t.get(word,0)+2*(word in title))*math.log((N+1)/(df[word]+1)) for word,v in q.items()) + (5 if skill==m['skill_id'] else 0) + exact
    return sorted(docs,key=lambda m:(-score(m),m['skill_id']))[:limit]
