"""邮件服务"""

import aiosmtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict

from app.config import settings


class EmailService:
    """邮件服务类"""
    
    @staticmethod
    async def send_email(
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, bytes]]] = None
    ):
        """
        发送邮件
        attachments 格式: [{"filename": "xxx.pdf", "content": b"..."}]
        """
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            print(f"邮件服务未配置，跳过发送邮件: {subject}")
            return
        
        # 创建邮件
        message = MIMEMultipart("mixed")
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        message["To"] = ", ".join(to_emails)
        
        # 邮件正文 (alternative 容器放置 text 和 html)
        body = MIMEMultipart("alternative")
        
        # 添加文本内容
        if text_content:
            part1 = MIMEText(text_content, "plain", "utf-8")
            body.attach(part1)
        
        # 添加 HTML 内容
        part2 = MIMEText(html_content, "html", "utf-8")
        body.attach(part2)
        
        message.attach(body)
        
        # 添加附件
        if attachments:
            for item in attachments:
                attachment = MIMEApplication(item["content"])
                attachment.add_header('Content-Disposition', 'attachment', filename=item["filename"])
                message.attach(attachment)
        
        try:
            # 解决某些服务器（如macOS本地）证书验证失败的问题
            tls_context = ssl.create_default_context()
            tls_context.check_hostname = False
            tls_context.verify_mode = ssl.CERT_NONE

            # 发送邮件
            result = await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=True,
                tls_context=tls_context
            )
            print(f"邮件发送成功: {subject} -> {to_emails}")
            return True
        except Exception as e:
            print(f"邮件发送失败: {e}")
    
    @staticmethod
    async def send_order_confirmation(
        user_email: str,
        order_number: str,
        pdf_bytes: bytes
    ):
        """发送订单确认通知，含需求确认函 PDF"""
        subject = f"需求已确认 - 订单 {order_number} 将进入制作流程"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    订单需求确认成功
                </h2>
                <p>您好，</p>
                <p>您的订单 <strong>{order_number}</strong> 的需求内容我们已收到并确认。</p>
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #27ae60; font-weight: bold;">✅ 订单即将进入排期并开始制作！</p>
                </div>
                <p>为方便您的留档与核对，我们随信附上了本次订单的<strong>《需求告知函》PDF文件</strong>（见附件），里面包含了所有的需求细节及预计制作周期。</p>
                <p>在制作过程中如果您有任何问题，可以随时登录系统查看订单进度状态。</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    此邮件由系统自动发送，请勿回复。<br>
                    AI设计任务管理系统
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        订单需求确认成功
        
        您好，
        
        您的订单 {order_number} 的需求内容我们已收到并确认。
        ✅ 订单即将进入排期并开始制作！
        
        为方便您的留档与核对，我们随信附上了本次订单的《需求告知函》PDF文件（见附件），里面包含了所有的需求细节及预计制作周期。
        
        在制作过程中如果您有任何问题，可以随时登录系统查看订单进度状态。
        
        此邮件由系统自动发送，请勿回复。
        AI设计任务管理系统
        """
        
        attachments = [{
            "filename": f"订单需求告知函_{order_number}.pdf",
            "content": pdf_bytes
        }]
        
        await EmailService.send_email(
            [user_email], 
            subject, 
            html_content, 
            text_content, 
            attachments=attachments
        )

    @staticmethod
    async def send_order_status_notification(
        user_email: str,
        order_number: str,
        old_status: str,
        new_status: str
    ):
        """发送订单状态变更通知"""
        status_names = {
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
        
        subject = f"订单状态更新通知 - {order_number}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    订单状态更新
                </h2>
                <p>您好，</p>
                <p>您的订单 <strong>{order_number}</strong> 状态已更新：</p>
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 10px 0;">
                        <span style="color: #7f8c8d;">原状态：</span>
                        <strong>{status_names.get(old_status, old_status)}</strong>
                    </p>
                    <p style="margin: 10px 0;">
                        <span style="color: #27ae60;">新状态：</span>
                        <strong style="color: #27ae60;">{status_names.get(new_status, new_status)}</strong>
                    </p>
                </div>
                <p>请登录系统查看详情。</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    此邮件由系统自动发送，请勿回复。<br>
                    AI设计任务管理系统
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        订单状态更新
        
        您好，
        
        您的订单 {order_number} 状态已更新：
        原状态：{status_names.get(old_status, old_status)}
        新状态：{status_names.get(new_status, new_status)}
        
        请登录系统查看详情。
        
        此邮件由系统自动发送，请勿回复。
        AI设计任务管理系统
        """
        
        await EmailService.send_email([user_email], subject, html_content, text_content)
    
    @staticmethod
    async def send_preview_ready_notification(
        user_email: str,
        order_number: str,
        preview_type: str = "初稿"
    ):
        """发送预览文件就绪通知"""
        subject = f"{preview_type}预览已就绪 - {order_number}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    {preview_type}预览已就绪
                </h2>
                <p>您好，</p>
                <p>您的订单 <strong>{order_number}</strong> 的{preview_type}预览文件已上传。</p>
                <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p>请登录系统查看并提供反馈意见。</p>
                </div>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">
                    此邮件由系统自动发送，请勿回复。<br>
                    AI设计任务管理系统
                </p>
            </div>
        </body>
        </html>
        """
        
        await EmailService.send_email([user_email], subject, html_content)

