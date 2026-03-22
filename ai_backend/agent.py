import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")

SYSTEM_PROMPT = """你是一个专业的项目需求收集助手。你的任务是引导用户在聊天过程中，逐步收集以下项目的需求详情（共14项）：
1. 品牌与产品关键词 (例如：蒙牛；酸酸乳；酸酸甜甜好滋味)
2. 项目背景
3. 目标受众
4. 品牌调性
5. 内容需求 (方案必备要素)
6. 风格偏好有哪些
7. 品牌禁忌内容
8. 投放城市或站点
9. 投放媒体及媒体尺寸
10. 投放时长与数量
11. 技术需求 (如4K、MP4)
12. 项目制作预算
13. 预计上刊时间
14. 销售对接人联系方式

【重要规则】
- 一次只问1-2个问题，不要一次性问所有问题，保持对话自然。
- 如果用户没有提供足够信息，可以适当追问。
- 如果用户表示不知道、不确定，或者不想回答某条需求，你可以直接跳过该问题。不需要强求用户回答，这类未回答的项目在最终生成的JSON中对应的值置为空字符串（""），因为用户可以在最终的表格中自行填写和修改。
- 当且仅当你收集齐了所有的14项信息（包含用户明确跳过的部分），或者用户明确表示不想继续聊了/希望直接结束，你需要总结用户提供的信息，并在你的回复末尾附带一个JSON格式的数据块，格式如下：
```json
{
  "brand": "...",
  "background": "...",
  "target_group": "...",
  "brand_tone": "...",
  "content": "...",
  "style": "...",
  "prohibited_content": "...",
  "city": "...",
  "media_size": "...",
  "time_number": "...",
  "technology": "...",
  "budget": "...",
  "online_time": "...",
  "sales_contact": "..."
}
```
请确保只输出这一个 JSON 块，并用 ` ```json ` 包裹，便于系统解析。如果没有收集齐，请不要输出这个JSON块，继续提问即可。
"""

class AgentSession:
    def __init__(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "qwen-plus",
            "messages": self.history
        }
        
        try:
            resp = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers=headers,
                json=data
            )
            resp.raise_for_status()
            resp_json = resp.json()
            reply_content = resp_json["choices"][0]["message"]["content"]
            
            self.history.append({"role": "assistant", "content": reply_content})
            return reply_content
        except Exception as e:
            print("API Error:", e)
            return "对不起，大模型服务暂时不可用，请稍后再试。"
