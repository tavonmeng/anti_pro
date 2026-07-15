"""订单服务"""

import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List, Optional, Union
from datetime import datetime

from app.models.order import Order, OrderType, OrderStatus, OrderAssignee
from app.models.contractor_assignment import ContractorAssignment, AssignmentStatus
from app.models.contractor_deliverable import ContractorDeliverable, DeliverableStatus
from app.models.staff_assignment import StaffAssignment, StaffAssignmentStatus
from app.models.staff_deliverable import StaffDeliverable
from app.models.user import EnterpriseStatus, User, UserRole
from app.utils.dependencies import AnyUser
from app.models.admin import Admin
from app.models.staff_member import StaffMember
from app.models.file import File, FileType
from app.models.feedback import Feedback, FeedbackType
from app.models.notification import NotificationType
from app.schemas.order import *
from app.schemas.file import FileUpload, FileResponse
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.utils.validators import generate_order_number, generate_id
from app.services.file_service import FileService
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from app.services.pdf_service import PDFService
from app.services.staff_creator_service import sync_staff_assignments_for_order
from app.config import settings
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_iso, beijing_now, beijing_now_iso


logger = get_module_logger("order")


def _log_email_result(event: str, sent: bool, **fields):
    log_business_event(
        logger,
        event if sent else f"{event}_failed",
        level="info" if sent else "warning",
        **fields,
    )


async def _get_order_assignee_ids(db: AsyncSession, order_id: str) -> List[str]:
    """获取订单的所有负责人 ID（从 order_assignees 表查询）"""
    result = await db.execute(
        select(OrderAssignee.assignee_id).where(OrderAssignee.order_id == order_id)
    )
    return [row[0] for row in result.all()]


