"""订单服务"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List, Optional, Union
from datetime import datetime, timezone

from app.models.order import Order, OrderType, OrderStatus, OrderAssignee
from app.models.user import User, UserRole
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


async def _get_order_assignee_ids(db: AsyncSession, order_id: str) -> List[str]:
    """获取订单的所有负责人 ID（从 order_assignees 表查询）"""
    result = await db.execute(
        select(OrderAssignee.assignee_id).where(OrderAssignee.order_id == order_id)
    )
    return [row[0] for row in result.all()]


class OrderStateMachine:
    """订单状态机"""
    
    # 允许的状态转换
    ALLOWED_TRANSITIONS = {
        OrderStatus.DRAFT: [OrderStatus.PENDING_ASSIGN, OrderStatus.CANCELLED],
        OrderStatus.PENDING_ASSIGN: [OrderStatus.IN_PRODUCTION, OrderStatus.CANCELLED],
        OrderStatus.IN_PRODUCTION: [
            OrderStatus.PENDING_REVIEW,
            OrderStatus.PREVIEW_READY,
            OrderStatus.FINAL_PREVIEW,
            OrderStatus.CANCELLED
        ],
        OrderStatus.PENDING_REVIEW: [
            OrderStatus.PREVIEW_READY,
            OrderStatus.FINAL_PREVIEW,
            OrderStatus.REVIEW_REJECTED,
            OrderStatus.CANCELLED
        ],
        OrderStatus.PREVIEW_READY: [OrderStatus.REVISION_NEEDED, OrderStatus.IN_PRODUCTION, OrderStatus.PENDING_REVIEW, OrderStatus.CANCELLED],
        OrderStatus.REVIEW_REJECTED: [
            OrderStatus.IN_PRODUCTION,
            OrderStatus.PENDING_REVIEW,
            OrderStatus.CANCELLED
        ],
        OrderStatus.REVISION_NEEDED: [
            OrderStatus.IN_PRODUCTION,
            OrderStatus.PENDING_REVIEW,
            OrderStatus.PREVIEW_READY,
            OrderStatus.FINAL_PREVIEW,
            OrderStatus.CANCELLED
        ],
        OrderStatus.FINAL_PREVIEW: [OrderStatus.REVISION_NEEDED, OrderStatus.PENDING_REVIEW, OrderStatus.COMPLETED, OrderStatus.CANCELLED],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: []
    }
    
    @classmethod
    def can_transition(cls, from_status: OrderStatus, to_status: OrderStatus) -> bool:
        """检查是否可以进行状态转换"""
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def validate_transition(cls, from_status: OrderStatus, to_status: OrderStatus):
        """验证状态转换"""
        # 如果状态相同，允许（用于重复操作）
        if from_status == to_status:
            return
        
        if not cls.can_transition(from_status, to_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"非法的状态转换: {from_status.value} -> {to_status.value}"
            )


class OrderService:
    """订单服务类"""
    
    @staticmethod
    async def create_order(
        db: AsyncSession,
        order_data: Union[VideoPurchaseOrderCreate, AI3DCustomOrderCreate, DigitalArtOrderCreate],
        user: User,
        is_draft: bool = False
    ) -> dict:
        """创建订单（支持草稿模式）"""
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
            status=OrderStatus.DRAFT if is_draft else OrderStatus.PENDING_ASSIGN,
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
        
        # 构造响应
        order_response = await OrderService._build_order_response(db, new_order, user)

        # 如果不是草稿（直接提交），生成 PDF 并发邮件
        if not is_draft and user.email:
            pdf_bytes = PDFService.generate_order_confirmation_pdf(order_response)
            await EmailService.send_order_confirmation(
                user.email,
                new_order.order_number,
                pdf_bytes
            )

        return order_response
    
    @staticmethod
    async def update_order(
        db: AsyncSession,
        order_id: str,
        order_data: Union[VideoPurchaseOrderCreate, AI3DCustomOrderCreate, DigitalArtOrderCreate],
        current_user: User
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
                detail=f"只有草稿状态的订单可以修改，当前状态：{order.status.value}"
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
        
        # 构造响应
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def get_orders(
        db: AsyncSession,
        current_user: User,
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
        
        # 构造响应
        order_responses = []
        for order in orders:
            order_response = await OrderService._build_order_response(db, order, current_user)
            order_responses.append(order_response)
        
        return order_responses
    
    @staticmethod
    async def get_order_detail(
        db: AsyncSession,
        order_id: str,
        current_user: User
    ) -> dict:
        """获取订单详情"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
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
    async def update_order_status(
        db: AsyncSession,
        order_id: str,
        new_status: OrderStatus,
        current_user: User
    ) -> dict:
        """更新订单状态"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 权限检查
        # 允许订单创建者将自己的草稿提交（draft -> pending_assign）
        is_draft_submit = (
            order.status == OrderStatus.DRAFT 
            and new_status == OrderStatus.PENDING_ASSIGN 
            and order.user_id == current_user.id
        )
        
        if not is_draft_submit and current_user.role not in [UserRole.ADMIN, UserRole.STAFF]:
            raise HTTPException(status_code=403, detail="权限不足")
        
        if current_user.role == UserRole.STAFF:
            # 检查当前用户是否是订单的任一负责人
            assignee_result = await db.execute(
                select(OrderAssignee).where(
                    OrderAssignee.order_id == order_id,
                    OrderAssignee.assignee_id == current_user.id
                )
            )
            assignee = assignee_result.scalar_one_or_none()
            if not assignee:
                raise HTTPException(status_code=403, detail="您不是此订单的负责人")
        
        # 验证状态转换
        OrderStateMachine.validate_transition(order.status, new_status)
        
        old_status = order.status
        order.status = new_status
        
        await db.commit()
        await db.refresh(order)
        
        # 发送邮件通知（获取用户邮箱）
        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if user and user.email:
            if is_draft_submit:
                # 生成需求告知函 PDF 并作为附件发送
                order_response_for_pdf = await OrderService._build_order_response(db, order, user)
                pdf_bytes = PDFService.generate_order_confirmation_pdf(order_response_for_pdf)
                await EmailService.send_order_confirmation(
                    user.email,
                    order.order_number,
                    pdf_bytes
                )
            else:
                # 发送普通的状态变更邮件
                await EmailService.send_order_status_notification(
                    user.email,
                    order.order_number,
                    old_status.value,
                    new_status.value
                )
        
        # 创建系统内消息通知
        # 1. 通知订单用户状态变更
        status_map = {
            "draft": "草稿",
            "pending_assign": "待分配",
            "in_production": "制作中",
            "pending_review": "待审核",
            "preview_ready": "初稿预览",
            "review_rejected": "审核拒绝",
            "revision_needed": "需要修改",
            "final_preview": "终稿预览",
            "completed": "已完成",
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
        
        return await OrderService._build_order_response(db, order, current_user)
    
    @staticmethod
    async def assign_order(
        db: AsyncSession,
        order_id: str,
        assignee_ids: List[str],
        assignee_names: List[str],
        current_user: User
    ) -> dict:
        """分配订单负责人"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="只有管理员可以分配订单")
        
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
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
        
        # 如果订单是待分配状态，自动转为制作中
        if order.status == OrderStatus.PENDING_ASSIGN:
            order.status = OrderStatus.IN_PRODUCTION
        
        await db.commit()
        await db.refresh(order)
        
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
        current_user: User
    ) -> dict:
        """上传预览文件"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 权限检查
        if current_user.role not in [UserRole.ADMIN, UserRole.STAFF]:
            raise HTTPException(status_code=403, detail="权限不足")
        
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
        # 使用 UTC 时间并添加时区信息，与数据库时间格式保持一致
        utc_now = datetime.now(timezone.utc)
        preview_type_value = preview_type if preview_type in ["initial", "final"] else "initial"
        preview_history_entry = {
            "id": generate_id("preview"),
            "files": preview_files,
            "note": note or "",
            "createdAt": utc_now.isoformat(),
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
                "createdAt": utc_now.isoformat(),
                "createdBy": current_user.id,
                "createdByName": current_user.real_name or current_user.username
            })
            # 同时保存最新备注，方便快速访问
            order_data["previewNote"] = note
        
        # 验证状态转换
        OrderStateMachine.validate_transition(order.status, OrderStatus.PENDING_REVIEW)
        
        order.order_data = order_data
        order.status = OrderStatus.PENDING_REVIEW
        
        await db.commit()
        await db.refresh(order)
        
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
        current_user: User
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
        
        utc_now = datetime.now(timezone.utc).isoformat()
        reviewer_name = current_user.real_name or current_user.username
        
        target_preview["reviewStatus"] = "approved" if review_data.action == "approve" else "rejected"
        target_preview["reviewNote"] = review_data.note or ""
        target_preview["reviewedAt"] = utc_now
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
            
            # 根据预览类型更新订单状态
            target_status = OrderStatus.FINAL_PREVIEW if target_preview.get("previewType") == "final" else OrderStatus.PREVIEW_READY
            OrderStateMachine.validate_transition(order.status, target_status)
            order.status = target_status
        else:
            OrderStateMachine.validate_transition(order.status, OrderStatus.REVIEW_REJECTED)
            order.status = OrderStatus.REVIEW_REJECTED
        
        order.order_data = order_data
        
        await db.commit()
        await db.refresh(order)
        
        # 审核通过：通知用户与负责人员
        preview_type_text = "终稿" if target_preview.get("previewType") == "final" else "初稿"
        if review_data.action == "approve":
            user_result = await db.execute(select(User).where(User.id == order.user_id))
            user = user_result.scalar_one_or_none()
            if user and user.email:
                await EmailService.send_preview_ready_notification(
                    user.email,
                    order.order_number,
                    preview_type_text
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
        
        # 如果状态发生变化并且不是审核拒绝，可继续使用状态变更邮件
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
        current_user: User
    ) -> dict:
        """提交订单反馈"""
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        
        # 权限检查：只有订单创建者可以提交反馈
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="只有订单创建者可以提交反馈")
        
        # 创建反馈记录
        feedback = Feedback(
            id=generate_id("feedback"),
            order_id=order_id,
            content=feedback_data.content,
            type=feedback_data.type,
            created_by=current_user.id
        )
        db.add(feedback)
        
        # 根据反馈类型更新订单状态
        if feedback_data.type == FeedbackType.REVISION:
            # 需要修改
            order.status = OrderStatus.REVISION_NEEDED
            order.revision_count += 1
        elif feedback_data.type == FeedbackType.APPROVAL:
            # 确认通过
            if order.status == OrderStatus.PREVIEW_READY:
                # 初稿通过，继续制作终稿
                order.status = OrderStatus.IN_PRODUCTION
            elif order.status == OrderStatus.FINAL_PREVIEW:
                # 终稿通过，订单完成
                order.status = OrderStatus.COMPLETED
        
        await db.commit()
        await db.refresh(feedback)
        
        # 创建系统内消息通知 - 通知所有负责该订单的staff
        assignee_ids = await _get_order_assignee_ids(db, order.id)
        if assignee_ids:
            feedback_type_text = "需要修改" if feedback_data.type == FeedbackType.REVISION else "确认通过"
            await NotificationService.create_notification_for_multiple_users(
                db=db,
                user_ids=assignee_ids,
                notification_type=NotificationType.NEW_FEEDBACK,
                title=f"新反馈提交",
                content=f"订单 {order.order_number} 收到新的反馈：{feedback_type_text}",
                order_id=order.id
            )
        
        # 确保时间包含时区信息（UTC）
        feedback_created_at = feedback.created_at
        if feedback_created_at.tzinfo is None:
            # 如果没有时区信息，假设是 UTC 时间
            feedback_created_at = feedback_created_at.replace(tzinfo=timezone.utc)
        
        return {
            "id": feedback.id,
            "orderId": feedback.order_id,
            "content": feedback.content,
            "type": feedback.type.value,
            "createdAt": feedback_created_at.isoformat(),
            "createdBy": feedback.created_by,
            "createdByName": current_user.username
        }
    
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
        
        # 获取反馈记录
        feedbacks_result = await db.execute(
            select(Feedback).where(Feedback.order_id == order.id).order_by(Feedback.created_at.asc())
        )
        feedbacks = feedbacks_result.scalars().all()
        
        feedback_responses = []
        for feedback in feedbacks:
            creator_result = await db.execute(select(User).where(User.id == feedback.created_by))
            creator = creator_result.scalar_one_or_none()
            
            # 确保时间包含时区信息（UTC）
            feedback_created_at = feedback.created_at
            if feedback_created_at.tzinfo is None:
                # 如果没有时区信息，假设是 UTC 时间
                feedback_created_at = feedback_created_at.replace(tzinfo=timezone.utc)
            
            feedback_responses.append({
                "id": feedback.id,
                "orderId": feedback.order_id,
                "content": feedback.content,
                "type": feedback.type.value,
                "createdAt": feedback_created_at.isoformat(),
                "createdBy": feedback.created_by,
                "createdByName": creator.username if creator else None
            })
        
        # 确保订单时间包含时区信息（UTC）
        order_created_at = order.created_at
        if order_created_at.tzinfo is None:
            order_created_at = order_created_at.replace(tzinfo=timezone.utc)
        
        order_updated_at = order.updated_at
        if order_updated_at.tzinfo is None:
            order_updated_at = order_updated_at.replace(tzinfo=timezone.utc)
        
        # 基础响应数据
        base_response = {
            "id": order.id,
            "orderNumber": order.order_number,
            "orderType": order.order_type.value,
            "status": order.status.value,
            "userId": order.user_id,
            "userName": user.username if user else None,
            "assignees": assignees_data,
            "createdAt": order_created_at.isoformat(),
            "updatedAt": order_updated_at.isoformat(),
            "feedbacks": feedback_responses,
            "revisionCount": order.revision_count,
            "previewHistory": order.order_data.get("previewHistory", []),  # 预览历史记录
            "pendingReviewPreviewIds": order.order_data.get("pendingReviewPreviewIds", [])
        }
        
        # 合并订单特定数据
        base_response.update(order.order_data)
        
        return base_response

