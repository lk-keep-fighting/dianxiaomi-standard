# AI内容生成结构化数据使用指南

## 🎯 功能概述

[`new_title_and_key_features`](src/ai_category_validator.py#L220) 方法现在返回结构化的字典数据，而不是原始的文本响应，让你能够更方便地访问AI生成的各个内容部分。

## 📋 返回数据结构

```python
{
    'title': '优化后的产品标题',
    'bullet_points': '五点描述（用换行符分隔）',
    'description': '详细产品描述'
}
```

## 🔧 使用方法

### 1. 基本调用

```python
from src.ai_category_validator import AICategoryValidator

validator = AICategoryValidator(
    api_base_url="https://api.hunyuan.cloud.tencent.com/v1",
    api_key="your-api-key",
    model_name="hunyuan-turbos-latest"
)

# 调用AI生成内容
result = validator.new_title_and_key_features(
    title="原始产品标题",
    key_features=["特征1", "特征2", "特征3"],
    remove_words="需要移除的违规词",
    category="产品分类"
)
```

### 2. 访问结构化数据

```python
if result:
    # 获取优化后的标题
    optimized_title = result['title']
    
    # 获取五点描述（字符串形式）
    bullet_points_text = result['bullet_points']
    
    # 将五点描述转换为列表
    bullet_list = bullet_points_text.split('\n')
    clean_bullets = [bullet.strip() for bullet in bullet_list if bullet.strip()]
    
    # 获取详细描述
    description = result['description']
    
    print(f"标题: {optimized_title}")
    print(f"五点描述数量: {len(clean_bullets)}")
    print(f"描述长度: {len(description)} 字符")
```

### 3. 在自动化脚本中使用

```python
# 生成AI内容
ai_content = validator.new_title_and_key_features(
    title=product_data.title,
    key_features=product_data.features,
    remove_words=forbidden_words,
    category=product_category
)

if ai_content:
    # 填充表单标题
    edit_frame.locator("#title-input").fill(ai_content['title'])
    
    # 填充五点描述
    bullets = ai_content['bullet_points'].split('\n')
    for i, bullet in enumerate(bullets, 1):
        if bullet.strip():
            clean_bullet = bullet.strip().lstrip('- ')
            edit_frame.locator(f"#bullet-point-{i}").fill(clean_bullet)
    
    # 填充详细描述
    edit_frame.locator("#description-textarea").fill(ai_content['description'])
```

## 🛠️ 数据处理技巧

### 清理五点描述格式

```python
def clean_bullet_points(bullet_text):
    """清理并格式化五点描述"""
    bullets = bullet_text.split('\n')
    cleaned = []
    
    for bullet in bullets:
        bullet = bullet.strip()
        if bullet:
            # 移除开头的"-"或"•"符号
            bullet = bullet.lstrip('- •').strip()
            # 确保每个要点都有统一的格式
            cleaned.append(f"- {bullet}")
    
    return cleaned

# 使用示例
if ai_result:
    bullet_points = clean_bullet_points(ai_result['bullet_points'])
    for i, bullet in enumerate(bullet_points, 1):
        print(f"要点{i}: {bullet}")
```

### 验证数据完整性

```python
def validate_ai_content(result):
    """验证AI生成内容的完整性"""
    if not result:
        return False, "AI生成失败"
    
    title = result.get('title', '').strip()
    bullet_points = result.get('bullet_points', '').strip()
    description = result.get('description', '').strip()
    
    issues = []
    
    if not title:
        issues.append("标题为空")
    elif len(title) < 50:
        issues.append("标题过短")
    elif len(title) > 250:
        issues.append("标题过长")
    
    if not bullet_points:
        issues.append("五点描述为空")
    else:
        bullet_count = len([b for b in bullet_points.split('\n') if b.strip()])
        if bullet_count < 3:
            issues.append(f"五点描述不足，只有{bullet_count}个")
    
    if not description:
        issues.append("详细描述为空")
    elif len(description) < 100:
        issues.append("详细描述过短")
    
    return len(issues) == 0, issues

# 使用示例
ai_result = validator.new_title_and_key_features(...)
is_valid, issues = validate_ai_content(ai_result)

if is_valid:
    print("✅ AI内容验证通过")
else:
    print(f"⚠️ AI内容存在问题: {', '.join(issues)}")
```

## 🔄 错误处理

```python
try:
    ai_result = validator.new_title_and_key_features(
        title=product_title,
        key_features=features,
        remove_words=forbidden_words,
        category=category
    )
    
    if ai_result:
        # 处理成功的结果
        process_ai_content(ai_result)
    else:
        # AI生成失败，使用备用方案
        print("AI内容生成失败，使用原始数据")
        fallback_content = {
            'title': product_title,
            'bullet_points': '\n'.join([f"- {feature}" for feature in features]),
            'description': f"This is a {category} product with excellent features."
        }
        process_ai_content(fallback_content)
        
except Exception as e:
    print(f"AI内容生成异常: {e}")
    # 错误处理逻辑
```

## 💡 实际应用示例

在你的 `main_shuziqiuzhang_canada.py` 中：

```python
# 原来的调用方式已经更新为返回结构化数据
ai_content = ai_category_validator.new_title_and_key_features(
    title=product_data.title, 
    key_features=product_data.details.get("key features", "").split("|"), 
    remove_words=forbidden_words_str, 
    category=product_data.details.get("Category", "Musical Instruments")
)

print("AI 优化结果")
if ai_content:
    print(f"标题: {ai_content['title']}")
    print(f"五点描述: {ai_content['bullet_points']}")
    print(f"详情描述: {ai_content['description']}")
    
    # 在表单中使用这些数据
    # ... 你的表单填充代码 ...
else:
    print("AI生成失败")
```

## 🎉 优势总结

1. **结构化访问**: 不再需要手动解析文本，直接通过字典键访问
2. **类型安全**: 返回明确的字典结构，便于IDE提示和错误检查
3. **容错处理**: 内置多重解析机制，确保即使AI响应格式不完美也能提取有用信息
4. **便于调试**: 可以轻松查看和验证每个部分的内容
5. **代码简洁**: 减少了文本处理的代码量，提高可维护性

现在你可以更方便地使用AI生成的内容，并且能够确保数据的结构化和可靠性！