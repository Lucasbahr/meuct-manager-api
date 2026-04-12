from fastapi import status


def test_admin_create_and_public_list_feed(client, admin_token):
    response = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "tipo": "evento",
            "titulo": "Evento UFC",
            "descricao": "Luta do mês",
            "evento_data": "2026-01-15",
            "local": "São Paulo",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    created = response.json()["data"]
    assert created["titulo"] == "Evento UFC"
    item_id = created["id"]

    public = client.get("/feed/?academia_id=1")
    assert public.status_code == status.HTTP_200_OK
    items = public.json()["data"]
    assert any(i["id"] == item_id for i in items)


def test_like_unlike_and_liked_by_me(client, admin_token, user_token):
    create = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tipo": "evento", "titulo": "Evento X"},
    )
    assert create.status_code == status.HTTP_200_OK
    item_id = create.json()["data"]["id"]

    like = client.post(
        f"/feed/{item_id}/likes",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert like.status_code == status.HTTP_200_OK
    assert like.json()["data"]["liked"] is True
    assert like.json()["data"]["like_count"] == 1

    feed = client.get(
        "/feed/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert feed.status_code == status.HTTP_200_OK
    items = feed.json()["data"]
    item = next(i for i in items if i["id"] == item_id)
    assert item["liked_by_me"] is True

    unlike = client.delete(
        f"/feed/{item_id}/likes",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert unlike.status_code == status.HTTP_200_OK
    assert unlike.json()["data"]["like_count"] == 0


def test_add_comment_and_list_comments(client, admin_token, user_token):
    create = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"tipo": "luta", "titulo": "Luta Y"},
    )
    assert create.status_code == status.HTTP_200_OK
    item_id = create.json()["data"]["id"]

    comment = client.post(
        f"/feed/{item_id}/comments",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"conteudo": "Vai dar merda!!"},
    )
    assert comment.status_code == status.HTTP_200_OK
    assert comment.json()["data"]["conteudo"] == "Vai dar merda!!"

    comments = client.get(f"/feed/{item_id}/comments?academia_id=1")
    assert comments.status_code == status.HTTP_200_OK
    data = comments.json()["data"]
    assert any(c["id"] == comment.json()["data"]["id"] for c in data)


def test_create_feed_with_imagem_link_roundtrip(client, admin_token, user_token):
    url = "https://example.com/fight"
    create = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "tipo": "evento",
            "titulo": "Post com link na foto",
            "imagem_link": url,
        },
    )
    assert create.status_code == status.HTTP_200_OK
    assert create.json()["data"]["imagem_link"] == url
    item_id = create.json()["data"]["id"]

    feed = client.get(
        "/feed/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert feed.status_code == status.HTTP_200_OK
    item = next(i for i in feed.json()["data"] if i["id"] == item_id)
    assert item.get("imagem_link") == url

    clear = client.put(
        f"/feed/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"imagem_link": None},
    )
    assert clear.status_code == status.HTTP_200_OK
    assert clear.json()["data"].get("imagem_link") is None


def test_create_feed_without_tipo_defaults_evento(client, admin_token):
    response = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"titulo": "Post sem tipo"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["tipo"] == "evento"


def test_create_feed_accepts_calendar_datetime_string(client, admin_token):
    response = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "tipo": "evento",
            "titulo": "Com data calendario",
            "evento_data": "2026-04-01T00:00:00.000Z",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["evento_data"] == "2026-04-01"


def test_create_feed_rejects_invalid_date(client, admin_token):
    response = client.post(
        "/feed/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "tipo": "evento",
            "titulo": "Data errada",
            "evento_data": "31-02-2026",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

