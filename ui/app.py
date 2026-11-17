"""Educational workspace over the existing Service: profile, analysis, learning plan."""
import os
from html import escape

import requests
import streamlit as st

from src.api.contracts import APP_VERSION, ContractError
from ui.api_client import fetch_json, fetch_plan
from ui.presentation import count_phrase, friendly_labels, percent, skill_label, split_skills, learning_reason

API = os.getenv('EDUPATH_API', 'http://127.0.0.1:8000').rstrip('/')
PAGES = ('Профиль ученика', 'Анализ знаний', 'План обучения')
st.set_page_config(page_title='EduPath · план обучения', page_icon='📖', layout='wide')
st.markdown('''<style>
.block-container {max-width:1040px;padding-top:1.5rem;padding-bottom:3rem;}
h1,h2,h3 {letter-spacing:-.02em;overflow-wrap:anywhere;}
h1 {font-size:2rem!important;} h2 {font-size:1.65rem!important;} h3 {font-size:1.2rem!important;}
.edu-brand {color:#276b61;font-weight:750;letter-spacing:.06em;font-size:.85rem;margin-bottom:.7rem;}
.edu-intro {color:#50616c;line-height:1.6;margin-bottom:1.3rem;}
.edu-stats {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:1rem 0 1.5rem;}
.edu-stat {background:#f4f8f7;border:1px solid #dde8e4;border-radius:14px;padding:18px;min-width:0;}
.edu-stat strong {display:block;font-size:1.9rem;color:#184b43;margin:.3rem 0;}
.edu-stat span {color:#42564f;font-size:.95rem;overflow-wrap:anywhere;}
.edu-stat small {display:block;color:#596a64;line-height:1.5;}
.edu-topic {border-bottom:1px solid #e2e8e5;padding:.8rem 0;overflow-wrap:anywhere;}
.edu-topic strong {display:block;color:#223e38;margin-bottom:.35rem;}
.edu-topic p {color:#52635d;margin:0;line-height:1.55;}
.edu-summary {background:#eef6f2;border-left:4px solid #438374;border-radius:0 12px 12px 0;padding:1rem 1.2rem;margin:.8rem 0 1.2rem;}
.edu-summary p {margin:.4rem 0;line-height:1.65;}
.edu-tag {color:#386858;font-weight:650;font-size:.85rem;margin-top:.8rem;}
div[data-testid="stRadio"] label {white-space:normal;overflow-wrap:anywhere;}
div[data-testid="stHorizontalBlock"] {flex-wrap:wrap;}
@media(max-width:640px) {
 .block-container {padding:1rem 1rem 2rem;}
 .edu-stats {grid-template-columns:1fr;gap:10px;}
 h1 {font-size:1.6rem!important;}
 div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {width:100%!important;flex:1 1 100%!important;min-width:0!important;}
}
</style>''', unsafe_allow_html=True)


@st.cache_data(ttl=30)
def student_choices(base):
    return fetch_json(base, '/students?limit=100')


def go_to_plan():
    st.session_state.page = PAGES[2]


def choose_step(key, value):
    st.session_state[key] = value


def remember_step(uid, sid, widget_key):
    marks = st.session_state.setdefault('completed_steps', {})
    completed = set(marks.get(uid, []))
    if st.session_state[widget_key]:
        completed.add(sid)
    else:
        completed.discard(sid)
    marks[uid] = sorted(completed)


def connection_help():
    with st.expander('Как восстановить соединение'):
        st.write('Остановите старые процессы API и Streamlit сочетанием Ctrl+C. '
                 'Запустите оба из корня этого проекта в двух терминалах; обучение запускать не нужно.')
        st.code('.venv/bin/python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000')
        st.code('EDUPATH_API=http://127.0.0.1:8000 .venv/bin/python -m streamlit run ui/app.py')
        st.caption(f'Адрес API: {API}')


