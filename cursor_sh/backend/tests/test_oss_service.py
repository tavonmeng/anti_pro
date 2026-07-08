from app.services import oss_service


def test_get_signed_url_passes_response_params_to_oss(monkeypatch):
    captured = {}

    class FakeBucket:
        def sign_url(self, method, key, expires, headers=None, params=None, slash_safe=False, additional_headers=None):
            captured.update(
                {
                    "method": method,
                    "key": key,
                    "expires": expires,
                    "params": params,
                    "slash_safe": slash_safe,
                }
            )
            return "http://bucket.oss-cn-beijing.aliyuncs.com/deliverables/demo.pdf?signature=abc"

    monkeypatch.setattr(oss_service, "_get_bucket", lambda: FakeBucket())
    monkeypatch.setattr(oss_service, "_rewrite_to_public_endpoint", lambda url: url)

    url = oss_service.get_signed_url(
        "deliverables/demo.pdf",
        expires=600,
        response_params={
            "response-content-type": "application/pdf",
            "response-content-disposition": "inline",
        },
    )

    assert url.startswith("https://")
    assert captured == {
        "method": "GET",
        "key": "deliverables/demo.pdf",
        "expires": 600,
        "params": {
            "response-content-type": "application/pdf",
            "response-content-disposition": "inline",
        },
        "slash_safe": True,
    }
