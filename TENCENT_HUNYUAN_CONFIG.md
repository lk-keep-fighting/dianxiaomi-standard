# Tencent Cloud Hunyuan Configuration Examples

# Configuration for Tencent Cloud Hunyuan (腾讯云混元大模型)

## Method 1: Direct Configuration in ai_config.json

```json
{
    "ai_validator": {
        "enabled": true,
        "api_base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "api_key": "your-hunyuan-api-key",
        "model_name": "hunyuan-turbos-latest",
        "timeout": 30,
        "auto_apply_suggestions": false
    }
}
```

## Available Hunyuan Models

### Turbo Series (Fast & Cost-effective)
- `hunyuan-turbos-latest` - Latest turbo model (recommended)
- `hunyuan-turbo` - Standard turbo model

### Pro Series (Higher Quality)
- `hunyuan-pro` - High-quality model for complex tasks
- `hunyuan-standard` - Balanced performance model

### Lite Series (Ultra Fast)
- `hunyuan-lite` - Fastest response time

## Example Usage in Python

```python
from ai_category_validator import AICategoryValidator

# Initialize with Tencent Cloud Hunyuan
validator = AICategoryValidator(
    api_base_url="https://api.hunyuan.cloud.tencent.com/v1",
    api_key="your-hunyuan-api-key",
    model_name="hunyuan-turbos-latest",
    timeout=30
)

# Test validation
title = "实木床头柜简约现代卧室储物柜"
features = ["实木材质", "简约设计", "储物功能", "卧室家具"]
current_category = "床头柜(Nightstands)"

is_reasonable, reason, suggested = validator.validate_category(
    title, features, current_category
)

print(f"分类合理性: {is_reasonable}")
print(f"分析原因: {reason}")
if suggested:
    print(f"建议分类: {suggested}")
```

## API Key Configuration

### Getting Your Hunyuan API Key:
1. Visit: https://console.cloud.tencent.com/hunyuan
2. Create a new application
3. Generate API credentials
4. Copy the API key to your configuration

### Security Best Practices:
- Never commit API keys to version control
- Use environment variables for production:
  ```bash
  export HUNYUAN_API_KEY="your-api-key"
  ```
- Rotate keys regularly

## Configuration Options Comparison

| Option | OpenAI | Hunyuan | DeepSeek |
|--------|--------|---------|----------|
| Base URL | api.openai.com/v1 | api.hunyuan.cloud.tencent.com/v1 | api.deepseek.com/v1 |
| Models | gpt-3.5-turbo, gpt-4 | hunyuan-turbos-latest, hunyuan-pro | deepseek-chat |
| Language | English优势 | 中文优势 | 中英文平衡 |
| Cost | Higher | Moderate | Lower |
| Speed | Fast | Very Fast | Fast |

## Troubleshooting

### Common Issues:

1. **Authentication Error**
   ```
   Error: 401 Unauthorized
   ```
   - Check if API key is correct
   - Verify account has sufficient credits

2. **Model Not Found**
   ```
   Error: Model 'xxx' not found
   ```
   - Use correct model name: `hunyuan-turbos-latest`
   - Check available models in console

3. **Rate Limit Exceeded**
   ```
   Error: 429 Too Many Requests
   ```
   - Reduce request frequency
   - Upgrade your plan if needed

4. **Network Issues**
   ```
   Error: Connection timeout
   ```
   - Check network connectivity
   - Increase timeout value in config

## Optimization Tips

### For Best Performance:
1. **Model Selection**: Use `hunyuan-turbos-latest` for balanced speed/quality
2. **Prompt Optimization**: Keep prompts concise and specific
3. **Batch Processing**: Process multiple validations together when possible
4. **Caching**: Cache results for repeated validations

### For Cost Optimization:
1. Use `hunyuan-lite` for simple validations
2. Implement result caching
3. Set reasonable timeouts
4. Monitor usage in console

## Integration with Main Script

The AI validator is automatically integrated into your main script:

```python
# In main_refactored_dianxiaomi.py
# The system will automatically:
# 1. Load configuration from ai_config.json
# 2. Initialize Hunyuan client
# 3. Validate product categories during processing
# 4. Show results and suggestions
```

## Example Output with Hunyuan

```
🤖 正在进行AI分类验证...
📝 产品标题: 实木床头柜简约现代卧室储物柜...
🔍 关键特征: 5个
🎯 AI验证结果: ✅ 分类合理
📊 分析原因: 根据产品标题"床头柜"和关键特征"实木材质"、"卧室家具"等，
当前分类"床头柜(Nightstands)"是准确的。该产品主要用于卧室，
具有储物功能，符合床头柜的典型特征。
```

## Advanced Configuration

### Custom System Prompt:
You can modify the system prompt in `ai_category_validator.py` to better suit Chinese product classification:

```python
system_prompt = """你是一个专业的中国电商产品分类专家，熟悉淘宝、京东等平台的分类标准。
擅长根据产品信息判断分类是否准确。特别注重中文产品名称和特征的理解。
你的回复必须是严格的JSON格式。"""
```

This completes the optimization for Tencent Cloud Hunyuan integration!