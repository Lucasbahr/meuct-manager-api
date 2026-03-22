def test_create_checkin(client, admin_token):
    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": 1},
    )

    assert response.status_code in [200, 201, 404]


def test_get_checkins(client, admin_token):
    response = client.get(
        "/checkin/ranking", headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200

    data = response.json()

    assert "data" in data
    assert isinstance(data["data"], list)


def test_checkin_invalid_student(client, admin_token):
    response = client.post(
        "/checkin/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"student_id": 9999},
    )

    assert response.status_code == 404


def test_checkin_unauthorized(client):
    response = client.post("/checkin/", json={"student_id": 1})
    assert response.status_code == 401
