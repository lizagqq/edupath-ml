"""Shared, dependency-free wire contract. Reject stale responses before rendering."""
import math

TRAJECTORY_CONTRACT_VERSION = 2
APP_VERSION = '0.2.0'


class ContractError(ValueError):
    pass


def validate_trajectory(data):
    """Validate required UI data, including nested lesson content; never fill gaps."""
    def fail(path):
        raise ContractError(f'Несовместимый ответ API: {path}. Ожидается контракт '
                            f'{TRAJECTORY_CONTRACT_VERSION}. Перезапустите API и интерфейс из одной версии проекта.')

    def fields(obj, names, path):
        if not isinstance(obj, dict): fail(path + ' должен быть объектом')
        missing = set(names) - obj.keys()
        if missing: fail(path + ': отсутствуют ' + ', '.join(sorted(missing)))

    def text(value, path):
        if not isinstance(value, str) or not value.strip(): fail(path + ': ожидается непустой текст')

    def strings(values, path):
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values): fail(path + ': ожидается список ID')

    def number(value, path, nullable=False):
        if value is None and nullable: return
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            fail(path + ': ожидается вероятность от 0 до 1')

    def count(value, path):
        if type(value) is not int or value < 0: fail(path + ': ожидается неотрицательное целое')

    def sequence(obj, name, path):
        if not isinstance(obj[name], list): fail(path + '.' + name + ': ожидается список')

    def skill(obj, path):
        fields(obj, ('skill_id', 'skill_name', 'observations', 'observed_accuracy', 'predicted_probability'), path)
        text(obj['skill_id'], path + '.skill_id')
        text(obj['skill_name'], path + '.skill_name')
        count(obj['observations'], path + '.observations')
        number(obj['predicted_probability'], path + '.predicted_probability', nullable=True)
        number(obj['observed_accuracy'], path + '.observed_accuracy', nullable=True)

    required = ('contract_version', 'user_id', 'responses', 'observed_accuracy', 'skills',
                'trajectory', 'trajectory_note', 'detected_difficulties', 'without_materials',
                'reinforcement', 'focus_skill_ids', 'prerequisite_skill_ids', 'material_count', 'selection_rule')
    fields(data, required, 'trajectory')
    if type(data['contract_version']) is not int or data['contract_version'] != TRAJECTORY_CONTRACT_VERSION:
        fail('contract_version')
    text(data['user_id'], 'user_id')
    text(data['trajectory_note'], 'trajectory_note')
    for name in ('focus_skill_ids', 'prerequisite_skill_ids'): strings(data[name], name)
    count(data['responses'], 'responses'); count(data['material_count'], 'material_count')
    number(data['observed_accuracy'], 'observed_accuracy', nullable=True)
    for name in ('skills', 'trajectory', 'detected_difficulties', 'without_materials',
                 'reinforcement', 'focus_skill_ids', 'prerequisite_skill_ids'):
        sequence(data, name, 'trajectory')
    ids = set()
    for obj in data['skills']:
        skill(obj, 'skills[]')
        if obj['skill_id'] in ids: fail('skills: повтор ID')
        ids.add(obj['skill_id'])
    selected = set()
    for step in data['trajectory']:
        skill(step, 'trajectory[]')
        fields(step, ('role', 'reason', 'prerequisites', 'all_prerequisites', 'material', 'priority', 'evidence_note'), 'trajectory[]')
        if step['role'] not in ('focus', 'prerequisite'): fail('trajectory[].role')
        if step['skill_id'] not in ids or step['skill_id'] in selected: fail('trajectory[].skill_id')
        strings(step['prerequisites'], 'trajectory[].prerequisites')
        text(step['reason'], 'trajectory[].reason')
        if not set(step['prerequisites']) <= selected: fail('trajectory: нарушен порядок предварительных тем')
        selected.add(step['skill_id'])
        material = step['material']
        fields(material, ('skill_id', 'title', 'explanation', 'example', 'source', 'url',
                          'learning_goal', 'theory', 'worked_example', 'practice_exercises'), 'material')
        if material['skill_id'] != step['skill_id']: fail('material.skill_id')
        for name in ('title', 'source', 'url', 'learning_goal', 'theory'): text(material[name], 'material.' + name)
        fields(material['worked_example'], ('question', 'solution'), 'worked_example')
        for name in ('question', 'solution'): text(material['worked_example'][name], 'worked_example.' + name)
        sequence(material, 'practice_exercises', 'material')
        if not 1 <= len(material['practice_exercises']) <= 2: fail('practice_exercises: требуется 1–2 задания')
        for exercise in material['practice_exercises']:
            fields(exercise, ('question', 'answer', 'solution'), 'practice_exercises[]')
            for name in ('question', 'answer', 'solution'): text(exercise[name], 'practice_exercises[].' + name)
    for name in ('detected_difficulties', 'without_materials', 'reinforcement'):
        for obj in data[name]:
            skill(obj, name + '[]')
            fields(obj, ('material_available', 'material'), name + '[]')
            if obj['skill_id'] not in ids: fail(name + '[].skill_id')
            if type(obj['material_available']) is not bool: fail(name + '[].material_available')
            if obj['material_available']:
                fields(obj['material'], ('skill_id', 'url'), name + '[].material')
                text(obj['material']['url'], name + '[].material.url')
                if obj['material']['skill_id'] != obj['skill_id']: fail(name + '[].material.skill_id')
            elif obj['material'] is not None:
                fail(name + '[]: материал указан при material_available=false')
    for role, key in (('focus', 'focus_skill_ids'), ('prerequisite', 'prerequisite_skill_ids')):
        if set(data[key]) != {step['skill_id'] for step in data['trajectory'] if step['role'] == role}:
            fail(key + ': роли не совпадают с шагами')
    if set(data['focus_skill_ids']) | set(data['prerequisite_skill_ids']) != selected:
        fail('trajectory: состав основных и предварительных тем не совпадает с шагами')
    return data
