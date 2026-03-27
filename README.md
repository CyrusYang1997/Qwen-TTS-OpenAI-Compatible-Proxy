# Qwen-TTS OpenAI Proxy

将阿里云百炼 Qwen-TTS 接口包装成 OpenAI API 兼容形式的代理服务。

## OpenClaw使用，
将以下内容加入openclaw.config中
"messages": {
    "tts": {
      "auto": "tagged",
      "provider": "openai",
      "openai": {
        "apiKey": "sk-**************",
        "baseUrl": "http://localhost:8000/v1",
        "model": "qwen3-tts-vc-2026-01-22",
        "voice": "Cherry"
      }
    }

## 快速开始

### 1. 获取 API Key

前往 [阿里云百炼平台](https://bailian.console.aliyun.com/) 注册并获取 API Key。

### 2. 配置

复制 `.env.example` 为 `.env`，填入你的 API Key：

```
DASHSCOPE_API_KEY=sk-your-api-key-here
```

### 3. 启动

双击 `start.bat` 即可启动服务，默认监听 `http://localhost:8000`。

## API 使用

### 语音合成

```bash
curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-tts-flash","input":"你好，世界！","voice":"alloy"}' \
  --output speech.mp3
```

### Python 示例（OpenAI SDK）

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-your-key")
response = client.audio.speech.create(
    model="qwen3-tts-flash",
    voice="alloy",
    input="你好，世界！"
)
response.stream_to_file("output.mp3")
```

## 支持的模型

| 模型 | 说明 |
|------|------|
| `qwen3-tts-flash` | 高质量低延迟，推荐 |
| `qwen3-tts-instruct-flash` | 支持自然语言指令控制风格 |
| `qwen-tts` | 原始版本 |

## 音色映射

| OpenAI Voice | Qwen Voice | 说明 |
|---|---|---|
| `alloy` | Cherry | 阳光活泼女声（默认） |
| `echo` | Ethan | 标准男声 |
| `fable` | Serena | 温柔女声 |
| `onyx` | Ethan | 标准男声 |
| `nova` | Chelsie | 虚拟女友风格 |
| `shimmer` | Momo | 可爱俏皮女声 |

> 也可以直接传入 Qwen-TTS 原生音色名称，如 `Cherry`、`Serena` 等。

## 支持的音频格式

`mp3`（默认）、`wav`、`pcm`

## 配置项

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | - | 百炼平台 API Key（必需） |
| `SERVER_PORT` | `8000` | 服务端口 |
| `DEFAULT_MODEL` | `qwen3-tts-flash` | 默认模型 |
| `DEFAULT_VOICE` | `Cherry` | 默认音色 |
| `DEFAULT_FORMAT` | `mp3` | 默认音频格式 |
