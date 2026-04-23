import asyncio, json
from app.database import async_session_maker
from app.services.order_service import OrderService
from sqlalchemy import select
from app.models.user import User

async def main():
    async with async_session_maker() as db:
        user_result = await db.execute(select(User))
        user = user_result.scalars().first()
        if user:
            orders = await OrderService.get_orders(db, user)
            with open("test_orders.json", "w") as f:
                json.dump(orders, f, ensure_ascii=False, indent=2)
            print("Dumped orders.")
asyncio.run(main())
