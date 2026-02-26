from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_mvp_smoke_flow():
    suffix = uuid4().hex[:8]
    admin_username = f'smoke_admin_{suffix}'
    user_username = f'smoke_user_{suffix}'

    with TestClient(app) as client:
        register_admin = client.post('/api/v1/auth/register', json={'username': admin_username, 'password': 'secret123'})
        assert register_admin.status_code == 201
        admin_token = register_admin.json()['access_token']

        register_user = client.post('/api/v1/auth/register', json={'username': user_username, 'password': 'secret123'})
        assert register_user.status_code == 201

        headers = {'Authorization': f'Bearer {admin_token}'}

        create_group = client.post('/api/v1/groups', json={'name': 'smoke-group', 'settings': {}}, headers=headers)
        assert create_group.status_code == 201
        group_id = create_group.json()['id']

        add_member = client.post(f'/api/v1/groups/{group_id}/members', json={'username': user_username}, headers=headers)
        assert add_member.status_code == 201

        send_message = client.post(f'/api/v1/groups/{group_id}/messages', json={'content': 'hola'}, headers=headers)
        assert send_message.status_code == 201

        history = client.get(f'/api/v1/groups/{group_id}/messages', headers=headers)
        assert history.status_code == 200
        assert len(history.json()) >= 1