st.markdown('<div class="edu-brand">EDUPATH · УЧИМСЯ ПО ШАГАМ</div>', unsafe_allow_html=True)
try:
    students = student_choices(API)
    if not students:
        st.info('В истории пока нет учеников.'); st.stop()
except (requests.RequestException, ContractError) as exc:
    st.error(f'Не удалось получить список учеников. {exc}')
    connection_help(); st.stop()

st.sidebar.header('Ученики')
selected = st.sidebar.selectbox('Выберите ученика', students)
st.sidebar.caption('Профиль и план относятся к выбранному ученику.')
with st.sidebar.expander('О системе'):
    st.write('Анализ сохранённой истории математических ответов ASSISTments. '
             'План помогает выбрать повторение и не заменяет оценку преподавателя.')
    st.caption(f'EduPath ML {APP_VERSION}. Новые оцениваемые ответы здесь не собираются.')

try:
    # The plan includes its profile. One validated HTTP snapshot prevents mixed data.
    data = fetch_plan(API, selected)
except ContractError as exc:
    st.error(str(exc)); connection_help(); st.stop()
except requests.RequestException as exc:
    st.error(f'Не удалось загрузить данные ученика. {exc}')
    connection_help(); st.stop()

if st.session_state.get('page') not in PAGES:
    st.session_state.page = PAGES[0]
st.radio('Раздел', PAGES, key='page', horizontal=True, label_visibility='collapsed')
st.caption(f'Выбран ученик {selected}')
enough, sparse, unseen = split_skills(data['skills'])
labels = friendly_labels(data['skills'])
by_id = {s['skill_id']: s for s in data['skills']}
route = data['trajectory']
difficulties = data['detected_difficulties']


def title(item):
    return labels[item['skill_id']]


def topic_line(item):
    p = item['predicted_probability']
    reason = f"Прогноз следующего правильного ответа — {percent(p)}; в истории {count_phrase(item['observations'])}."
    st.markdown(f'<div class="edu-topic"><strong>{escape(title(item))}</strong><p>{escape(reason)}</p></div>', unsafe_allow_html=True)


def table(items):
    return [{'Тема': title(s), 'Ответов': s['observations'],
             'Правильно раньше': percent(s['observed_accuracy'], 1),
             'Прогноз следующего ответа': percent(s['predicted_probability'], 1),
             'Основание': 'Нет ответов' if s['observations'] == 0 else
             'Истории недостаточно' if s['observations'] < 3 else
             'Предварительный сигнал' if s['observations'] < 10 else 'Есть история ответов'} for s in items]


if st.session_state.page == PAGES[0]:
    st.title('Профиль ученика')
    st.markdown('<p class="edu-intro">Посмотрите, что уже есть в истории ответов и какие темы стоит повторить. '
                'Персональный план поможет перейти от результатов к занятиям.</p>', unsafe_allow_html=True)
    stats = [('Ответов на задания', f"{data['responses']:,}".replace(',', ' '), 'Записи в сохранённой истории'),
             ('Правильные ответы', percent(data['observed_accuracy'], 1), 'Доля от всех ответов ученика'),
             ('Темы с ответами', str(len(enough) + len(sparse)), 'Есть хотя бы одно наблюдение'),
             ('Темы с достаточной историей', str(len(enough)), 'Не менее трёх ответов; это не отметка об освоении')]
    st.markdown('<div class="edu-stats">' + ''.join(
        f'<div class="edu-stat"><span>{escape(label)}</span><strong>{escape(value)}</strong><small>{escape(note)}</small></div>'
        for label, value, note in stats) + '</div>', unsafe_allow_html=True)
    st.subheader('На что обратить внимание')
    if difficulties:
        for item in difficulties[:3]:
            topic_line(item)
        st.caption('При 3–9 ответах вывод предварительный. Прогноз помогает выбрать повторение, а не подтверждает пробел в знаниях.')
    else:
        st.info('По темам с достаточной историей низких прогнозов пока не выявлено.')
    st.button('Открыть персональный план →', key='open_plan', type='primary', on_click=go_to_plan)
    st.caption(f"В плане {count_phrase(len(route), 'шаг', 'шага', 'шагов')}. "
               'Темы без подготовленных материалов показаны отдельно.')

