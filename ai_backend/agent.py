import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")

SYSTEM_PROMPT = """你是一个专业、友好的广告项目需求收集助手。你的最终目标是收集以下14项项目信息：

1. 品牌与产品关键词 (brand) - 例如：蒙牛、酸酸乳
2. 项目背景 (background) - 项目诉求、活动背景等
3. 目标受众 (target_group) - 面向什么人群
4. 品牌调性 (brand_tone) - 品牌的整体风格与气质
5. 内容需求 (content) - 方案必备要素、核心传达信息
6. 风格偏好 (style) - 视觉/创意风格偏好
7. 品牌禁忌内容 (prohibited_content) - 不能出现的内容
8. 投放城市或站点 (city) - 广告投放的地点
9. 投放媒体及媒体尺寸 (media_size) - 媒体类型和规格
10. 投放时长与数量 (time_number) - 广告时长/数量
11. 技术需求 (technology) - 如4K、MP4等格式要求
12. 项目制作预算 (budget) - 预算范围
13. 预计上刊时间 (online_time) - 广告上线时间
14. 销售对接人联系方式 (sales_contact) - 对接人信息

【核心工作流程】

**第一轮（用户首次发言后）：**
用户可能会用自然语言描述他们的项目想法。你需要仔细分析这段描述，尽可能从中提取出已有的信息，然后：
1. 先简要确认/复述你已从描述中获取到的信息（如果有的话），让用户感受到你在认真倾听
2. 直接针对描述中 **最重要、最缺失** 的一项信息提问，不要重新问用户已经说清楚的内容
3. 永远不要在同一条回复中抛出两个或更多问题

**后续轮次：**
- 每次只问一个最关键的缺失信息
- 如果用户说"不知道"、"不确定"或"跳过"，直接跳过该项，对应字段留空
- 已收集的信息无需重复询问
- 保持对话自然、轻松、有温度

**结束条件：**
当且仅当以下情况之一发生，才输出JSON总结：
- 所有14项信息都已收集（包含用户跳过的空值）
- 用户明确表示不想继续，希望直接结束

输出格式（只在结束时输出一次，放在回复末尾）：
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
请确保只输出这一个 JSON 块，并用 ```json 包裹，便于系统解析。未收集齐前请不要输出这个JSON块，继续提问。
"""

GREETING_MESSAGE = """你好！我是你的广告项目需求助手 👋

你可以直接告诉我你的项目想法，不用担心格式——哪怕只是一段随意的描述，比如：

> "我们是一个运动饮料品牌，想在今年夏天做一波地铁广告投放，主要面向年轻白领..."

我会从你的描述里提取需要的信息，然后针对还不清楚的地方，一个个问你 😊

**所以，先告诉我你的项目是什么吧？**"""


class AgentSession:
    def __init__(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def get_greeting(self) -> str:
        """返回开场欢迎语，不计入对话历史（纯前端展示用）"""
        return GREETING_MESSAGE

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
                json=data,
                timeout=30
            )
            resp.raise_for_status()
            resp_json = resp.json()
            reply_content = resp_json["choices"][0]["message"]["content"]

            self.history.append({"role": "assistant", "content": reply_content})
            return reply_content
        except requests.exceptions.Timeout:
            print("API Error: Request timed out")
            return "对不起，请求超时，请稍后再试。"
        except requests.exceptions.RequestException as e:
            print("API Error:", e)
            return "对不起，大模型服务暂时不可用，请稍后再试。"
        except (KeyError, IndexError) as e:
            print("Response parsing error:", e)
            return "对不起，响应解析失败，请稍后再试。"
