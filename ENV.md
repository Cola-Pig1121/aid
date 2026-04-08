# Environment Variables

<!-- AUTO-GENERATED from config.toml.example -->
<!-- Do not edit manually -->

## Configuration

This project uses `config.toml` for configuration. Copy `config.toml.example` to `config.toml` and fill in your values.

## Model Configuration

### ModelScope (Recommended)

| Key | Required | Description | Default |
|-----|----------|-------------|---------|
| `modelscope.api_key` | Yes* | ModelScope API Key | - |
| `modelscope.base_url` | No | API base URL | `https://api-inference.modelscope.cn/v1` |
| `modelscope.model` | No | Model name | `Qwen/Qwen3.5-27B` |

### OpenRouter (Alternative)

| Key | Required | Description | Default |
|-----|----------|-------------|---------|
| `openrouter.api_key` | Yes* | OpenRouter API Key | - |
| `openrouter.base_url` | No | API base URL | `https://openrouter.ai/api/v1` |
| `openrouter.model` | No | Model name | `qwen/qwen-2.5-72b-instruct` |

*At least one of `modelscope.api_key` or `openrouter.api_key` is required.

### LLM Settings

| Key | Required | Description | Default |
|-----|----------|-------------|---------|
| `llm.temperature` | No | Sampling temperature (0.0-1.0) | `0.7` |
| `llm.max_tokens` | No | Maximum generated tokens | `4096` |

### Server Settings

| Key | Required | Description | Default |
|-----|----------|-------------|---------|
| `server.port` | No | Web server port | `7860` |

### Search Configuration

| Key | Required | Description |
|-----|----------|-------------|
| `search.api_key` | Recommended | Tavily API Key for web search |

### Location Services

| Key | Required | Description |
|-----|----------|-------------|
| `location.tencent_key` | Yes | Tencent Maps API Key |
| `location.tencent_sk` | Yes | Tencent Maps Secret Key |

## Example Configuration

```toml
[modelscope]
api_key = "your_modelscope_api_key_here"
model = "Qwen/Qwen3.5-27B"

[llm]
temperature = 0.7
max_tokens = 4096

[server]
port = 7860

[search]
api_key = "your_tavily_api_key_here"

[location]
tencent_key = "your_tencent_map_key"
tencent_sk = "your_tencent_map_sk"
```

## Obtaining API Keys

- **ModelScope**: https://www.modelscope.cn/my/myaccesstoken
- **OpenRouter**: https://openrouter.ai/keys
- **Tavily**: https://tavily.com/
- **Tencent Maps**: https://lbs.qq.com/

<!-- END AUTO-GENERATED -->
