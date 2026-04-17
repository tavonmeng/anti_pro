import asyncio
from app.services.email_service import EmailService

async def test():
    print("Testing SMTP connection using environment variables...")
    service = EmailService()
    try:
        await service.send_email(
            to_emails=["uniquevideo@163.com"],
            subject="Test System Mail",
            html_content="<p>Hello, your SMTP configuration is successfully working!</p>"
        )
        print("Successfully connected and sent to uniquevideo@163.com!")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test())
