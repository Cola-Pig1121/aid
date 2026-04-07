# Environment Variables

<!-- AUTO-GENERATED from .env.example -->
<!-- Do not edit manually -->

## Required API Keys

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `MODELSCOPE_API_KEY` | Yes* | ModelScope API Key for LLM access | `your_modelscope_api_key_here` |
| `OPENROUTER_API_KEY` | Yes* | OpenRouter API Key (fallback) | `your_openrouter_api_key_here` |
| `TAVILY_API_KEY` | Recommended | Tavily API Key for web search | `your_tavily_api_key_here` |
| `TENCENT_MAP_KEY` | Yes | Tencent Maps API Key for geocoding | `your_tencent_key` |
| `TENCENT_MAP_SK` | Yes | Tencent Maps Secret Key for SN signature | `your_tencent_sk` |

*At least one of `MODELSCOPE_API_KEY` or `OPENROUTER_API_KEY` is required.

## Model Configuration

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `MODELSCOPE_BASE_URL` | No | ModelScope API base URL | `https://api-inference.modelscope.cn/v1` |
| `MODELSCOPE_MODEL` | No | ModelScope model name | `Qwen/Qwen3.5-27B` |
| `OPENROUTER_BASE_URL` | No | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | No | OpenRouter model name | `qwen/qwen-2.5-72b-instruct` |
| `LLM_TEMPERATURE` | No | LLM sampling temperature (0.0-1.0) | `0.7` |

## Server Configuration

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `GRADIO_SERVER_PORT` | No | Web server port | `7860` |

## Obtaining API Keys

- **ModelScope**: https://www.modelscope.cn/my/myaccesstoken
- **OpenRouter**: https://openrouter.ai/keys
- **Tavily**: https://tavily.com/
- **Tencent Maps**: https://lbs.qq.com/

<!-- END AUTO-GENERATED -->
