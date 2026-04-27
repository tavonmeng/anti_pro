"""语音识别服务

提供两种识别模式：
1. /api/asr/recognize (POST) — 一次性识别（推荐，准确率更高）
   前端录音结束后，将完整 PCM 音频通过 HTTP POST 发送，
   后端调用阿里云 DashScope paraformer-realtime-v2 模型进行识别。

2. /api/asr/stream (WebSocket) — 实时流式识别（保留备用）
"""

import os
import ssl
import asyncio
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse
import websockets
from app.config import settings

# 强制忽略系统层面的网络代理
os.environ["NO_PROXY"] = "dashscope.aliyuncs.com,dashscope-intl.aliyuncs.com,localhost,127.0.0.1"
os.environ["no_proxy"] = "dashscope.aliyuncs.com,dashscope-intl.aliyuncs.com,localhost,127.0.0.1"

router = APIRouter(tags=["语音识别"])

DASHSCOPE_WSS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"
DASHSCOPE_FILE_API = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"


# ============================================================
# 离线一次性识别（推荐）
# ============================================================
@router.post("/asr/recognize")
async def asr_recognize(audio: UploadFile = File(...)):
    """接收完整 PCM 音频文件，调用 DashScope 识别"""
    import time
    t0 = time.time()

    api_key = settings.AI_API_KEY
    if not api_key:
        return JSONResponse({"error": "服务端未配置 AI_API_KEY"}, status_code=500)

    try:
        # 读取前端发来的 PCM 数据
        pcm_data = await audio.read()
        t1 = time.time()
        print(f"[ASR] 读取音频: {len(pcm_data)} bytes, 耗时: {(t1-t0)*1000:.0f}ms")

        if len(pcm_data) < 100:
            return JSONResponse({"error": "音频数据太短"})

        # 直接发送 PCM 数据（不做 WAV 转换，省去封装开销）
        result_text = await recognize_via_ws(api_key, pcm_data)
        t2 = time.time()
        print(f"[ASR] 识别完成: '{result_text[:50]}...', 总耗时: {(t2-t0)*1000:.0f}ms")

        return JSONResponse({"text": result_text})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


async def recognize_via_ws(api_key: str, pcm_data: bytes) -> str:
    """通过 WebSocket 调用 DashScope 语音识别（一次性发送整段 PCM 音频）"""
    import time
    task_id = uuid.uuid4().hex[:32]

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    t0 = time.time()
    async with websockets.connect(
        DASHSCOPE_WSS_URL,
        additional_headers={"Authorization": f"bearer {api_key}"},
        ping_interval=20,
        ping_timeout=10,
        ssl=ssl_context,
    ) as ws:
        t1 = time.time()
        print(f"[ASR] WebSocket 连接: {(t1-t0)*1000:.0f}ms")

        # 发送 run-task（直接用 PCM 格式，省去 WAV 封装）
        run_msg = {
            "header": {
                "action": "run-task",
                "task_id": task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": "paraformer-realtime-v2",
                "parameters": {
                    "format": "pcm",
                    "sample_rate": 16000,
                    "language_hints": ["zh"],
                },
                "input": {},
            },
        }
        await ws.send(json.dumps(run_msg))

        # 等待 task-started
        while True:
            resp = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(resp)
            event = msg.get("header", {}).get("event", "")
            if event == "task-started":
                break
            elif event == "task-failed":
                raise Exception(msg.get("header", {}).get("error_message", "任务启动失败"))

        t2 = time.time()
        print(f"[ASR] 任务启动: {(t2-t1)*1000:.0f}ms")

        # 一次性大块发送音频（64KB 每块，无人为延迟）
        chunk_size = 64 * 1024
        for i in range(0, len(pcm_data), chunk_size):
            await ws.send(pcm_data[i:i + chunk_size])

        # 发送 finish-task
        finish_msg = {
            "header": {
                "action": "finish-task",
                "task_id": task_id,
                "streaming": "duplex",
            },
            "payload": {"input": {}},
        }
        await ws.send(json.dumps(finish_msg))

        t3 = time.time()
        print(f"[ASR] 音频发送: {(t3-t2)*1000:.0f}ms")

        # 收集识别结果
        sentences = []
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=30)
                msg = json.loads(resp)
                event = msg.get("header", {}).get("event", "")

                if event == "result-generated":
                    sentence = msg.get("payload", {}).get("output", {}).get("sentence", {})
                    text = sentence.get("text", "")
                    is_end = sentence.get("sentence_end", False)
                    if is_end and text:
                        sentences.append(text)
                elif event == "task-finished":
                    break
                elif event == "task-failed":
                    raise Exception(msg.get("header", {}).get("error_message", "识别失败"))
            except asyncio.TimeoutError:
                break

        t4 = time.time()
        print(f"[ASR] 结果等待: {(t4-t3)*1000:.0f}ms")

        return "".join(sentences)


