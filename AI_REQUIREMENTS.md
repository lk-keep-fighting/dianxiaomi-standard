# AI Category Validator Requirements

## Python Dependencies

Add the following to your requirements.txt:

```
openai>=1.3.0
```

## Installation

```bash
pip install openai>=1.3.0
```

## Verification

Test the installation:

```python
from ai_category_validator import AICategoryValidator
print("✅ AI Category Validator successfully imported!")
```

## Tencent Cloud Hunyuan Setup

1. **Install OpenAI library**: `pip install openai`
2. **Get API Key**: Visit https://console.cloud.tencent.com/hunyuan
3. **Configure**: Update `src/config/ai_config.json` with your credentials
4. **Test**: Run the validator example

## Compatibility

- **OpenAI**: ✅ Fully supported
- **Tencent Hunyuan**: ✅ Optimized for Chinese products  
- **DeepSeek**: ✅ Cost-effective alternative
- **Alibaba Qwen**: ✅ Good for multilingual
- **Local Ollama**: ✅ Privacy-focused option

The optimized validator now uses the official OpenAI Python library for better compatibility and error handling with all OpenAI-compatible APIs including Tencent Cloud Hunyuan.