elif st.session_state.page == PAGES[1]:
    st.title('Анализ знаний')
    st.write('«Правильно раньше» — доля правильных ответов в истории. «Прогноз» — вероятность правильного '
             'следующего ответа по теме. Оба показателя полезны вместе с числом наблюдений.')
    st.caption('При 3–9 ответах сигнал предварительный; 1–2 ответа не участвуют в отборе слабых тем. '
               'Названия «запись 1», «запись 2» различают отдельные записи с одинаковым названием, не разные виды задач.')
    st.subheader('Темы, требующие внимания')
    if difficulties:
        st.dataframe(table(difficulties), hide_index=True, width='stretch')
    else:
        st.info('Низких прогнозов по темам с тремя и более ответами нет.')
    with st.expander(f'Все темы с достаточной историей · {len(enough)}'):
        if enough: st.dataframe(table(enough), hide_index=True, width='stretch')
    with st.expander(f'Мало ответов · {len(sparse)}'):
        if sparse: st.dataframe(table(sparse), hide_index=True, width='stretch')
    with st.expander(f'Темы без ответов · {len(unseen)}'):
        st.caption('У этих тем нет личной практики ученика. Прогноз модели приведён для полноты и не участвует в диагностике.')
        if unseen: st.dataframe(table(unseen), hide_index=True, width='stretch')
    with st.expander('Подробности отдельной записи'):
        sid = st.selectbox('Тема', [s['skill_id'] for s in data['skills']], format_func=lambda value: labels[value], key='detail_skill')
        skill = by_id[sid]
        st.write(f"Идентификатор: {sid}. Исходное название: {skill['skill_name']}.")
        st.write(f"{count_phrase(skill['observations']).capitalize()}. Правильно раньше: {percent(skill['observed_accuracy'], 1)}. "
                 f"Прогноз: {percent(skill['predicted_probability'], 1)}.")
        if skill_label(skill)[1]: st.caption('Исходное описание отсутствует: содержание темы не предполагается по одному идентификатору.')
    st.button('Перейти к плану обучения →', on_click=go_to_plan, type='primary')

