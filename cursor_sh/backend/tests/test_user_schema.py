from app.schemas.user import UserCreate, UserUpdate


def test_user_create_treats_blank_optional_email_as_missing():
    user = UserCreate(
        username="staff_test",
        password="secret123",
        email="",
        phone="15802610941",
        realName="测试负责人",
        role="staff",
        isActive=True,
    )

    assert user.email is None


def test_user_update_treats_blank_optional_email_as_missing():
    user = UserUpdate(email="   ")

    assert user.email is None
