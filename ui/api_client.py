"""HTTP boundary: no cache for learner data, explicit contract compatibility."""
import requests
from src.api.contracts import validate_trajectory, ContractError


def fetch_json(base, path):
    response = requests.get(base.rstrip('/') + path, timeout=15)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as exc:
        raise ContractError('API вернул ответ, который не является JSON. Проверьте адрес сервера.') from exc


def fetch_plan(base, user_id):
    data = validate_trajectory(fetch_json(base, f'/students/{user_id}/trajectory'))
    if data['user_id'] != user_id:
        raise ContractError('API вернул данные другого ученика. Обновите страницу и проверьте сервер.')
    return data
