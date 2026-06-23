---
name: md-img-to-html
description: |
  将 Markdown 文档中的所有图片格式转换为 HTML <img> 标签格式。
  支持标准 Markdown 格式 ![alt](path) 和 Obsidian wikilink 格式 ![[path]]，以及它们的宽度变体。
  当用户提到"图片转HTML"、"Markdown图片转HTML"、"img标签"、"转换图片格式"等需求时触发。
  也处理已有 HTML <img> 标签的 alt 属性检查和填充。
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

# Markdown 图片转 HTML Skill

将 Markdown 文档中的所有图片格式转换为 HTML `<img>` 标签格式，同时确保所有图片都有有效的 alt 属性。

## 支持的输入格式

### 1. 标准 Markdown 格式
- `![alt text](image-path)`
- `![alt text|600px](image-path)`

### 2. Obsidian Wikilink 格式
- `![[image-path]]`
- `![[image-path|600px]]`

## 转换规则

### 输出格式
所有图片都转换为以下 HTML 格式：
```html
<img src="图片源路径" style="display: block; width: [宽度]px;" alt="替换文字">
```

### 1. 图片源路径（src）
- **严格原则**：图片源路径必须完全来自 Markdown 输入，绝对不可以自行更改或修改
- 路径的正确性是输入文件编写者的责任，不是这个 Skill 的职责
- 这个 Skill 只负责格式转换，不了解具体应用场景，所以不应做出超出职责的判断

### 2. 替换文字（alt）
- **有替换文字**：使用 Markdown 中的替换文字
- **无替换文字**：使用默认值 `"替换文字"`，不可以留空

**为什么必须有 alt 属性**：
- 一些工作流强制要求 HTML 格式的图片必须有 alt 属性且不能为空
- 如果不使用默认值填充，会导致工作流中断
- 这是为了确保输出的 HTML 兼容性

### 3. 宽度（width）
#### 当 Markdown 没有提供宽度时
格式：`![[path]]` 或 `![alt](path)`

**用户指定了默认宽度**：使用用户指定的默认值
```html
<img src="path" style="display: block; width: 100%;" alt="替换文字">
```

**用户没有指定默认宽度**：使用 800px
```html
<img src="path" style="display: block; width: 800px;" alt="替换文字">
```

#### 当 Markdown 提供了宽度时
格式：`![[path|600px]]` 或 `![alt|600px](path)`

保留原宽度不变：
```html
<img src="path" style="display: block; width: 600px;" alt="替换文字">
```

## 转换过程

按以下顺序执行转换：

### 步骤 1：梳理所有图片
扫描文件，识别所有需要转换的图片，记录：
- 图片的 Markdown 标签
- 替换文字（如有）
- 宽度（如有）
- 在文件中的位置（行号和列号）

### 步骤 2：制定转换计划
- 按照图片在文件中出现的位置，**从下到上逆序**转换
- **为什么逆序**：先修改下面的图片不会改变上面图片的位置，确保计划可行
- 列出清晰的转换计划，告知用户将要进行哪些修改

### 步骤 3：执行转换
按照计划逐个转换图片标签

### 步骤 4：验证 alt 属性
- 检查所有 HTML `<img>` 标签的 alt 属性
- 如果 alt 属性不存在或值为空，使用默认值 `"替换文字"` 填充
- 这包括新转换的图片和文件中已有的 `<img>` 标签

## 错误处理

### 无法识别的格式
- **策略**：跳过无法识别的图片语法，继续处理其他图片
- **记录**：在完成后向用户报告哪些格式无法识别
- **保持原样**：无法识别的格式保持不变

**示例**：
- 损坏的 Markdown 语法：`![](broken syntax`
- 不支持的格式：某些自定义的图片语法

## 已有 HTML <img> 标签的处理

对于文件中已经存在的 HTML `<img>` 标签：
- **只检查和填充 alt 属性**：确保 alt 属性存在且不为空
- **不修改其他部分**：src、style 等属性保持不变
- **遵循相同规则**：如果 alt 缺失或为空，使用默认值 `"替换文字"`

## 工作流程示例

**输入文件内容**：
```markdown
# 我的文档

这是一张图片：
![[example.png]]

这是带宽度的图片：
![[photo.jpg|600px]]

这是标准 Markdown：
![图表](chart.png)
![图示|400px](diagram.png)
```

**转换过程**：
1. 识别 4 个图片需要转换
2. 制定从下到上的转换计划
3. 逐个转换
4. 验证所有 alt 属性

**输出文件内容**：
```markdown
# 我的文档

这是一张图片：
<img src="example.png" style="display: block; width: 800px;" alt="替换文字">

这是带宽带度的图片：
<img src="photo.jpg" style="display: block; width: 600px;" alt="替换文字">

这是标准 Markdown：
<img src="chart.png" style="display: block; width: 800px;" alt="图表">

这是带宽度标准 Markdown：
<img src="diagram.png" style="display: block; width: 400px;" alt="图示">
```

## 用户指定默认宽度

在调用此 Skill 时，用户可以指定默认宽度：

**示例用户提示**：
```
使用默认宽度 100% 转换这个文件中的图片
```

**结果**：所有没有指定宽度的图片都将使用 `width: 100%;`

## 范围边界

### ✅ 会做的
- 转换标准 Markdown 图片格式
- 转换 Obsidian wikilink 图片格式
- 检查和填充所有 `<img>` 标签的 alt 属性
- 保留原图路径不做修改
- 从下到上逆序转换以确保位置准确性
- 报告无法识别的格式

### ❌ 不会做的
- 验证图片路径是否正确
- 修改图片路径
- 处理非图片的 wikilink
- 修改 HTML `<img>` 标签的其他属性（除 alt 外）
- 处理 CSS 背景图片或其他非 `<img>` 标签的图片

## 注意事项

1. **路径严格性**：图片路径必须从原文严格拷贝，不做任何修改
2. **Alt 必填**：所有图片必须有 alt 属性，使用默认值填充缺失的 alt
3. **逆序转换**：从下到上转换以避免位置偏移
4. **宽度优先级**：Markdown 中指定的宽度 > 用户指定的默认宽度 > 800px
5. **兼容性**：确保输出的 HTML 符合 Web 标准

## 示例对话

**用户**: 把这个 Markdown 文件中的所有图片转换为 HTML 格式

**Skill 执行**:
1. 读取文件
2. 识别所有图片格式
3. 制定从下到上的转换计划
4. 执行转换
5. 验证 alt 属性
6. 报告完成情况和任何问题

---

**用户**: 使用 100% 作为默认宽度转换图片

**Skill 执行**:
1. 识别用户指定的默认宽度：100%
2. 执行转换时，所有没有指定宽度的图片使用 `width: 100%;`
3. Markdown 中指定了宽度的图片保持原宽度

---

**用户**: 这个文档的图片都没有 alt 文字，帮我转换一下

**Skill 执行**:
1. 识别所有图片都没有 alt 文字
2. 转换时使用默认值 `"替换文字"` 填充 alt 属性
3. 确保所有 `<img>` 标签都有有效的 alt 属性
