from app.api.contractor import (
    ProfileUpdate,
    _apply_creator_profile_update,
    _serialize_creator_profile,
)


class _Staff:
    id = "staff-1"
    username = "internal-maker"
    email = "maker@example.com"
    phone = "13800000001"
    real_name = "内部制作者"
    company = "Unique Vision"
    created_at = None

    @property
    def role(self):
        return "staff"


def test_serialize_staff_creator_profile_uses_basic_internal_shape():
    profile = _serialize_creator_profile(_Staff())

    assert profile["creatorType"] == "staff"
    assert profile["isInternalCreator"] is True
    assert profile["realName"] == "内部制作者"
    assert profile["company"] == "Unique Vision"
    assert profile["address"] == ""
    assert profile["specialty"] == ""
    assert profile["expertise"] == ""
    assert profile["showcaseCases"] == []


def test_apply_staff_creator_profile_update_only_allows_basic_fields():
    staff = _Staff()
    _apply_creator_profile_update(
        staff,
        ProfileUpdate(
            email="new-maker@example.com",
            real_name="新名字",
            company="不应由个人设置修改",
            specialty="不应写入",
            showcase_cases=[{"url": "/demo.mp4"}],
        ),
    )

    assert staff.email == "new-maker@example.com"
    assert staff.real_name == "新名字"
    assert staff.company == "Unique Vision"
    assert not hasattr(staff, "specialty")
    assert not hasattr(staff, "showcase_cases")