def _iso_beijing(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return beijing_iso(dt)


def _feedback_deliverable_id(feedback: Feedback) -> str | None:
    """返回反馈实际关联的交付物 ID，兼容承包商和内部负责人历史数据。"""
    return feedback.deliverable_id or feedback.staff_deliverable_id


def _can_view_customer_feedback(current_user: AnyUser) -> bool:
    """客户原始反馈只对客户本人和管理员开放。"""
    return current_user.role in (UserRole.USER, UserRole.ADMIN)


def _derive_creator_review_statuses(rows: list[tuple]) -> dict[str, str]:
    """按订单当前制作环节的最新交付版本，计算管理员审核队列状态。"""
    latest_by_stage = {}

    for order_id, current_stage_order, deliverable in rows:
        try:
            current_order = int(current_stage_order or "1")
        except (TypeError, ValueError):
            continue

        if deliverable.stage_order != current_order:
            continue

        key = (order_id, deliverable.assignment_id, deliverable.stage_order)
        latest = latest_by_stage.get(key)
        if latest is None or (deliverable.version or 0) > (latest.version or 0):
            latest_by_stage[key] = deliverable

    statuses_by_order: dict[str, list] = {}
    for (order_id, _assignment_id, _stage_order), deliverable in latest_by_stage.items():
        statuses_by_order.setdefault(order_id, []).append(deliverable)

    result: dict[str, str] = {}
    for order_id, deliverables in statuses_by_order.items():
        if any(d.status == DeliverableStatus.SUBMITTED for d in deliverables):
            result[order_id] = "pending_review"
            continue

        if any(
            d.status == DeliverableStatus.ADMIN_REJECTED
            or (d.status == DeliverableStatus.DRAFT and bool(d.parent_id))
            for d in deliverables
        ):
            result[order_id] = "review_rejected"

    return result


async def _get_creator_review_statuses(
    db: AsyncSession,
    order_ids: list[str],
) -> dict[str, str]:
    """批量读取承包商/内部负责人当前交付物状态，避免订单列表逐单查询。"""
    if not order_ids:
        return {}

    contractor_result = await db.execute(
        select(
            ContractorAssignment.order_id,
            ContractorAssignment.current_stage_order,
            ContractorDeliverable,
        )
        .join(
            ContractorDeliverable,
            ContractorDeliverable.assignment_id == ContractorAssignment.id,
        )
        .where(
            ContractorAssignment.order_id.in_(order_ids),
            ContractorAssignment.status.in_([
                AssignmentStatus.ACCEPTED,
                AssignmentStatus.IN_PROGRESS,
            ]),
        )
    )
    staff_result = await db.execute(
        select(
            StaffAssignment.order_id,
            StaffAssignment.current_stage_order,
            StaffDeliverable,
        )
        .join(
            StaffDeliverable,
            StaffDeliverable.assignment_id == StaffAssignment.id,
        )
        .where(
            StaffAssignment.order_id.in_(order_ids),
            StaffAssignment.status == StaffAssignmentStatus.IN_PROGRESS,
        )
    )

    return _derive_creator_review_statuses(
        [*contractor_result.all(), *staff_result.all()]
    )


async def _resolve_published_feedback_deliverable(
    db: AsyncSession,
    order_id: str,
    deliverable_id: str,
) -> str | None:
    """确认客户反馈目标属于当前订单且已发布，返回制作者类型。"""
    contractor_result = await db.execute(
        select(ContractorDeliverable.id)
        .join(ContractorAssignment, ContractorDeliverable.assignment_id == ContractorAssignment.id)
        .where(
            ContractorDeliverable.id == deliverable_id,
            ContractorAssignment.order_id == order_id,
            ContractorDeliverable.is_published_to_user == True,  # noqa: E712
        )
    )
    if contractor_result.scalar_one_or_none():
        return "contractor"

    staff_result = await db.execute(
        select(StaffDeliverable.id)
        .join(StaffAssignment, StaffDeliverable.assignment_id == StaffAssignment.id)
        .where(
            StaffDeliverable.id == deliverable_id,
            StaffAssignment.order_id == order_id,
            StaffDeliverable.is_published_to_user == True,  # noqa: E712
        )
    )
    if staff_result.scalar_one_or_none():
        return "staff"

    return None


class OrderStateMachine:
    """六阶段订单状态机；审核、驳回和修改是交付物子状态。"""

    ORDERED_STATUSES = (
        OrderStatus.DRAFT,
        OrderStatus.PENDING_CONTRACT,
        OrderStatus.IN_PRODUCTION,
        OrderStatus.PREVIEW_READY,
        OrderStatus.FINAL_PREVIEW,
        OrderStatus.COMPLETED,
    )
    NEXT_STATUS = {
        OrderStatus.DRAFT: OrderStatus.PENDING_CONTRACT,
        OrderStatus.PENDING_CONTRACT: OrderStatus.IN_PRODUCTION,
        OrderStatus.IN_PRODUCTION: OrderStatus.PREVIEW_READY,
        OrderStatus.PREVIEW_READY: OrderStatus.FINAL_PREVIEW,
        OrderStatus.FINAL_PREVIEW: OrderStatus.COMPLETED,
    }

    @classmethod
    def canonical_status(
        cls,
        order_status: OrderStatus,
        *,
        has_final_preview: bool = False,
    ) -> OrderStatus:
        """将历史状态映射到六阶段，不修改数据库中的历史记录。"""
        if order_status == OrderStatus.PENDING_ASSIGN:
            return OrderStatus.DRAFT
        if order_status in (
            OrderStatus.PENDING_REVIEW,
            OrderStatus.REVIEW_REJECTED,
            OrderStatus.REVISION_NEEDED,
        ):
            return OrderStatus.FINAL_PREVIEW if has_final_preview else OrderStatus.PREVIEW_READY
        return order_status

    @classmethod
    def next_status(
        cls,
        order_status: OrderStatus,
        *,
        has_final_preview: bool = False,
    ) -> OrderStatus | None:
        """返回唯一可推进的下一状态；历史状态先原位归一化。"""
        if order_status == OrderStatus.PENDING_ASSIGN:
            return OrderStatus.PENDING_CONTRACT
        if order_status in (
            OrderStatus.PENDING_REVIEW,
            OrderStatus.REVIEW_REJECTED,
            OrderStatus.REVISION_NEEDED,
        ):
            return cls.canonical_status(
                order_status,
                has_final_preview=has_final_preview,
            )
        return cls.NEXT_STATUS.get(order_status)
    
    @classmethod
    def can_transition(
        cls,
        from_status: OrderStatus,
        to_status: OrderStatus,
        *,
        has_final_preview: bool = False,
    ) -> bool:
        """检查是否可以进行状态转换"""
        if from_status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            return False
        if to_status == OrderStatus.CANCELLED:
            return True
        return to_status == cls.next_status(
            from_status,
            has_final_preview=has_final_preview,
        )
    
    @classmethod
    def validate_transition(
        cls,
        from_status: OrderStatus,
        to_status: OrderStatus,
        *,
        has_final_preview: bool = False,
    ):
        """验证状态转换"""
        # 如果状态相同，允许（用于重复操作）
        if from_status == to_status:
            return
        
        if not cls.can_transition(
            from_status,
            to_status,
            has_final_preview=has_final_preview,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"非法的状态转换: {from_status.value} -> {to_status.value}"
            )


class OrderService:
    """订单服务类"""

    @staticmethod
    def _ensure_order_detail_role_allowed(current_user: AnyUser) -> None:
        if current_user.role == UserRole.CONTRACTOR:
            raise HTTPException(status_code=403, detail="承包商请通过制作任务查看订单信息")

    @staticmethod
    def _ensure_assignment_design_plan_completed(order: Order) -> None:
        design_plan = order.design_plan if isinstance(order.design_plan, dict) else {}
        if design_plan.get("status") != "completed":
            raise HTTPException(status_code=400, detail="请先完成AI方案设计")

    @staticmethod
    def _confirmation_pdf_filename(order: Order) -> str:
        return f"订单需求确认函_{order.order_number}.pdf"

    @staticmethod
    def _confirmation_pdf_object_key(order: Order) -> str:
        return f"confirmation_pdfs/{order.user_id}/{order.id}_{order.order_number}.pdf"

    @staticmethod
    def _confirmation_pdf_local_path(order: Order) -> str:
        return os.path.join(
            settings.UPLOAD_DIR,
            "confirmation_pdfs",
            order.user_id,
            f"{order.id}_{order.order_number}.pdf",
        )

    @staticmethod
    def _get_archived_confirmation_meta(order: Order) -> dict:
        order_data = order.order_data if isinstance(order.order_data, dict) else {}
        return order_data.get("confirmationPdf") or {}

    @staticmethod
    async def _ensure_confirmation_pdf_archive(
        db: AsyncSession,
        order: Order,
        user: User,
        order_response: Optional[dict] = None,
    ) -> tuple[bytes, str]:
        """确保订单需求确认函只生成并归档一次，后续邮件/下载复用同一文件。"""
        meta = OrderService._get_archived_confirmation_meta(order)
        filename = meta.get("filename") or OrderService._confirmation_pdf_filename(order)

        if settings.OSS_ENABLED and meta.get("objectKey"):
            from app.services.oss_service import download_object_bytes
            try:
                return download_object_bytes(meta["objectKey"]), filename
            except Exception as e:
                log_business_event(
                    logger,
                    "order_confirmation_pdf_archive_read_failed",
                    level="warning",
                    order_id=order.id,
                    order_number=order.order_number,
                    object_key=meta.get("objectKey", ""),
                    error=str(e),
                )

        if not settings.OSS_ENABLED and meta.get("filePath") and os.path.exists(meta["filePath"]):
            with open(meta["filePath"], "rb") as f:
                return f.read(), filename

        if order_response is None:
            order_response = await OrderService._build_order_response(db, order, user)

        pdf_bytes = PDFService.generate_order_confirmation_pdf(order_response)
        archived_at = beijing_now_iso()

        if settings.OSS_ENABLED:
            from app.services.oss_service import upload_bytes
            object_key = OrderService._confirmation_pdf_object_key(order)
            upload_bytes(pdf_bytes, object_key, "application/pdf")
            confirmation_meta = {
                "storage": "oss",
                "objectKey": object_key,
                "filename": filename,
                "contentType": "application/pdf",
                "size": len(pdf_bytes),
                "archivedAt": archived_at,
            }
        else:
            file_path = OrderService._confirmation_pdf_local_path(order)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            confirmation_meta = {
                "storage": "local",
                "filePath": file_path,
                "filename": filename,
                "contentType": "application/pdf",
                "size": len(pdf_bytes),
                "archivedAt": archived_at,
            }

        next_order_data = dict(order.order_data or {})
        next_order_data["confirmationPdf"] = confirmation_meta
        order.order_data = next_order_data
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "order_confirmation_pdf_archived",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            storage=confirmation_meta["storage"],
            object_key=confirmation_meta.get("objectKey", ""),
        )
        return pdf_bytes, filename

    @staticmethod
    def _enterprise_status_value(user: AnyUser) -> str:
        status_value = getattr(user, "enterprise_status", EnterpriseStatus.NONE)
        if hasattr(status_value, "value"):
            return status_value.value
        return str(status_value or "none").lower()

    @staticmethod
    def _require_enterprise_approved(user: AnyUser):
        """普通客户正式提交订单前必须完成企业认证。"""
        if isinstance(user, User) and OrderService._enterprise_status_value(user) != EnterpriseStatus.APPROVED.value:
            raise HTTPException(
                status_code=403,
                detail="请先完成企业认证后再提交订单。您可以先将订单保存为订单草稿。"
            )
    
    @staticmethod
    async def create_order(
        db: AsyncSession,
        order_data: Union[VideoPurchaseOrderCreate, AI3DCustomOrderCreate, DigitalArtOrderCreate],
        user: User,
        is_draft: bool = False
    ) -> dict:
        """创建订单（支持草稿模式）"""
        if not is_draft:
            OrderService._require_enterprise_approved(user)

        # 生成订单 ID 和订单号
        order_id = generate_id("order")
        order_number = generate_order_number()
        
        # 根据订单类型处理数据
        order_type_map = {
            "video_purchase": OrderType.VIDEO_PURCHASE,
            "ai_3d_custom": OrderType.AI_3D_CUSTOM,
            "digital_art": OrderType.DIGITAL_ART
        }
        
        order_type = order_type_map.get(order_data.orderType)
        if not order_type:
            raise HTTPException(status_code=400, detail="无效的订单类型")
        
        # 准备订单数据
        order_dict = order_data.model_dump()
        order_type_str = order_dict.pop("orderType")
        
        # 处理文件（如果有）
        files_to_create = []
        
        if order_type == OrderType.AI_3D_CUSTOM:
            scene_photos = order_dict.pop("scenePhotos", [])
            order_dict["scenePhotos"] = []
            for photo in scene_photos:
                file_response = FileService.convert_file_upload_to_response(photo, order_id)
                order_dict["scenePhotos"].append(file_response.model_dump())
                # 创建文件记录
                files_to_create.append({
                    "id": file_response.id,
                    "name": file_response.name,
                    "size": file_response.size,
                    "mime_type": file_response.type,
                    "url": file_response.url,
                    "file_type": FileType.SCENE_PHOTO
                })
        
        elif order_type == OrderType.DIGITAL_ART:
            materials = order_dict.pop("materials", [])
            order_dict["materials"] = []
            for material in materials:
                file_response = FileService.convert_file_upload_to_response(material, order_id)
                order_dict["materials"].append(file_response.model_dump())
                files_to_create.append({
                    "id": file_response.id,
                    "name": file_response.name,
                    "size": file_response.size,
                    "mime_type": file_response.type,
                    "url": file_response.url,
                    "file_type": FileType.MATERIAL
                })
        
        # 创建订单
        new_order = Order(
            id=order_id,
            order_number=order_number,
            order_type=order_type,
            status=OrderStatus.DRAFT if is_draft else OrderStatus.PENDING_CONTRACT,
            user_id=user.id,
            revision_count=0,
            order_data=order_dict
        )
        
        db.add(new_order)
        
        # 创建文件记录
        for file_data in files_to_create:
            file_record = File(
                order_id=order_id,
                **file_data
            )
            db.add(file_record)
        
        await db.commit()
        await db.refresh(new_order)
        log_business_event(
            logger,
            "order_created",
            order_id=new_order.id,
            order_number=new_order.order_number,
            user_id=user.id,
            username=user.username,
            order_type=new_order.order_type,
            status=new_order.status,
            is_draft=is_draft,
            file_count=len(files_to_create),
        )
        
        # 构造响应
        order_response = await OrderService._build_order_response(db, new_order, user)

        # 如果不是草稿（直接提交），生成 PDF 并发邮件
        if not is_draft:
            if user.email:
                pdf_bytes, _ = await OrderService._ensure_confirmation_pdf_archive(
                    db,
                    new_order,
                    user,
                    order_response,
                )
                email_sent = await EmailService.send_order_confirmation(
                    user.email,
                    new_order.order_number,
                    pdf_bytes
                )
                _log_email_result(
                    "order_confirmation_email_sent",
                    email_sent,
                    order_id=new_order.id,
                    order_number=new_order.order_number,
                    user_id=user.id,
                    email=user.email,
                )
            
            # 通知所有管理员有新订单提交
            try:
                from app.models.admin import Admin
                admin_result = await db.execute(select(Admin))
                admins = admin_result.scalars().all()
                admin_ids = [admin.id for admin in admins]
                if admin_ids:
                    await NotificationService.create_notification_for_multiple_users(
                        db=db,
                        user_ids=admin_ids,
                        notification_type=NotificationType.SYSTEM_NOTICE,
                        title="新订单提交",
                        content=f"用户 {user.username} 提交了新订单：{new_order.order_number}，请及时处理。",
                        order_id=new_order.id
                    )
            except Exception as e:
                log_business_event(
                    logger,
                    "order_admin_notification_failed",
                    level="warning",
                    order_id=new_order.id,
                    order_number=new_order.order_number,
                    user_id=user.id,
                    error=str(e),
                )

        return order_response
    
    @staticmethod
    async def update_order(
        db: AsyncSession,
        order_id: str,
        order_data: Union[VideoPurchaseOrderCreate, AI3DCustomOrderCreate, DigitalArtOrderCreate],
        current_user: AnyUser
    ) -> dict:
        """修改订单（仅待分配状态可修改）"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 权限检查：只有订单创建者可以修改
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权修改此订单")
        
        # 状态检查：只有草稿状态的订单可以修改（签名后不可修改）
        if order.status != OrderStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail=f"只有订单草稿状态的订单可以修改，当前状态：{order.status.value}"
            )
        
        # 验证订单类型不能改变
        order_type_map = {
            "video_purchase": OrderType.VIDEO_PURCHASE,
            "ai_3d_custom": OrderType.AI_3D_CUSTOM,
            "digital_art": OrderType.DIGITAL_ART
        }
        
        new_order_type = order_type_map.get(order_data.orderType)
        if not new_order_type:
            raise HTTPException(status_code=400, detail="无效的订单类型")
        
        if order.order_type != new_order_type:
            raise HTTPException(status_code=400, detail="不能修改订单类型")
        
        # 准备新的订单数据
        order_dict = order_data.model_dump()
        order_dict.pop("orderType")  # 移除 orderType，因为已经在 order_type 字段中
        
        # 处理文件（如果有）
        files_to_create = []
        files_to_delete = []  # 需要删除的旧文件
        
        if new_order_type == OrderType.AI_3D_CUSTOM:
            # 获取旧的文件记录
            old_files_result = await db.execute(
                select(File).where(File.order_id == order_id, File.file_type == FileType.SCENE_PHOTO)
            )
            old_files = old_files_result.scalars().all()
            files_to_delete = [f.id for f in old_files]
            
            scene_photos = order_dict.pop("scenePhotos", [])
            order_dict["scenePhotos"] = []
            for photo in scene_photos:
                file_response = FileService.convert_file_upload_to_response(photo, order_id)
                order_dict["scenePhotos"].append(file_response.model_dump())
                files_to_create.append({
                    "id": file_response.id,
                    "name": file_response.name,
                    "size": file_response.size,
                    "mime_type": file_response.type,
                    "url": file_response.url,
                    "file_type": FileType.SCENE_PHOTO
                })
        
        elif new_order_type == OrderType.DIGITAL_ART:
            # 获取旧的文件记录
            old_files_result = await db.execute(
                select(File).where(File.order_id == order_id, File.file_type == FileType.MATERIAL)
            )
            old_files = old_files_result.scalars().all()
            files_to_delete = [f.id for f in old_files]
            
            materials = order_dict.pop("materials", [])
            order_dict["materials"] = []
            for material in materials:
                file_response = FileService.convert_file_upload_to_response(material, order_id)
                order_dict["materials"].append(file_response.model_dump())
                files_to_create.append({
                    "id": file_response.id,
                    "name": file_response.name,
                    "size": file_response.size,
                    "mime_type": file_response.type,
                    "url": file_response.url,
                    "file_type": FileType.MATERIAL
                })
        
        # 更新订单数据
        order.order_data = order_dict
        
        # 删除旧文件记录
        if files_to_delete:
            from sqlalchemy import delete
            delete_stmt = delete(File).where(File.id.in_(files_to_delete))
            await db.execute(delete_stmt)
        
        # 创建新文件记录
        for file_data in files_to_create:
            file_record = File(
                order_id=order_id,
                **file_data
            )
            db.add(file_record)
        
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "order_updated",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            order_type=order.order_type,
            status=order.status,
            file_count=len(files_to_create),
            deleted_file_count=len(files_to_delete),
        )
        
        # 构造响应
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def get_orders(
        db: AsyncSession,
        current_user: AnyUser,
        user_id: Optional[str] = None,
        order_type: Optional[OrderType] = None,
        status: Optional[OrderStatus] = None,
        assignee_id: Optional[str] = None
    ) -> List[dict]:
        """获取订单列表"""
        # 判断是否需要JOIN
        needs_join = False
        if current_user.role == UserRole.STAFF:
            needs_join = True
        elif assignee_id:
            needs_join = True
        
        if needs_join:
            query = select(Order).distinct().join(
                OrderAssignee, Order.id == OrderAssignee.order_id
            )
        else:
            query = select(Order)
        
        # 权限过滤
        if current_user.role == UserRole.USER:
            # 普通用户只能查看自己的订单
            query = query.where(Order.user_id == current_user.id)
        elif current_user.role == UserRole.STAFF:
            # 负责人可以查看分配给自己的订单
            query = query.where(OrderAssignee.assignee_id == current_user.id)
        # 管理员可以查看所有订单
        
        # 其他筛选条件
        if user_id and current_user.role == UserRole.ADMIN:
            query = query.where(Order.user_id == user_id)
        if order_type:
            query = query.where(Order.order_type == order_type)
        if status:
            query = query.where(Order.status == status)
        if assignee_id:
            # 筛选包含指定负责人的订单
            if not needs_join:
                query = query.join(
                    OrderAssignee, Order.id == OrderAssignee.order_id
                )
            query = query.where(OrderAssignee.assignee_id == assignee_id)
        
        # 执行查询
        result = await db.execute(query.order_by(Order.created_at.desc()))
        orders = result.scalars().all()

        creator_review_statuses = {}
        if current_user.role == UserRole.ADMIN:
            creator_review_statuses = await _get_creator_review_statuses(
                db,
                [order.id for order in orders],
            )
        
        # 构造响应
        order_responses = []
        for order in orders:
            order_response = await OrderService._build_order_response(db, order, current_user)
            if current_user.role == UserRole.ADMIN:
                order_response["creatorReviewStatus"] = creator_review_statuses.get(order.id)
            order_responses.append(order_response)
        
        return order_responses
    
    @staticmethod
    async def get_order_detail(
        db: AsyncSession,
        order_id: str,
        current_user: AnyUser
    ) -> dict:
        """获取订单详情"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        OrderService._ensure_order_detail_role_allowed(current_user)
        
        # 权限检查
        if current_user.role == UserRole.USER and order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权查看此订单")
        elif current_user.role == UserRole.STAFF:
            # 检查当前用户是否是订单的任一负责人
            assignee_result = await db.execute(
                select(OrderAssignee).where(
                    OrderAssignee.order_id == order_id,
                    OrderAssignee.assignee_id == current_user.id
                )
            )
            assignee = assignee_result.scalar_one_or_none()
            if not assignee:
                raise HTTPException(status_code=403, detail="无权查看此订单")
        
        return await OrderService._build_order_response(db, order, current_user)

    @staticmethod
    async def get_confirmation_pdf_archive(
        db: AsyncSession,
        order_id: str,
        current_user: AnyUser,
    ) -> tuple[bytes, str]:
        """获取订单需求确认函归档文件；旧订单没有归档时补生成一次。"""
        order_response = await OrderService.get_order_detail(db, order_id, current_user)

        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="订单用户不存在")

        return await OrderService._ensure_confirmation_pdf_archive(
            db,
            order,
            user,
            order_response,
        )
    
    @staticmethod
    async def update_order_status(
        db: AsyncSession,
        order_id: str,
        new_status: OrderStatus,
        current_user: AnyUser
    ) -> dict:
        """更新订单状态"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 权限检查
        # 允许订单创建者将自己的草稿提交（draft -> pending_contract）
        is_draft_submit = (
            order.status == OrderStatus.DRAFT 
            and new_status in [OrderStatus.PENDING_CONTRACT, OrderStatus.PENDING_ASSIGN]
            and order.user_id == current_user.id
        )
        # 兼容：如果前端还传 pending_assign，自动映射到 pending_contract
        if is_draft_submit and new_status == OrderStatus.PENDING_ASSIGN:
            new_status = OrderStatus.PENDING_CONTRACT

        if is_draft_submit:
            OrderService._require_enterprise_approved(current_user)
        
        # 允许订单创建者删除自己的草稿（draft -> cancelled）
        is_draft_delete = (
            order.status == OrderStatus.DRAFT 
            and new_status == OrderStatus.CANCELLED 
            and order.user_id == current_user.id
        )
        
        # 签订确认函后（非草稿状态），用户不能取消订单，只有管理员可以
        if new_status == OrderStatus.CANCELLED and order.status != OrderStatus.DRAFT:
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="签订确认函后，只有管理员可以取消订单")
        
        if not is_draft_submit and not is_draft_delete and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="权限不足")
        
        # 验证状态转换
        has_final_preview = any(
            item.get("previewType") == "final"
            for item in (order.order_data or {}).get("previewHistory", [])
            if isinstance(item, dict)
        )
        OrderStateMachine.validate_transition(
            order.status,
            new_status,
            has_final_preview=has_final_preview,
        )
        
        old_status = order.status
        order.status = new_status
        
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "order_status_updated",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            status_from=old_status,
            status_to=order.status,
            is_draft_submit=is_draft_submit,
            is_draft_delete=is_draft_delete,
        )
        
        # 发送邮件通知（获取用户邮箱）
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if user and user.email:
            if is_draft_submit:
                # 生成并归档订单需求确认函 PDF，邮件和后续下载复用同一份文件
                order_response_for_pdf = await OrderService._build_order_response(db, order, user)
                pdf_bytes, _ = await OrderService._ensure_confirmation_pdf_archive(
                    db,
                    order,
                    user,
                    order_response_for_pdf,
                )
                email_sent = await EmailService.send_order_confirmation(
                    user.email,
                    order.order_number,
                    pdf_bytes
                )
                _log_email_result(
                    "order_confirmation_email_sent",
                    email_sent,
                    order_id=order.id,
                    order_number=order.order_number,
                    user_id=order.user_id,
                    email=user.email,
                )
            else:
                # 发送普通的状态变更邮件
                email_sent = await EmailService.send_order_status_notification(
                    user.email,
                    order.order_number,
                    old_status.value,
                    new_status.value
                )
                _log_email_result(
                    "order_status_email_sent",
                    email_sent,
                    order_id=order.id,
                    order_number=order.order_number,
                    user_id=order.user_id,
                    status_from=old_status,
                    status_to=new_status,
                    email=user.email,
                )
        
        # 创建系统内消息通知
        # 1. 通知订单用户状态变更
        status_map = {
            "draft": "需求确认",
            "pending_assign": "需求确认",
            "pending_contract": "合同与付款",
            "in_production": "内容制作",
            "pending_review": "初稿交付",
            "preview_ready": "初稿交付",
            "review_rejected": "初稿交付",
            "revision_needed": "初稿交付",
            "final_preview": "终稿交付",
            "completed": "项目完成",
            "cancelled": "已取消"
        }
        new_status_text = status_map.get(new_status.value, new_status.value)
        
        await NotificationService.create_notification(
            db=db,
            user_id=order.user_id,
            notification_type=NotificationType.ORDER_STATUS_CHANGED,
            title=f"订单状态更新",
            content=f"您的订单 {order.order_number} 状态已变更为：{new_status_text}",
            order_id=order.id
        )
        
        # 2. 通知所有负责该订单的staff
        assignee_ids = await _get_order_assignee_ids(db, order.id)
        if assignee_ids:
            await NotificationService.create_notification_for_multiple_users(
                db=db,
                user_ids=assignee_ids,
                notification_type=NotificationType.ORDER_STATUS_CHANGED,
                title=f"订单状态更新",
                content=f"订单 {order.order_number} 状态已变更为：{new_status_text}",
                order_id=order.id
            )
            
        # 3. 如果是用户提交草稿或者是没有负责人的订单，通知管理员
        if is_draft_submit or not assignee_ids:
            try:
                from app.models.admin import Admin
                admin_result = await db.execute(select(Admin))
                admins = admin_result.scalars().all()
                admin_ids = [admin.id for admin in admins]
                if admin_ids:
                    title = "新订单提交" if is_draft_submit else "订单状态更新"
                    content = f"用户提交了订单草稿：{order.order_number}，请及时分配。" if is_draft_submit else f"订单 {order.order_number} 状态变更为 {new_status_text}。"
                    await NotificationService.create_notification_for_multiple_users(
                        db=db,
                        user_ids=admin_ids,
                        notification_type=NotificationType.SYSTEM_NOTICE,
                        title=title,
                        content=content,
                        order_id=order.id
                    )
            except Exception as e:
                log_business_event(
                    logger,
                    "order_admin_notification_failed",
                    level="warning",
                    order_id=order.id,
                    order_number=order.order_number,
                    user_id=order.user_id,
                    status_from=old_status,
                    status_to=new_status,
                    error=str(e),
                )
        
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def assign_order(
        db: AsyncSession,
        order_id: str,
        assignee_ids: List[str],
        assignee_names: List[str],
        current_user: AnyUser
    ) -> dict:
        """分配订单负责人"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="只有管理员可以分配订单")
        
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        assignable_statuses = {
            OrderStatus.IN_PRODUCTION,
            OrderStatus.PENDING_REVIEW,
            OrderStatus.PREVIEW_READY,
            OrderStatus.REVIEW_REJECTED,
            OrderStatus.REVISION_NEEDED,
            OrderStatus.FINAL_PREVIEW,
        }
        if assignee_ids and order.status not in assignable_statuses:
            raise HTTPException(
                status_code=400,
                detail="订单进入「内容制作」后才可以分配内部负责人",
            )

        OrderService._ensure_assignment_design_plan_completed(order)
        
        if len(assignee_ids) != len(assignee_names):
            raise HTTPException(status_code=400, detail="负责人ID和名称数量不匹配")
        
        # 验证所有负责人（从 staff_members 表）
        assignees_result = await db.execute(
            select(StaffMember).where(StaffMember.id.in_(assignee_ids))
        )
        assignees = assignees_result.scalars().all()
        assignee_dict = {a.id: a for a in assignees}
        
        if len(assignees) != len(assignee_ids):
            raise HTTPException(status_code=400, detail="部分负责人不存在")
        
        for assignee_id in assignee_ids:
            assignee = assignee_dict.get(assignee_id)
            if not assignee:
                raise HTTPException(status_code=400, detail=f"无效的负责人: {assignee_id}")

        if assignee_ids:
            active_contractor_result = await db.execute(
                select(ContractorAssignment.id)
                .where(
                    ContractorAssignment.order_id == order_id,
                    ContractorAssignment.status.in_([
                        AssignmentStatus.PENDING,
                        AssignmentStatus.ACCEPTED,
                        AssignmentStatus.IN_PROGRESS,
                    ]),
                )
                .limit(1)
            )
            if active_contractor_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="该订单已派给承包商，不能再分配内部负责人")
        
        # 获取旧的负责人ID列表（用于判断是新分配还是重新分配）
        old_assignees_result = await db.execute(
            select(OrderAssignee).where(OrderAssignee.order_id == order_id)
        )
        old_assignees = old_assignees_result.scalars().all()
        old_assignee_ids = {assignee.assignee_id for assignee in old_assignees}
        new_assignee_ids = set(assignee_ids)
        
        # 删除旧的关联记录
        from sqlalchemy import delete
        delete_stmt = delete(OrderAssignee).where(OrderAssignee.order_id == order_id)
        await db.execute(delete_stmt)
        
        # 创建新的关联记录
        for assignee_id in assignee_ids:
            order_assignee = OrderAssignee(
                order_id=order_id,
                assignee_id=assignee_id
            )
            db.add(order_assignee)

        await sync_staff_assignments_for_order(
            db=db,
            order_id=order_id,
            old_staff_ids=old_assignee_ids,
            new_staff_ids=new_assignee_ids,
            assigned_by=current_user.id,
        )
        
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "order_assigned",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            status_from=order.status,
            status_to=order.status,
            old_assignee_ids=sorted(old_assignee_ids),
            new_assignee_ids=sorted(new_assignee_ids),
        )
        
        # 创建系统内消息通知
        # 判断是新分配还是重新分配
        if old_assignee_ids:
            # 重新分配：通知新的负责人
            newly_assigned = new_assignee_ids - old_assignee_ids
            if newly_assigned:
                await NotificationService.create_notification_for_multiple_users(
                    db=db,
                    user_ids=list(newly_assigned),
                    notification_type=NotificationType.ORDER_ASSIGNED,
                    title=f"新订单分配",
                    content=f"您已被分配负责订单：{order.order_number}",
                    order_id=order.id
                )
            
            # 通知被移除的旧负责人
            removed_assignees = old_assignee_ids - new_assignee_ids
            if removed_assignees:
                await NotificationService.create_notification_for_multiple_users(
                    db=db,
                    user_ids=list(removed_assignees),
                    notification_type=NotificationType.ORDER_REASSIGNED,
                    title=f"订单负责人变更",
                    content=f"您已不再负责订单：{order.order_number}",
                    order_id=order.id
                )
        else:
            # 首次分配：通知所有新负责人
            await NotificationService.create_notification_for_multiple_users(
                db=db,
                user_ids=assignee_ids,
                notification_type=NotificationType.ORDER_ASSIGNED,
                title=f"新订单分配",
                content=f"您已被分配负责订单：{order.order_number}",
                order_id=order.id
            )
        
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def upload_preview(
        db: AsyncSession,
        order_id: str,
        files: List[FileUpload],
        note: Optional[str],
        preview_type: str,
        current_user: AnyUser
    ) -> dict:
        """上传预览文件"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 权限检查
        if current_user.role not in [UserRole.ADMIN, UserRole.STAFF]:
            raise HTTPException(status_code=403, detail="权限不足")

        if current_user.role == UserRole.STAFF:
            assignee_result = await db.execute(
                select(OrderAssignee).where(
                    OrderAssignee.order_id == order_id,
                    OrderAssignee.assignee_id == current_user.id
                )
            )
            if not assignee_result.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="无权为未分配给自己的订单上传预览")
        
        # 处理预览文件
        preview_files = []
        for file_upload in files:
            file_response = FileService.convert_file_upload_to_response(file_upload, order_id)
            preview_files.append(file_response.model_dump())
            
            # 创建文件记录
            file_record = File(
                id=file_response.id,
                order_id=order_id,
                file_type=FileType.PREVIEW,
                name=file_response.name,
                size=file_response.size,
                mime_type=file_response.type,
                url=file_response.url
            )
            db.add(file_record)
        
        # 更新订单数据中的预览文件和备注
        order_data = order.order_data.copy()
        preview_files_field = order_data.get("previewFiles", [])
        # 仅保留审核通过的预览文件，未审核文件通过预览历史关联
        order_data["previewFiles"] = preview_files_field
        
        # 存储预览历史记录（每次上传都保存一条完整记录）
        now = beijing_now()
        preview_type_value = preview_type if preview_type in ["initial", "final"] else "initial"
        preview_history_entry = {
            "id": generate_id("preview"),
            "files": preview_files,
            "note": note or "",
            "createdAt": now.isoformat(),
            "createdBy": current_user.id,
            "createdByName": current_user.real_name or current_user.username,
            "previewType": preview_type_value,
            "reviewStatus": "pending",
            "reviewNote": "",
            "reviewedAt": None,
            "reviewedBy": None,
            "reviewedByName": None
        }
        
        if "previewHistory" not in order_data:
            order_data["previewHistory"] = []
        order_data["previewHistory"].append(preview_history_entry)
        
        pending_review_ids = set(order_data.get("pendingReviewPreviewIds", []))
        pending_review_ids.add(preview_history_entry["id"])
        order_data["pendingReviewPreviewIds"] = list(pending_review_ids)
        
        # 存储备注（如果提供了备注）
        if note:
            # 如果已有备注数组，追加；否则创建新数组
            if "previewNotes" not in order_data:
                order_data["previewNotes"] = []
            order_data["previewNotes"].append({
                "note": note,
                "createdAt": now.isoformat(),
                "createdBy": current_user.id,
                "createdByName": current_user.real_name or current_user.username
            })
            # 同时保存最新备注，方便快速访问
            order_data["previewNote"] = note
        
        old_status = order.status
        has_final_preview = any(
            item.get("previewType") == "final"
            for item in order_data.get("previewHistory", [])
            if isinstance(item, dict)
        )
        current_stage = OrderStateMachine.canonical_status(
            order.status,
            has_final_preview=has_final_preview,
        )
        allowed_upload_stages = (
            (OrderStatus.IN_PRODUCTION, OrderStatus.PREVIEW_READY)
            if preview_type_value == "initial"
            else (OrderStatus.PREVIEW_READY, OrderStatus.FINAL_PREVIEW)
        )
        if current_stage not in allowed_upload_stages:
            preview_label = "初稿" if preview_type_value == "initial" else "终稿"
            raise HTTPException(
                status_code=400,
                detail=f"当前订单阶段不能上传{preview_label}",
            )

        order.order_data = order_data
        
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "preview_uploaded",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            preview_id=preview_history_entry["id"],
            preview_type=preview_type_value,
            file_count=len(preview_files),
            status_from=old_status,
            status_to=order.status,
        )
        
        # 通知管理员有新的预览待审核（从 admins 表查询）
        admin_result = await db.execute(select(Admin))
        admins = admin_result.scalars().all()
        admin_ids = [admin.id for admin in admins]
        preview_type_text = "终稿" if preview_type_value == "final" else "初稿"
        if admin_ids:
            await NotificationService.create_notification_for_multiple_users(
                db=db,
                user_ids=admin_ids,
                notification_type=NotificationType.PREVIEW_REVIEW_REQUIRED,
                title="预览待审核",
                content=f"订单 {order.order_number} 上传了新的{preview_type_text}预览，等待审核。",
                order_id=order.id
            )
        
        # 通知所有负责该订单的 staff 预览已提交并等待审核
        assignee_ids = await _get_order_assignee_ids(db, order.id)
        if assignee_ids:
            await NotificationService.create_notification_for_multiple_users(
                db=db,
                user_ids=assignee_ids,
                notification_type=NotificationType.PREVIEW_REVIEW_REQUIRED,
                title="预览待审核",
                content=f"订单 {order.order_number} 的{preview_type_text}预览已提交，等待管理员审核。",
                order_id=order.id
            )
        
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def review_preview(
        db: AsyncSession,
        order_id: str,
        review_data: PreviewReview,
        current_user: AnyUser
    ) -> dict:
        """审核预览文件"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="只有管理员可以审核预览")
        
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        order_data = order.order_data.copy()
        preview_history = order_data.get("previewHistory", [])
        
        target_preview = next((p for p in preview_history if p.get("id") == review_data.previewId), None)
        if not target_preview:
            raise HTTPException(status_code=404, detail="预览记录不存在")
        
        if target_preview.get("reviewStatus") != "pending":
            raise HTTPException(status_code=400, detail="该预览已审核")
        
        now = beijing_now_iso()
        reviewer_name = current_user.real_name or current_user.username
        
        target_preview["reviewStatus"] = "approved" if review_data.action == "approve" else "rejected"
        target_preview["reviewNote"] = review_data.note or ""
        target_preview["reviewedAt"] = now
        target_preview["reviewedBy"] = current_user.id
        target_preview["reviewedByName"] = reviewer_name
        
        pending_ids = set(order_data.get("pendingReviewPreviewIds", []))
        pending_ids.discard(target_preview["id"])
        order_data["pendingReviewPreviewIds"] = list(pending_ids)
        
        old_status = order.status
        if review_data.action == "approve":
            # 将文件添加到已审核通过的预览列表
            approved_files = target_preview.get("files", [])
            if approved_files:
                preview_files = order_data.get("previewFiles", [])
                preview_files = preview_files + approved_files
                order_data["previewFiles"] = preview_files
            
            # 审核结果保存在预览记录中；通过时只向前推进到对应交付阶段。
            target_status = OrderStatus.FINAL_PREVIEW if target_preview.get("previewType") == "final" else OrderStatus.PREVIEW_READY
            has_final_preview = any(
                item.get("previewType") == "final"
                for item in preview_history
                if isinstance(item, dict)
            )
            current_stage = OrderStateMachine.canonical_status(
                order.status,
                has_final_preview=has_final_preview,
            )
            if current_stage != target_status:
                OrderStateMachine.validate_transition(
                    order.status,
                    target_status,
                    has_final_preview=has_final_preview,
                )
                order.status = target_status
            elif order.status != target_status:
                order.status = target_status
        
        order.order_data = order_data
        
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "preview_reviewed",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            preview_id=target_preview["id"],
            preview_type=target_preview.get("previewType"),
            action=review_data.action,
            review_status=target_preview.get("reviewStatus"),
            status_from=old_status,
            status_to=order.status,
        )
        
        # 审核通过：通知用户与负责人员
        preview_type_text = "终稿" if target_preview.get("previewType") == "final" else "初稿"
        if review_data.action == "approve":
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            if user and user.email:
                email_sent = await EmailService.send_preview_ready_notification(
                    user.email,
                    order.order_number,
                    preview_type_text
                )
                _log_email_result(
                    "preview_ready_email_sent",
                    email_sent,
                    order_id=order.id,
                    order_number=order.order_number,
                    user_id=order.user_id,
                    preview_id=target_preview["id"],
                    email=user.email,
                )
            
            await NotificationService.create_notification(
                db=db,
                user_id=order.user_id,
                notification_type=NotificationType.PREVIEW_READY,
                title=f"{preview_type_text}预览已通过审核",
                content=f"您的订单 {order.order_number} 的{preview_type_text}预览已通过管理员审核。",
                order_id=order.id
            )
            
            assignee_ids_approved = await _get_order_assignee_ids(db, order.id)
            if assignee_ids_approved:
                await NotificationService.create_notification_for_multiple_users(
                    db=db,
                    user_ids=assignee_ids_approved,
                    notification_type=NotificationType.PREVIEW_REVIEW_APPROVED,
                    title=f"{preview_type_text}预览审核通过",
                    content=f"订单 {order.order_number} 的{preview_type_text}预览通过审核，客户可查看。",
                    order_id=order.id
                )
        else:
            # 审核拒绝：通知负责人员
            rejection_reason = review_data.note or "请重新上传预览文件。"
            assignee_ids_rejected = await _get_order_assignee_ids(db, order.id)
            if assignee_ids_rejected:
                await NotificationService.create_notification_for_multiple_users(
                    db=db,
                    user_ids=assignee_ids_rejected,
                    notification_type=NotificationType.PREVIEW_REVIEW_REJECTED,
                    title=f"{preview_type_text}预览审核被拒绝",
                    content=f"订单 {order.order_number} 的{preview_type_text}预览未通过审核：{rejection_reason}",
                    order_id=order.id
                )
        
        # 如果审核通过并推进了主状态，发送状态变更邮件。
        if review_data.action == "approve" and order.status != old_status:
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            if user and user.email:
                await EmailService.send_order_status_notification(
                    user.email,
                    order.order_number,
                    old_status.value,
                    order.status.value
                )
        
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def submit_feedback(
        db: AsyncSession,
        order_id: str,
        feedback_data: FeedbackCreate,
        current_user: AnyUser
    ) -> dict:
        """提交订单反馈（支持订单级别和交付物级别）"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 权限检查：只有订单创建者可以提交反馈
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="只有订单创建者可以提交反馈")

        # 交付物反馈必须指向当前订单下已经推送给客户的交付物。
        deliverable_creator_type = None
        if feedback_data.deliverableId:
            deliverable_creator_type = await _resolve_published_feedback_deliverable(
                db,
                order_id,
                feedback_data.deliverableId,
            )
            if not deliverable_creator_type:
                raise HTTPException(status_code=404, detail="交付物不存在或尚未对客户发布")

        target_status = None
        if not feedback_data.deliverableId:
            if feedback_data.type == FeedbackType.REVISION:
                if order.status not in [OrderStatus.PREVIEW_READY, OrderStatus.FINAL_PREVIEW]:
                    raise HTTPException(status_code=400, detail="当前订单状态不能提交修改反馈")
            elif feedback_data.type == FeedbackType.APPROVAL:
                if order.status == OrderStatus.PREVIEW_READY:
                    target_status = OrderStatus.FINAL_PREVIEW
                elif order.status == OrderStatus.FINAL_PREVIEW:
                    target_status = OrderStatus.COMPLETED
                else:
                    raise HTTPException(status_code=400, detail="当前订单状态不能确认通过")

            if target_status:
                OrderStateMachine.validate_transition(order.status, target_status)
        
        # 创建反馈记录
        feedback = Feedback(
            id=generate_id("feedback"),
            order_id=order_id,
            deliverable_id=(
                feedback_data.deliverableId
                if deliverable_creator_type == "contractor"
                else None
            ),
            staff_deliverable_id=(
                feedback_data.deliverableId
                if deliverable_creator_type == "staff"
                else None
            ),
            content=feedback_data.content,
            type=feedback_data.type,
            created_by=current_user.id
        )
        db.add(feedback)
        
        # 仅订单级别反馈时才更新订单状态（交付物级别反馈不影响订单状态）
        old_status = order.status
        if not feedback_data.deliverableId and feedback_data.type == FeedbackType.REVISION:
            order.revision_count += 1
        if target_status:
            order.status = target_status
        
        await db.commit()
        await db.refresh(feedback)
        log_business_event(
            logger,
            "feedback_submitted",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            feedback_id=feedback.id,
            feedback_type=feedback.type,
            deliverable_id=_feedback_deliverable_id(feedback),
            status_from=old_status,
            status_to=order.status,
            revision_count=order.revision_count,
        )
        
        # 构建通知描述
        feedback_type_text = "需要修改" if feedback_data.type == FeedbackType.REVISION else "确认通过"
        deliverable_hint = ""
        if feedback_data.deliverableId:
            deliverable_hint = "（针对交付物）"
        
        # 客户原始反馈只通知管理员，由管理员整理后再反馈给制作者。
        try:
            from app.models.admin import Admin
            admin_result = await db.execute(select(Admin))
            admins = admin_result.scalars().all()
            admin_ids = [admin.id for admin in admins]
            if admin_ids:
                await NotificationService.create_notification_for_multiple_users(
                    db=db,
                    user_ids=admin_ids,
                    notification_type=NotificationType.NEW_FEEDBACK,
                    title=f"客户反馈{deliverable_hint}",
                    content=f"订单 {order.order_number} 收到用户的反馈{deliverable_hint}：{feedback_type_text}。内容：{feedback_data.content[:100]}",
                    order_id=order.id
                )
        except Exception as e:
            log_business_event(
                logger,
                "feedback_admin_notification_failed",
                level="warning",
                order_id=order.id,
                order_number=order.order_number,
                user_id=order.user_id,
                feedback_id=feedback.id,
                error=str(e),
            )
        
        return {
            "id": feedback.id,
            "orderId": feedback.order_id,
            "deliverableId": _feedback_deliverable_id(feedback),
            "content": feedback.content,
            "type": feedback.type.value,
            "createdAt": beijing_iso(feedback.created_at),
            "createdBy": feedback.created_by,
            "createdByName": current_user.username
        }
    
    @staticmethod
    async def advance_contract(
        db: AsyncSession,
        order_id: str,
        contract_number: str,
        payment_amount: float,
        note: Optional[str],
        current_user: AnyUser
    ) -> dict:
        """管理员填写合同信息并推进订单到制作阶段"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="只有管理员可以推进合同流程")
        
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        if order.status != OrderStatus.PENDING_CONTRACT:
            raise HTTPException(
                status_code=400, 
                detail=f"只有处于'合同与付款'状态的订单才能推进，当前状态：{order.status.value}"
            )
        
        # 验证状态转换
        OrderStateMachine.validate_transition(order.status, OrderStatus.IN_PRODUCTION)
        
        # 保存合同信息到 order_data
        order_data = order.order_data.copy()
        now = beijing_now()
        order_data["contractInfo"] = {
            "contractNumber": contract_number,
            "paymentAmount": payment_amount,
            "note": note or "",
            "confirmedAt": now.isoformat(),
            "confirmedBy": current_user.id,
            "confirmedByName": current_user.real_name or current_user.username
        }
        
        old_status = order.status
        order.order_data = order_data
        order.status = OrderStatus.IN_PRODUCTION
        
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "order_contract_advanced",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            contract_number=contract_number,
            payment_amount=payment_amount,
            status_from=old_status,
            status_to=order.status,
        )
        
        # 通知用户：订单已进入制作阶段
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if user and user.email:
            email_sent = await EmailService.send_order_status_notification(
                user.email,
                order.order_number,
                old_status.value,
                OrderStatus.IN_PRODUCTION.value
            )
            _log_email_result(
                "order_status_email_sent",
                email_sent,
                order_id=order.id,
                order_number=order.order_number,
                user_id=order.user_id,
                status_from=old_status,
                status_to=OrderStatus.IN_PRODUCTION,
                email=user.email,
            )
        
        await NotificationService.create_notification(
            db=db,
            user_id=order.user_id,
            notification_type=NotificationType.ORDER_STATUS_CHANGED,
            title="订单已进入制作阶段",
            content=f"您的订单 {order.order_number} 合同已确认，首付款已收到，订单已正式进入制作流程。",
            order_id=order.id
        )
        
        # 通知负责人
        assignee_ids = await _get_order_assignee_ids(db, order.id)
        if assignee_ids:
            await NotificationService.create_notification_for_multiple_users(
                db=db,
                user_ids=assignee_ids,
                notification_type=NotificationType.ORDER_STATUS_CHANGED,
                title="订单进入制作阶段",
                content=f"订单 {order.order_number} 合同已确认，可以开始制作。",
                order_id=order.id
            )
        
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def admin_cancel_order(
        db: AsyncSession,
        order_id: str,
        phone: str,
        sms_code: str,
        reason: Optional[str],
        current_user: AnyUser
    ) -> dict:
        """管理员通过 SMS 验证取消订单"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="只有管理员可以取消订单")
        
        # 验证短信验证码
        from app.services.sms_service import verify_sms_code
        is_valid = await verify_sms_code(phone, sms_code)
        if not is_valid:
            raise HTTPException(status_code=400, detail="验证码错误或已过期")
        
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="该订单无法取消")
        
        old_status = order.status
        
        # 保存取消原因到 order_data
        order_data = order.order_data.copy()
        now = beijing_now()
        order_data["cancelInfo"] = {
            "reason": reason or "",
            "cancelledAt": now.isoformat(),
            "cancelledBy": current_user.id,
            "cancelledByName": current_user.real_name or current_user.username
        }
        
        order.order_data = order_data
        order.status = OrderStatus.CANCELLED
        
        await db.commit()
        await db.refresh(order)
        log_business_event(
            logger,
            "order_cancelled_by_admin",
            order_id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            status_from=old_status,
            status_to=order.status,
            reason_present=bool(reason),
        )
        
        # 通知用户订单已取消
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        cancel_reason_text = f"取消原因：{reason}" if reason else ""
        
        if user and user.email:
            email_sent = await EmailService.send_order_status_notification(
                user.email,
                order.order_number,
                old_status.value,
                OrderStatus.CANCELLED.value
            )
            _log_email_result(
                "order_status_email_sent",
                email_sent,
                order_id=order.id,
                order_number=order.order_number,
                user_id=order.user_id,
                status_from=old_status,
                status_to=OrderStatus.CANCELLED,
                email=user.email,
            )
        
        await NotificationService.create_notification(
            db=db,
            user_id=order.user_id,
            notification_type=NotificationType.ORDER_CANCELLED,
            title="订单已取消",
            content=f"您的订单 {order.order_number} 已被管理员取消。{cancel_reason_text}",
            order_id=order.id
        )
        
        # 通知负责人
        assignee_ids = await _get_order_assignee_ids(db, order.id)
        if assignee_ids:
            await NotificationService.create_notification_for_multiple_users(
                db=db,
                user_ids=assignee_ids,
                notification_type=NotificationType.ORDER_CANCELLED,
                title="订单已取消",
                content=f"订单 {order.order_number} 已被管理员取消。{cancel_reason_text}",
                order_id=order.id
            )
        
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def _build_order_response(db: AsyncSession, order: Order, current_user) -> dict:
        """构建订单响应"""
        # 获取用户信息（从 users 表，即客户表）
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        
        # 获取所有负责人信息（从 staff_members 表）
        assignees_result = await db.execute(
            select(OrderAssignee, StaffMember).join(
                StaffMember, OrderAssignee.assignee_id == StaffMember.id
            ).where(OrderAssignee.order_id == order.id)
        )
        assignees_data = []
        for order_assignee, assignee_staff in assignees_result.all():
            assignees_data.append({
                "id": assignee_staff.id,
                "name": assignee_staff.real_name or assignee_staff.username
            })
        
        feedback_responses = []
        # 客户原始反馈仅客户本人和管理员可见，制作者只接收管理员整理后的意见。
        if _can_view_customer_feedback(current_user):
            feedbacks_result = await db.execute(
                select(Feedback).where(Feedback.order_id == order.id).order_by(Feedback.created_at.asc())
            )
            feedbacks = feedbacks_result.scalars().all()

            for feedback in feedbacks:
                creator_result = await db.execute(select(User).where(User.id == feedback.created_by))
                creator = creator_result.scalar_one_or_none()

                feedback_responses.append({
                    "id": feedback.id,
                    "orderId": feedback.order_id,
                    "deliverableId": _feedback_deliverable_id(feedback),
                    "content": feedback.content,
                    "type": feedback.type.value,
                    "createdAt": beijing_iso(feedback.created_at),
                    "createdBy": feedback.created_by,
                    "createdByName": creator.username if creator else None
                })
        
        # 基础响应数据
        base_response = {
            "id": order.id,
            "orderNumber": order.order_number,
            "orderType": order.order_type.value,
            "status": order.status.value,
            "userId": order.user_id,
            "userName": user.username if user else None,
            "userEnterprise": user.enterprise_name if user else None,
            "userPhone": user.phone if user else None,
            "userEmail": user.email if user else None,
            "assignees": assignees_data,
            "createdAt": beijing_iso(order.created_at),
            "updatedAt": beijing_iso(order.updated_at),
            "feedbacks": feedback_responses,
            "revisionCount": order.revision_count,
            "previewHistory": order.order_data.get("previewHistory", []),  # 预览历史记录
            "pendingReviewPreviewIds": order.order_data.get("pendingReviewPreviewIds", []),
            "contractInfo": order.order_data.get("contractInfo", None),  # 合同信息
            "cancelInfo": order.order_data.get("cancelInfo", None)  # 取消信息
        }
        
        # 合并订单特定数据
        base_response.update(order.order_data)
        
        # 获取已发布给用户的承包商交付物
        try:
            from app.models.contractor_deliverable import ContractorDeliverable
            from app.models.contractor_assignment import ContractorAssignment
            from app.models.staff_deliverable import StaffDeliverable
            from app.models.staff_assignment import StaffAssignment
            from app.services.staff_creator_service import serialize_staff_deliverable_for_user
            
            published_dlv_result = await db.execute(
                select(ContractorDeliverable)
                .join(ContractorAssignment, ContractorDeliverable.assignment_id == ContractorAssignment.id)
                .where(
                    ContractorAssignment.order_id == order.id,
                    ContractorDeliverable.is_published_to_user == True
                )
                .order_by(ContractorDeliverable.published_at.desc(), ContractorDeliverable.created_at.desc())
            )
            published_deliverables = published_dlv_result.scalars().all()

            staff_published_dlv_result = await db.execute(
                select(StaffDeliverable)
                .join(StaffAssignment, StaffDeliverable.assignment_id == StaffAssignment.id)
                .where(
                    StaffAssignment.order_id == order.id,
                    StaffDeliverable.is_published_to_user == True
                )
                .order_by(StaffDeliverable.published_at.desc(), StaffDeliverable.created_at.desc())
            )
            staff_published_deliverables = staff_published_dlv_result.scalars().all()
            
            published_items = []
            for dlv in published_deliverables:
                published_items.append({
                    "id": dlv.id,
                    "creatorType": "contractor",
                    "stageName": dlv.stage_name,
                    "stageOrder": dlv.stage_order,
                    "version": dlv.version,
                    "files": dlv.files or [],
                    "description": dlv.description,
                    "publishedNote": dlv.published_note,
                    "publishedAt": _iso_beijing(dlv.published_at),
                    "createdAt": _iso_beijing(dlv.created_at),
                })
            for dlv in staff_published_deliverables:
                published_items.append(serialize_staff_deliverable_for_user(dlv))

            if published_items:
                base_response["publishedDeliverables"] = sorted(
                    published_items,
                    key=lambda item: item.get("publishedAt") or item.get("createdAt") or "",
                    reverse=True,
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"获取已发布交付物失败: {e}")
        
        # OSS 模式下：为所有文件 URL 字段生成签名 URL
        if settings.OSS_ENABLED:
            _sign_file_urls_in_response(base_response)
        
        return base_response


def _sign_file_urls_in_response(data: dict):
    """为订单响应中所有文件 URL 生成 OSS 签名 URL。

    处理字段：
    - scenePhotos[].url
    - scenePhotos[].file_url
    - materials[].url
    - materials[].file_url
    - previewFiles[].url
    - previewHistory[].files[].url
    - site_photos[].url / site_photos[].file_url
    - designPlan.files[].url / designPlan.files[].file_url
    - publishedDeliverables[].files[].url / publishedDeliverables[].files[].file_url
    """
    from app.services.oss_service import sign_file_url_fields

    # 签名单个文件对象的 url 字段
    def _sign_file_item(item):
        if isinstance(item, dict):
            sign_file_url_fields(item)

    # scenePhotos
    for photo in data.get("scenePhotos", []) or []:
        _sign_file_item(photo)

    # digital_art materials
    for material in data.get("materials", []) or []:
        _sign_file_item(material)

    # site_photos（承包商端脱敏后的字段名）
    for photo in data.get("site_photos", []) or []:
        _sign_file_item(photo)

    # previewFiles
    for f in data.get("previewFiles", []) or []:
        _sign_file_item(f)

    # previewHistory -> files
    for entry in data.get("previewHistory", []) or []:
        for f in entry.get("files", []) or []:
            _sign_file_item(f)

    # publishedDeliverables -> files
    for dlv in data.get("publishedDeliverables", []) or []:
        for f in dlv.get("files", []) or []:
            _sign_file_item(f)

    # designPlan -> files
    design_plan = data.get("designPlan") or data.get("design_plan") or {}
    for f in design_plan.get("files", []) or []:
        _sign_file_item(f)
