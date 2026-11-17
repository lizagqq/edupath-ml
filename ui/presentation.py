"""Small, dependency-free view helpers for the Streamlit interface."""

from html import escape
import re


MIN_OBSERVATIONS = 3

# Literal, manually checked translations of source skill_name values. The
# English originals remain in the database; unmapped labels stay unchanged.
SOURCE_TRANSLATIONS = {
    "Rotations": "Повороты",
    "Reflection": "Отражение",
    "Surface Area Cylinder": "Площадь поверхности цилиндра",
    "Surface Area Rectangular Prism": "Площадь поверхности прямоугольного параллелепипеда",
    "Circle Graph": "Круговая диаграмма",
    "Counting Methods": "Методы подсчёта",
    "Box and Whisker": "Диаграмма «ящик с усами»",
    "Probability of Two Distinct Events": "Вероятность двух различных событий",
    "Stem and Leaf Plot": "Диаграмма «стебель и листья»",
    "Area Irregular Figure": "Площадь фигуры неправильной формы",
    "Pythagorean Theorem": "Теорема Пифагора",
    "Least Common Multiple": "Наименьшее общее кратное",
    "Mean": "Среднее арифметическое",
    "Volume Cylinder": "Объём цилиндра",
    "Table": "Таблица",
}


SOURCE_TRANSLATIONS.update({
    'Absolute Value': 'Модуль числа',
    'Addition Whole Numbers': 'Сложение целых неотрицательных чисел',
    'Addition and Subtraction Positive Decimals': 'Сложение и вычитание положительных десятичных дробей',
    'Algebraic Simplification': 'Упрощение алгебраических выражений',
    'Algebraic Solving': 'Решение алгебраических задач',
    'Angles - Obtuse, Acute, and Right': 'Острые, тупые и прямые углы',
    'Angles on Parallel Lines Cut by a Transversal': 'Углы при параллельных прямых и секущей',
    'Area Parallelogram': 'Площадь параллелограмма',
    'Area Rectangle': 'Площадь прямоугольника',
    'Area Trapezoid': 'Площадь трапеции',
    'Area Triangle': 'Площадь треугольника',
    'Calculations with Similar Figures': 'Вычисления для подобных фигур',
    'Choose an Equation from Given Information': 'Выбор уравнения по условию',
    'Circumference': 'Длина окружности',
    'Complementary and Supplementary Angles': 'Углы с суммой 90° и 180°',
    'Congruence': 'Равенство геометрических фигур',
    'Conversion of Fraction Decimals Percents': 'Перевод дробей, десятичных дробей и процентов',
    'Distributive Property': 'Распределительное свойство',
    'Divisibility Rules': 'Признаки делимости',
    'Effect of Changing Dimensions of a Shape Prportionally': 'Пропорциональное изменение размеров фигуры',
    'Equivalent Fractions': 'Равные дроби',
    'Estimation': 'Приближённая оценка',
    'Exponents': 'Степени',
    'Finding Slope From Equation': 'Угловой коэффициент по уравнению',
    'Finding Slope From Situation': 'Угловой коэффициент по условию',
    'Finding Slope from Ordered Pairs': 'Угловой коэффициент по координатам точек',
    'Greatest Common Factor': 'Наибольший общий делитель',
    'Histogram as Table or Graph': 'Гистограмма в таблице или на графике',
    'Interior Angles Figures with More than 3 Sides': 'Внутренние углы многоугольника',
    'Interior Angles Triangle': 'Внутренние углы треугольника',
    'Interpreting Coordinate Graphs': 'Чтение координатных графиков',
    'Median': 'Медиана', 'Midpoint': 'Середина отрезка',
    'Multiplication and Division Integers': 'Умножение и деление целых чисел',
    'Multiplication and Division Positive Decimals': 'Умножение и деление положительных десятичных дробей',
    'Nets of 3D Figures': 'Развёртки объёмных фигур',
    'Number Line': 'Числовая прямая',
    'Order of Operations +,-,/,* () positive reals': 'Порядок действий с положительными числами и скобками',
    'Order of Operations All': 'Порядок арифметических действий',
    'Ordering Fractions': 'Сравнение и упорядочивание дробей',
    'Ordering Integers': 'Сравнение и упорядочивание целых чисел',
    'Ordering Positive Decimals': 'Сравнение и упорядочивание десятичных дробей',
    'Parts of a Polyomial, Terms, Coefficient, Monomial, Exponent, Variable': 'Многочлен: слагаемые, коэффициент, степень и переменная',
    'Pattern Finding': 'Поиск закономерностей',
    'Percent Discount': 'Процентная скидка', 'Percents': 'Проценты',
    'Perimeter of a Polygon': 'Периметр многоугольника',
    'Polynomial Factors': 'Множители многочлена', 'Prime Number': 'Простые числа',
    'Probability of a Single Event': 'Вероятность одного события',
    'Quadratic Formula to Solve Quadratic Equation': 'Решение квадратного уравнения по формуле',
    'Range': 'Размах данных', 'Rate': 'Отношение величин',
    'Reading a Ruler or Scale': 'Чтение линейки или шкалы',
    'Recognize Linear Pattern': 'Распознавание линейной зависимости',
    'Recognize Quadratic Pattern': 'Распознавание квадратичной зависимости',
    'Rounding': 'Округление', 'Scale Factor': 'Коэффициент масштабирования',
    'Scatter Plot': 'Диаграмма рассеяния', 'Scientific Notation': 'Стандартная запись числа',
    'Simplifying Expressions positive exponents': 'Упрощение выражений с положительными показателями степени',
    'Solving Systems of Linear Equations': 'Решение систем линейных уравнений',
    'Solving Systems of Linear Equations by Graphing': 'Графическое решение систем линейных уравнений',
    'Solving for a variable': 'Выражение переменной', 'Square Root': 'Квадратный корень',
    'Subtraction Whole Numbers': 'Вычитание целых неотрицательных чисел',
    'Translations': 'Параллельный перенос',
    'Unit Conversion Within a System': 'Перевод единиц в одной системе измерения',
    'Venn Diagram': 'Диаграмма Венна',
    'Volume Rectangular Prism': 'Объём прямоугольного параллелепипеда',
    'Volume Sphere': 'Объём шара',
    'Write Linear Equation from Graph': 'Составление линейного уравнения по графику',
    'Write Linear Equation from Ordered Pairs': 'Составление линейного уравнения по координатам точек',
    'Write Linear Equation from Situation': 'Составление линейного уравнения по условию',
})


