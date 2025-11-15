# AI Category Validator

AI分类验证器使用OpenAI兼容的大模型来验证产品分类是否合理。

## 配置说明

### 1. 配置文件位置
```
src/config/ai_config.json
```

### 2. 配置选项

```json
{
    "ai_validator": {
        "enabled": true,                              // 是否启用AI验证
        "api_base_url": "https://api.openai.com/v1", // API基础URL
        "api_key": "your-api-key-here",              // API密钥（必须配置）
        "model_name": "gpt-3.5-turbo",               // 模型名称
        "timeout": 30,                               // 请求超时时间(秒)
        "auto_apply_suggestions": false              // 是否自动应用建议
    }
}
```

### 3. 支持的API服务

#### OpenAI官方
```json
{
    "api_base_url": "https://api.openai.com/v1",
    "api_key": "sk-your-openai-key",
    "model_name": "gpt-3.5-turbo"
}
```

#### DeepSeek
```json
{
    "api_base_url": "https://api.deepseek.com/v1",
    "api_key": "your-deepseek-key",
    "model_name": "deepseek-chat"
}
```

#### 本地Ollama
```json
{
    "api_base_url": "http://localhost:11434/v1",
    "api_key": "ollama",
    "model_name": "llama2"
}
```

#### 其他兼容服务
任何支持OpenAI API格式的服务都可以使用，只需修改`api_base_url`即可。

## 使用方法

### 1. 启用AI验证
1. 复制配置文件模板：`src/config/ai_config.json`
2. 修改`api_key`为你的实际API密钥
3. 设置`enabled: true`

### 2. 运行程序
程序会自动在产品分类验证阶段调用AI验证器：

```
🤖 正在进行AI分类验证...
📝 产品标题: 床头柜实木简约现代卧室储物柜...
🔍 关键特征: 5个
🎯 AI验证结果: ✅ 分类合理
📊 分析原因: 根据产品标题和特征，这是一个典型的床头柜产品...
```

### 3. 处理建议
如果AI认为分类不合理，会显示建议：

```
🎯 AI验证结果: ⚠️ 分类可能不准确
💡 AI建议分类: 储物柜(Storage Cabinets)
是否采用AI建议的分类 'Storage Cabinets'? [Y]是 / [N]否: 
```

## 工作原理

1. **数据收集**：提取产品标题和关键特征（品牌、颜色、材质、尺寸等）
2. **AI分析**：发送给大模型进行分类合理性分析
3. **结果返回**：获取验证结果、分析原因和建议分类
4. **用户交互**：在手动模式下询问用户是否采用建议

## 注意事项

1. **API费用**：使用AI验证会产生API调用费用
2. **网络要求**：需要稳定的网络连接访问AI服务
3. **响应时间**：AI分析需要几秒时间，请耐心等待
4. **配置安全**：不要将API密钥提交到版本控制系统

## 故障排除

### 1. AI验证未启用
```
🤖 AI分类验证未启用或配置不完整
📝 请在 src/config/ai_config.json 中配置API密钥
```
**解决方法**：检查配置文件中的`enabled`和`api_key`设置

### 2. API请求失败
```
⚠️ AI分类验证失败: API请求失败
📝 继续使用当前分类
```
**解决方法**：
- 检查网络连接
- 验证API密钥是否正确
- 确认API服务是否可用

### 3. 响应超时
```
⚠️ AI分类验证失败: 请求超时
```
**解决方法**：增加配置中的`timeout`值或检查网络状况

## 扩展功能

### 1. 添加新的AI服务
在配置文件的`alternative_apis`部分添加新的服务配置。

### 2. 自定义验证逻辑
修改`ai_category_validator.py`中的提示词来调整验证标准。

### 3. 批量验证
可以扩展为对整个产品列表进行批量分类验证。