else:
    st.title('План обучения')
    focus = [item for item in route if item['role'] == 'focus']
    preparation = [item for item in route if item['role'] == 'prerequisite']
    if route:
        st.markdown(f'<div class="edu-summary"><p><b>Повторить: {count_phrase(len(route), "тему", "темы", "тем")}.</b> '
                    f'По результатам диагностики — {len(focus)}, для подготовки — {len(preparation)}.</p>'
                    f'<p><b>Выявлены затруднения:</b> {escape("; ".join(title(x) for x in focus))}.</p>'
                    f'<p><b>Предварительные знания:</b> {escape("; ".join(title(x) for x in preparation) or "дополнительная подготовка не добавлена")}.</p>'
                    '<p>Сначала повторяем темы с наиболее низкими прогнозами среди доступных. '
                    'Если нужна предварительная тема, проходим её раньше зависимой.</p></div>', unsafe_allow_html=True)
        st.write('Начните с первого шага: прочитайте объяснение, разберите пример, затем решите задания самостоятельно.')
        st.caption('При 3–9 ответах сигнал предварительный. Отметки ниже сохраняются только в текущей сессии: '
                   'они не подтверждают освоение и не меняют прогнозы.')
        marks = st.session_state.setdefault('completed_steps', {})
        completed = set(marks.get(selected, []))
        done = sum(x['skill_id'] in completed for x in route)
        st.progress(done / len(route), text=f'Отмечено шагов: {done} из {len(route)}')
        step_key = f'active_step_{selected}'
        index = st.radio('Шаги плана', list(range(len(route))),
                         format_func=lambda i: f'{i + 1}. {title(route[i])}',
                         key=step_key)
        item = route[index]; material = item['material']; sid = item['skill_id']
        st.markdown('<div class="edu-tag">' + ('ПРЕДВАРИТЕЛЬНАЯ ТЕМА' if item['role'] == 'prerequisite' else 'ПОВТОРЕНИЕ ПО РЕЗУЛЬТАТАМ') + '</div>', unsafe_allow_html=True)
        st.header(f'{index + 1}. {title(item)}')
        if item['role'] == 'prerequisite':
            children = [title(child) for child in route if sid in child['prerequisites']]
            st.write('**Почему здесь:** ' + ('Перед темой «' + '», «'.join(children) + '» нужна эта основа.' if children else learning_reason(item, labels)))
        else:
            st.write('**Почему здесь:** ' + learning_reason(item, labels))
        st.write('**Цель:** ' + material['learning_goal'])
        st.subheader('Разберём тему')
        st.write(material['theory'])
        st.subheader('Пример с решением')
        st.write(material['worked_example']['question'])
        st.info(material['worked_example']['solution'])
        st.subheader('Попробуйте самостоятельно')
        for n, exercise in enumerate(material['practice_exercises'], 1):
            st.write(f"**Задание {n}.** {exercise['question']}")
            with st.expander(f'Ответ и решение · задание {n}'):
                st.write('**Ответ:** ' + exercise['answer'])
                st.write(exercise['solution'])
        st.markdown(f"[Дополнительный материал: {material['source']}]({material['url']})")
        with st.expander('На чём основана рекомендация'):
            st.write(f"Запись навыка: {sid}. {count_phrase(item['observations']).capitalize()}.")
            if item['predicted_probability'] is not None:
                st.write(f"Прогноз следующего ответа: {percent(item['predicted_probability'], 1)}. "
                         f"Правильно раньше: {percent(item['observed_accuracy'], 1)}.")
            else:
                st.write('Численный прогноз для этой темы недоступен.')
            st.caption('При малом числе наблюдений вывод требует дополнительной проверки преподавателем.')
        mark_key = f'mark_{selected}_{sid}'
        st.checkbox('Я разобрал(а) этот шаг', value=sid in completed, key=mark_key,
                    on_change=remember_step, args=(selected, sid, mark_key))
        previous, following = st.columns(2)
        with previous:
            if index > 0:
                st.button('← Предыдущий шаг', on_click=choose_step, args=(step_key, index - 1), width='stretch')
        with following:
            if index + 1 < len(route):
                st.button(f'Следующий шаг: {title(route[index + 1])} →', key='next_step', type='primary',
                          on_click=choose_step, args=(step_key, index + 1), width='stretch')
            else:
                st.success('Это последний шаг. Обсудите оставшиеся вопросы с преподавателем.')
    else:
        st.info(data['trajectory_note'])
    if data['reinforcement']:
        with st.expander('Что можно повторить после основного плана'):
            st.caption('Эти темы отложены, чтобы основной план оставался коротким. Одноимённые записи сохраняют отдельные результаты.')
            for item in data['reinforcement']:
                topic_line(item)
                if item['material']:
                    st.markdown(f"[Учебный источник]({item['material']['url']})")
    if data['without_materials']:
        with st.expander(f"Другие затруднения: материалы пока не подготовлены · {len(data['without_materials'])}"):
            st.write('Эти темы выявлены по истории ответов, но не включены в план: в библиотеке нет связанного с ними '
                     'материала. Обсудите их с преподавателем. Для записей без названия содержание неизвестно.')
            st.dataframe(table(data['without_materials']), hide_index=True, width='stretch')
            st.caption('Точные идентификаторы доступны в «Анализе знаний» → «Подробности отдельной записи».')
