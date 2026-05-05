"""工作流环节配置 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.workflow import WorkflowStageConfig
from app.schemas.response import ApiResponse
from app.utils.dependencies import get_current_user, require_admin, AnyUser
from app.utils.validators import generate_id

router = APIRouter(prefix="/workflow-config", tags=["工作流配置"])


class StageConfigCreate(BaseModel):
    name: str
    default_days: int
    review_items: list[str] = []


class StageConfigUpdate(BaseModel):
    name: Optional[str] = None
    default_days: Optional[int] = None
    review_items: Optional[list[str]] = None
    is_active: Optional[bool] = None


class StageReorder(BaseModel):
    """重新排序请求：按新顺序传入 stage ID 列表"""
    stage_ids: list[str]


@router.get("")
async def get_workflow_stages(
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取所有工作流环节配置（管理员和承包商都可查看）"""
    try:
        role_value = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
        if role_value not in ["admin", "contractor", "staff"]:
            raise HTTPException(status_code=403, detail="权限不足")
        
        result = await db.execute(
            select(WorkflowStageConfig)
            .where(WorkflowStageConfig.is_active == True)
            .order_by(WorkflowStageConfig.display_order)
        )
        stages = result.scalars().all()
        
        stages_data = [
            {
                "id": s.id,
                "name": s.name,
                "defaultDays": s.default_days,
                "displayOrder": s.display_order,
                "reviewItems": s.review_items or [],
                "isActive": s.is_active,
                "createdAt": s.created_at.isoformat() if s.created_at else None,
                "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in stages
        ]
        
        return ApiResponse(code=200, message="获取成功", data=stages_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_workflow_stage(
    stage_data: StageConfigCreate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """新增工作流环节"""
    try:
        # 获取当前最大顺序号
        result = await db.execute(
            select(func.max(WorkflowStageConfig.display_order))
        )
        max_order = result.scalar() or 0
        
        new_stage = WorkflowStageConfig(
            id=generate_id("wf"),
            name=stage_data.name,
            default_days=stage_data.default_days,
            display_order=max_order + 1,
            review_items=stage_data.review_items or [
                "内容安全合规性", "风格与品牌调性一致", "技术规格达标", "无版权/商标侵权风险"
            ],
            is_active=True
        )
        
        db.add(new_stage)
        await db.commit()
        await db.refresh(new_stage)
        
        return ApiResponse(code=201, message="环节创建成功", data={
            "id": new_stage.id,
            "name": new_stage.name,
            "defaultDays": new_stage.default_days,
            "displayOrder": new_stage.display_order,
            "reviewItems": new_stage.review_items,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{stage_id}")
async def update_workflow_stage(
    stage_id: str,
    stage_data: StageConfigUpdate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """修改工作流环节"""
    try:
        result = await db.execute(
            select(WorkflowStageConfig).where(WorkflowStageConfig.id == stage_id)
        )
        stage = result.scalar_one_or_none()
        
        if not stage:
            raise HTTPException(status_code=404, detail="环节不存在")
        
        if stage_data.name is not None:
            stage.name = stage_data.name
        if stage_data.default_days is not None:
            stage.default_days = stage_data.default_days
        if stage_data.review_items is not None:
            stage.review_items = stage_data.review_items
        if stage_data.is_active is not None:
            stage.is_active = stage_data.is_active
        
        await db.commit()
        await db.refresh(stage)
        
        return ApiResponse(code=200, message="更新成功", data={
            "id": stage.id,
            "name": stage.name,
            "defaultDays": stage.default_days,
            "displayOrder": stage.display_order,
            "reviewItems": stage.review_items,
            "isActive": stage.is_active,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{stage_id}")
async def delete_workflow_stage(
    stage_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除工作流环节（软删除，标记为 is_active=False）"""
    try:
        result = await db.execute(
            select(WorkflowStageConfig).where(WorkflowStageConfig.id == stage_id)
        )
        stage = result.scalar_one_or_none()
        
        if not stage:
            raise HTTPException(status_code=404, detail="环节不存在")
        
        stage.is_active = False
        await db.commit()
        
        return ApiResponse(code=200, message="环节已删除", data=None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reorder")
async def reorder_workflow_stages(
    reorder_data: StageReorder,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """调整工作流环节顺序"""
    try:
        for idx, stage_id in enumerate(reorder_data.stage_ids, start=1):
            result = await db.execute(
                select(WorkflowStageConfig).where(WorkflowStageConfig.id == stage_id)
            )
            stage = result.scalar_one_or_none()
            if stage:
                stage.display_order = idx
        
        await db.commit()
        
        return ApiResponse(code=200, message="排序更新成功", data=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
