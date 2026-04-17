import asyncio
import httpx

async def test_chat():
    print("Testing local AI chat endpoint...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/ai/chat",
                json={
                    "session_id": "test_123",
                    "message": "我想做一个汽车广告视频，大概需要多少钱？"
                },
                timeout=30.0
            )
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()['message']}")
            else:
                print(f"Error Details: {response.text}")
        except Exception as e:
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_chat())