def skill_label(skill):
    """Prefer curated title, then the source dataset label; never invent a title."""
    skill_id = str(skill["skill_id"])
    for key in ("display_name", "skill_name"):
        name = str(skill.get(key) or "").strip()
        coded_slug = bool(re.match(r"^[A-Z]\.\d+(?:\.\d+)*-", name))
        if name and name != skill_id and not coded_slug and name.lower() not in {"nan", "none", "null", "na"}:
            return SOURCE_TRANSLATIONS.get(name, name), False
    return f"Навык ID {skill_id}", True


def split_skills(skills):
    enough = [s for s in skills if s["observations"] >= MIN_OBSERVATIONS]
    sparse = [s for s in skills if 0 < s["observations"] < MIN_OBSERVATIONS]
    unseen = [s for s in skills if s["observations"] == 0]
    return sorted(enough, key=lambda s: (s['predicted_probability'] is None, s['predicted_probability'] if s['predicted_probability'] is not None else 0)), sorted(
        sparse, key=lambda s: s["observations"], reverse=True
    ), sorted(unseen, key=lambda s: skill_label(s)[0])


def percent(value, digits=0):
    return "—" if value is None else f"{value * 100:.{digits}f} %".replace(".", ",")


def risk(probability):
    """Interface bands for the next-answer forecast, not a mastery diagnosis."""
    if probability < 0.5:
        return "Высокий риск", "high"
    if probability < 0.7:
        return "Умеренный риск", "medium"
    return "Низкий риск", "low"


def prediction_explanation(skill):
    count = skill["observations"]
    if count < MIN_OBSERVATIONS:
        return f"Есть только {count_phrase(count)} по теме; вывод требует новых наблюдений."
    _, missing = skill_label(skill)
    explanation = (
        f"Модель учитывает {count_phrase(count)} по этому навыку и общую историю ученика. "
        "Это прогноз правильности следующего ответа, а не оценка освоения темы."
    )
    if count < 10:
        explanation += " Ответов пока мало: это предварительный сигнал, который стоит проверить новым заданием."
    if missing:
        explanation += " Описание навыка в метаданных отсутствует."
    elif skill.get("skill_name") in SOURCE_TRANSLATIONS:
        explanation += f" Исходное название ASSISTments: {skill['skill_name']}."
    return explanation


def route_position_explanation(item, index, names):
    parents = [names.get(sid, f"Навык ID {sid}") for sid in item["prerequisites"]]
    if parents:
        return (
            f"Шаг {index}: сначала нужна предварительная тема «{'», «'.join(parents)}». "
            "После неё место среди доступных тем определяется баллом приоритета."
        )
    return (
        f"Шаг {index}: предварительная тема не требуется. "
        "Среди доступных тем место определяется баллом приоритета."
    )


def bar(label, value, tone="model", detail="", display=None):
    """Accessible horizontal bar with a full, wrapping label and visible value."""
    width = max(0, min(100, value * 100))
    return (
        '<div class="edubar">'
        f'<div class="edubar-head"><span>{escape(str(label))}</span>'
        f'<strong>{escape(display) if display is not None else percent(value, 1)}</strong></div>'
        f'<div class="edubar-track"><div class="edubar-fill {escape(tone)}" '
        f'style="width:{width:.1f}%"></div></div>'
        f'<div class="edubar-detail">{escape(str(detail))}</div>'
        '</div>'
    )


def count_phrase(number, one='ответ', few='ответа', many='ответов'):
    """Russian count forms, including 11–14 and numbers above 100."""
    ending = many if 11 <= number % 100 <= 14 else (one if number % 10 == 1 else few if number % 10 in (2, 3, 4) else many)
    return f'{number} {ending}'


def friendly_labels(skills):
    """Number duplicate records, not mathematical concepts; keep IDs in details."""
    groups = {}
    for skill in skills:
        title, missing = skill_label(skill)
        groups.setdefault('Тема без названия' if missing else title, []).append(skill['skill_id'])
    labels = {}
    for title, ids in groups.items():
        for index, sid in enumerate(sorted(ids), 1):
            labels[sid] = title if len(ids) == 1 else f'{title} · запись {index}'
    return labels


def learning_reason(item, names):
    if item['role'] == 'prerequisite':
        return 'Подготовка к следующей теме: здесь повторяем знания, которые понадобятся дальше.'
    probability = item['predicted_probability']
    if probability is None:
        return 'Тема включена в основной план; численный прогноз недоступен.'
    return (f"Прогноз правильного следующего ответа — {percent(probability)}. "
            f"В истории по теме {count_phrase(item['observations'])}.")
