from app.services.production_asset_service import build_production_assets


def test_build_production_assets_collects_user_files_and_design_plan_files():
    assets = build_production_assets(
        {
            "scenePhotos": [
                {
                    "id": "scene-1",
                    "name": "现场照片.jpg",
                    "url": "/uploads/site/scene.jpg",
                    "type": "image/jpeg",
                }
            ],
            "materials": [
                {
                    "id": "material-1",
                    "name": "参考说明.pdf",
                    "url": "/uploads/materials/brief.pdf",
                    "mime_type": "application/pdf",
                }
            ],
            "selectedLibraryItem": {
                "id": "lib-1",
                "title": "资源库视频",
                "media": {
                    "type": "video",
                    "url": "/library/demo.mp4",
                    "poster": "/library/demo.jpg",
                },
            },
        },
        {
            "files": [
                {
                    "id": "plan-1",
                    "filename": "AI方案附件.pptx",
                    "url": "/uploads/plan/deck.pptx",
                    "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                }
            ]
        },
    )

    assert [asset["source"] for asset in assets] == [
        "scene_photos",
        "materials",
        "selected_library_item",
        "design_plan",
    ]
    assert [asset["kind"] for asset in assets] == ["image", "pdf", "video", "document"]
    assert assets[0]["label"] == "现场/参考文件"
    assert assets[1]["label"] == "相关材料"
    assert assets[2]["name"] == "资源库视频"
    assert assets[3]["name"] == "AI方案附件.pptx"


def test_build_production_assets_deduplicates_same_file_url():
    assets = build_production_assets(
        {
            "scenePhotos": [
                {"name": "same.pdf", "url": "/uploads/same.pdf"},
            ],
            "site_photos": [
                {"name": "same.pdf", "url": "/uploads/same.pdf"},
            ],
        }
    )

    assert len(assets) == 1
    assert assets[0]["kind"] == "pdf"
