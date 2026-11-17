"""Exercise all educational pages against live HTTP, real ASGI, or local Service."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('EDUPATH_API', 'http://127.0.0.1:8000')
PAGES = ('Профиль ученика', 'Анализ знаний', 'План обучения')


class LocalResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.data


def local_get(service, url, timeout=15):
    path = urlsplit(url).path
    query = parse_qs(urlsplit(url).query)
    if path == '/students':
        return LocalResponse(service.students(int(query.get('limit', ['20'])[0])))
    if path.startswith('/students/') and path.endswith('/trajectory'):
        return LocalResponse(service.trajectory(path.split('/')[2]))
    raise AssertionError(f'Unexpected UI request: {url}')


def asgi_get(url, timeout=15):
    from scripts.smoke_asgi import get
    status, data = asyncio.run(get(url))
    return LocalResponse(data, status)


def check(at):
    assert not at.exception, [x.message for x in at.exception]
    assert not at.error, [x.value for x in at.error]


def exercise():
    at = AppTest.from_file(str(ROOT / 'ui/app.py'), default_timeout=30).run()
    check(at)
    assert at.sidebar.selectbox[0].value == '79021'
    assert tuple(at.radio[0].options) == PAGES
    assert any('<strong>93</strong>' in x.value and '<strong>56</strong>' in x.value for x in at.markdown)
    assert not any('Изученных навыков' in x.value for x in at.markdown)
    next(b for b in at.button if b.key == 'open_plan').click().run()
    check(at)
    assert at.radio[0].value == PAGES[2]
    assert len(at.radio[1].options) == 5
    assert 'Повороты фигур' in at.header[0].value
    assert len(at.checkbox) == 1
    at.checkbox[0].check().run()
    check(at)
    assert '292' in at.session_state['completed_steps']['79021']
    next(b for b in at.button if b.key == 'next_step').click().run()
    check(at)
    assert 'Отражение фигур' in at.header[0].value
    for step, topic in enumerate(['Повороты фигур', 'Отражение фигур', 'Круговые диаграммы', 'Площадь круга', 'Площадь поверхности цилиндра']):
        at.radio[1].set_value(step).run(); check(at)
        assert topic in at.header[0].value
        assert any('Ответ и решение' in x.label for x in at.expander)
        assert any('Цель:' in x.value for x in at.markdown)
        if step == 3:
            assert any('Перед темой «Площадь поверхности цилиндра»' in x.value for x in at.markdown)
    # Marking a later step must not change the selected step.
    at.radio[1].set_value(3).run(); check(at)
    at.checkbox[0].check().run(); check(at)
    assert at.radio[1].value == 3
    at.radio[0].set_value(PAGES[1]).run(); check(at)
    table = at.dataframe[0].value
    assert len(table) == 17
    circles = [x for x in table['Тема'] if 'Круговые диаграммы' in x]
    assert len(circles) >= 2 and len(circles) == len(set(circles))
    assert len(at.selectbox[0].options) == 149  # full individual records remain accessible
    for uid, expected in [('75169', 2), ('78970', 4)]:
        at.sidebar.selectbox[0].set_value(uid).run(); check(at)
        for page in PAGES:
            at.radio[0].set_value(page).run(); check(at)
            if page == PAGES[2]:
                assert len(at.radio[1].options) == expected
                for step in range(expected):
                    at.radio[1].set_value(step).run(); check(at)
                    assert any('Ответ и решение' in x.label for x in at.expander)
    at.sidebar.selectbox[0].set_value('79021').run(); check(at)
    assert '292' in at.session_state['completed_steps']['79021']
    at.radio[1].set_value(0).run(); check(at)
    assert at.checkbox[0].value is True
    assert '75169' not in at.session_state['completed_steps']
    return {'sections': PAGES, 'students_checked': ['79021', '75169', '78970'],
            'route_steps': {'79021': 5, '75169': 2, '78970': 4},
            'profile_79021': {'observed_skills': 93, 'sufficient_skills': 56},
            'step_navigation': 'passed', 'session_marks_isolated_by_student': True,
            'all_recommended_lessons_opened': True, 'browser_visual_check': 'not performed'}


def stale_response_check(getter):
    """Simulate the reported stale API, keeping actual current serialized data."""
    def stale(url, timeout=15):
        response = getter(url, timeout=timeout)
        if urlsplit(url).path.endswith('/trajectory'):
            body = dict(response.json())
            for name in ('detected_difficulties', 'material_count'):
                body.pop(name)
            return LocalResponse(body)
        return response
    with patch('requests.get', side_effect=stale):
        at = AppTest.from_file(str(ROOT / 'ui/app.py'), default_timeout=30).run()
    assert not at.exception
    assert at.error and 'detected_difficulties' in at.error[0].value and 'material_count' in at.error[0].value
    assert 'Перезапустите' in at.error[0].value
    return 'rejected before rendering, both missing fields reported'


def main():
    p = argparse.ArgumentParser()
    group = p.add_mutually_exclusive_group()
    group.add_argument('--local-service', action='store_true')
    group.add_argument('--asgi', action='store_true', help='Feed actual FastAPI serialized responses to UI; no sockets.')
    args = p.parse_args()
    if args.asgi:
        async def direct(func, *a, **kw): return func(*a, **kw)
        with patch('fastapi.routing.run_in_threadpool', direct):
            with patch('requests.get', side_effect=asgi_get): result = exercise()
            result['stale_api_regression'] = stale_response_check(asgi_get)
        result['mode'] = 'FastAPI ASGI -> JSON -> HTTP client validation -> Streamlit AppTest; direct handler shim, no sockets'
        target = ROOT / 'reports/streamlit_asgi_integration.json'
    elif args.local_service:
        from src.api.service import Service
        service = Service()
        getter = lambda url, timeout=15: local_get(service, url, timeout)
        with patch('requests.get', side_effect=getter): result = exercise()
        result['stale_api_regression'] = stale_response_check(getter)
        result['mode'] = 'local-service; no HTTP'
        target = ROOT / 'reports/streamlit_apptest_local.json'
    else:
        result = exercise()
        result['mode'] = 'live HTTP API -> Streamlit AppTest; browser not tested'
        target = ROOT / 'reports/streamlit_apptest.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