# ============================================================
# 实时流式识别（WebSocket 代理，保留备用）
# ============================================================
@router.websocket("/asr/stream")
async def asr_stream(ws: WebSocket):
    """实时语音识别 WebSocket 端点"""
    await ws.accept()

    api_key = settings.AI_API_KEY
    if not api_key:
        await ws.send_json({"type": "error", "message": "服务端未配置 AI_API_KEY"})
        await ws.close()
        return

    task_id = uuid.uuid4().hex[:32]
    ds_ws = None

    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        ds_ws = await websockets.connect(
            DASHSCOPE_WSS_URL,
            additional_headers={"Authorization": f"bearer {api_key}"},
            ping_interval=20,
            ping_timeout=10,
            ssl=ssl_context,
        )

        run_task_msg = {
            "header": {
                "action": "run-task",
                "task_id": task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": "paraformer-realtime-v2",
                "parameters": {
                    "format": "pcm",
                    "sample_rate": 16000,
                    "language_hints": ["zh"],
                },
                "input": {},
            },
        }
        await ds_ws.send(json.dumps(run_task_msg))

        started = False
        while not started:
            resp = await asyncio.wait_for(ds_ws.recv(), timeout=10)
            msg = json.loads(resp)
            event = msg.get("header", {}).get("event", "")
            if event == "task-started":
                started = True
                await ws.send_json({"type": "started"})
            elif event == "task-failed":
                err = msg.get("header", {}).get("error_message", "未知错误")
                await ws.send_json({"type": "error", "message": err})
                await ws.close()
                return

        stop_event = asyncio.Event()

        async def relay_results():
            try:
                async for raw in ds_ws:
                    if stop_event.is_set():
                        break
                    msg = json.loads(raw)
                    event = msg.get("header", {}).get("event", "")
                    if event == "result-generated":
                        sentence = msg.get("payload", {}).get("output", {}).get("sentence", {})
                        text = sentence.get("text", "")
                        is_final = sentence.get("sentence_end", False)
                        await ws.send_json({"type": "result", "text": text, "is_final": is_final})
                    elif event == "task-finished":
                        await ws.send_json({"type": "finished"})
                        break
                    elif event == "task-failed":
                        err = msg.get("header", {}).get("error_message", "识别失败")
                        await ws.send_json({"type": "error", "message": err})
                        break
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e:
                try:
                    await ws.send_json({"type": "error", "message": str(e)})
                except Exception:
                    pass

        relay_task = asyncio.create_task(relay_results())

        try:
            while True:
                data = await ws.receive()
                if data.get("type") == "websocket.disconnect":
                    break
                if "text" in data:
                    text_msg = json.loads(data["text"])
                    if text_msg.get("action") == "stop":
                        finish_msg = {
                            "header": {"action": "finish-task", "task_id": task_id, "streaming": "duplex"},
                            "payload": {"input": {}},
                        }
                        await ds_ws.send(json.dumps(finish_msg))
                        try:
                            await asyncio.wait_for(relay_task, timeout=5)
                        except asyncio.TimeoutError:
                            pass
                        break
                elif "bytes" in data:
                    audio_chunk = data["bytes"]
                    if audio_chunk and ds_ws is not None:
                        try:
                            await ds_ws.send(audio_chunk)
                        except Exception:
                            pass
        except WebSocketDisconnect:
            pass

        stop_event.set()
        if not relay_task.done():
            relay_task.cancel()
            try:
                await relay_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": f"语音识别服务异常: {str(e)}"})
        except Exception:
            pass
    finally:
        if ds_ws is not None:
            try:
                await ds_ws.close()
            except Exception:
                pass
        try:
            await ws.close()
        except Exception:
            pass
