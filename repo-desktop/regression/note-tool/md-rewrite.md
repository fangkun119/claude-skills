# md-rewrite Verification Spec

## 测试环境前提

- Claude Code 已安装 md-rewrite skill
- Python ≥3.12 已安装（用于运行验证脚本）
- 工作目录可写
- 测试使用 Markdown 格式文件

---

## Phase 1: 工作环境准备

## TC-MR-01: Phase 1 — 创建工作目录和初始化文件

**前置条件**：
- 源文件 `test_source.md` 存在，内容为测试 Markdown
- 工作目录可写

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/setup_workspace.py "./test_source.md"
```

**预期输出**：
- 返回 JSON 格式的路径信息
- 包含 `source_file_path`、`workspace_directory`、`rewritten_file_path`、`backup_file_path`
- 退出码为 0

**验证**：
```bash
# 验证工作目录创建
test -d "./test_source/workspace/test_source/"

# 验证改写文件创建
test -f "./test_source_rewritten.md"

# 验证备份文件创建
test -f "./test_source_backup.md"

# 验证文件内容一致
diff "./test_source.md" "./test_source_rewritten.md"
diff "./test_source.md" "./test_source_backup.md"
```

---

## TC-MR-02: Phase 1 — 源文件不存在时错误处理

**前置条件**：工作目录下没有 `nonexistent.md`。

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/setup_workspace.py "./nonexistent.md"
```

**预期输出**：
- stderr 包含错误信息
- 退出码为非零值
- 不创建任何目录或文件

---

## TC-MR-03: Phase 1 — 工作目录已存在时复用

**前置条件**：
- 源文件 `test_source.md` 存在
- 工作目录 `test_source/workspace/test_source/` 已存在

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/setup_workspace.py "./test_source.md"
```

**预期输出**：
- 返回正常的路径信息
- 工作目录被复用，不报错
- 改写文件和备份文件被重新创建（覆盖）

---

## Phase 2: 需求澄清

## TC-MR-04: Phase 2 — 跳过需求澄清（已提供需求文件）

**前置条件**：
- 源文件存在
- 需求文件 `requirements.md` 已存在
- 工作区已创建

**执行**：
通过 skill 调用，传入 `requirements_file_path` 参数。

**预期**：
- 跳过 6 轮 AskUserQuestion 交互
- 直接复制 `requirements.md` 到 `workspace/test_source/requirements.md`
- Phase 2 快速完成

**验证**：
```bash
diff "requirements.md" "./test_source/workspace/test_source/requirements.md"
```

---

## TC-MR-05: Phase 2 — 执行完整需求澄清（未提供需求文件）

**前置条件**：
- 源文件存在
- 未提供 `requirements_file_path`
- 工作区已创建

**执行**：
通过 skill 调用，不传入 `requirements_file_path` 参数。

**预期**：
- 执行 6 轮 AskUserQuestion 交互
- 每轮提问包含合理的备选答案
- 最终生成 `workspace/test_source/requirements.md`
- requirements.md 包含 JSON 格式的需求信息

**验证点**：
- requirements.md 包含所有 6 个需求维度：
  - `document_purposes`
  - `audience_and_needs`
  - `rewriter_personas`
  - `writing_style`
  - `hard_constraints`
  - `additional_clarifications`
- 每个维度包含 `clarification_question` 和 `answers`

---

## TC-MR-06: Phase 2 — 测试模式跳过交互

**前置条件**：
- 源文件存在
- 未提供 `requirements_file_path`
- 设置 `test_mode=true`

**执行**：
通过 skill 调用，传入 `test_mode=true`。

**预期**：
- 跳过所有 AskUserQuestion 交互
- 使用预设的默认需求
- 生成 `workspace/test_source/requirements.md`
- requirements.md 包含测试模式的预设需求

**验证点**：
- requirements.md 中的 `document_purposes.answers` 包含 `["测试验证", "演示 Skill 功能"]`
- requirements.md 中的 `rewriter_personas.answers` 包含 `["测试助手，严格按照规格执行"]`

---

## Phase 3: 文档改写

## TC-MR-07: Phase 3 — Option A 执行（保持原文章节顺序）

**前置条件**：
- 源文件为包含多章节的演讲转录稿
- 需求文件已生成
- 用户在 AskUserQuestion 中选择"是"（保持原文章节顺序）

**执行**：
通过 skill 调用，进入 Phase 3，用户选择保持原顺序。

**预期**：
- 执行章拆分（Operation 1）
- 逆序逐一改写（Operation 2）
- 每章生成独立的规格文件（`spec_chapter_N.md`）
- 最终生成改写文件

**验证点**：
- 工作区包含 `plan_chapters.md`
- 工作区包含 `spec_chapter_1.md` 到 `spec_chapter_N.md`
- 改写文件包含所有章的内容
- 改写文件去除了口语噪音
- 改写文件使用正式书面语

---

## TC-MR-08: Phase 3 — Option B 执行（重排章节顺序）

**前置条件**：
- 源文件为包含多章节的演讲转录稿
- 需求文件已生成
- 用户在 AskUserQuestion 中选择"否"（重排章节顺序）

**执行**：
通过 skill 调用，进入 Phase 3，用户选择重排顺序。

**预期**：
- 执行改写结果规格分析（Operation 1）
- 执行任务拆分与计划制定（Operation 2）
- 执行计划执行（Operation 3）
- 生成 `spec.md` 和 `plan.md`
- 最终生成改写文件

**验证点**：
- 工作区包含 `spec.md`
- 工作区包含 `plan.md`
- `plan.md` 包含详细的执行计划和步骤
- 改写文件按照新的章节结构组织

---

## TC-MR-09: Phase 3 — 章拆分生成合理的章节划分

**前置条件**：源文件包含 5 个章节的演讲内容。

**执行**：
运行 Operation 1（章拆分）。

**预期输出**：
- 生成 `plan_chapters.md`
- 包含合理的章节划分
- 每章有明确的标题、起始行号、结束行号

**验证点**：
- `plan_chapters.md` 包含章节总数
- 每章有清晰的主题边界
- 章节划分遵循主讲人边界或主题完整性原则

---

## TC-MR-10: Phase 3 — 逆序逐一改写遵守并发控制

**前置条件**：
- 文档包含 5 章
- 章拆分已完成

**执行**：
运行 Operation 2（逆序逐一改写）。

**预期**：
- 按逆序执行：第5章 → 第4章 → ... → 第1章
- 同时最多 2 个 Sub Agent 在执行
- 每章经历 Step 1（产出规格）和 Step 2（执行改写）

**验证点**：
- 每章生成对应的 `spec_chapter_N.md`
- 所有章节最终都被改写
- 改写文件内容完整

---

## TC-MR-11: Phase 3 — 图片预处理添加注释

**前置条件**：
- 源文件包含 Markdown 图片引用
- 图片格式为 Wiki-link、标准 Markdown 或 HTML

**执行**：
运行图片预处理步骤。

**预期**：
- 在每张图片下方添加 HTML 注释
- 注释包含图片路径、用途、内容描述
- 按逆序处理（从下到上）

**验证点**：
- 改写文件中的每个图片引用下方都有注释
- 注释格式正确：
  ```html
  <!-- 
  图片内容说明
  路径：{图片文件路径}
  用途：{推测出来的图片用途}
  内容：{提炼出的图片内容说明}
  -->
  ```

---

## 四级标题体系

## TC-MR-12: 四级标题验证 — 完全符合规范

**前置条件**：
- 改写文件已完成
- 使用标准的四级标题体系

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/validate_titles.py "./test_source_rewritten.md"
```

**预期输出**：
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

**验证点**：
- `valid` 为 `true`
- `errors` 数组为空
- 所有标题符合四级标题体系规范

---

## TC-MR-13: 四级标题验证 — 缺少 Level 1 标题

**前置条件**：改写文件缺少文档总标题。

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/validate_titles.py "./test_source_rewritten.md"
```

**预期输出**：
```json
{
  "valid": false,
  "errors": [
    "第 X 行: Level 2 标题没有父级 Level 1 标题"
  ],
  "warnings": []
}
```

---

## TC-MR-14: 四级标题验证 — 标题编号错误

**前置条件**：改写文件的标题编号不符合递增规则。

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/validate_titles.py "./test_source_rewritten.md"
```

**预期输出**：
```json
{
  "valid": false,
  "errors": [
    "第 X 行: Level 2 标题编号错误，期望 Y，实际 Z"
  ],
  "warnings": []
}
```

---

## TC-MR-15: 四级标题验证 — 父子关系错误

**前置条件**：改写文件的子级标题父级编号不匹配。

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/validate_titles.py "./test_source_rewritten.md"
```

**预期输出**：
```json
{
  "valid": false,
  "errors": [
    "第 X 行: Level 2 标题父级编号错误，期望 Y，实际 Z"
  ],
  "warnings": []
}
```

---

## TC-MR-16: 四级标题验证 — 超出四级

**前置条件**：改写文件包含 Level 5+ 标题（`######`）。

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/validate_titles.py "./test_source_rewritten.md"
```

**预期输出**：
```json
{
  "valid": false,
  "errors": [
    "第 X 行: 检测到 Level 5 标题，超出四级标题体系"
  ],
  "warnings": []
}
```

---

## System Rules 验证

## TC-MR-17: System Rule — 源文件只读（未被修改）

**前置条件**：
- 源文件 `test_source.md` 存在
- 执行完整的改写流程

**执行**：
完整执行 Phase 1-3。

**验证**：
```bash
# 源文件内容未被修改
diff "./test_source.md" "./test_source_backup.md"

# 源文件的修改时间未变化
SOURCE_MTIME=$(stat -f "%m" "./test_source.md" 2>/dev/null || stat -c "%Y" "./test_source.md" 2>/dev/null)
# 验证 SOURCE_MTIME 与执行前相同
```

---

## TC-MR-18: System Rule — 工作区目录隔离

**前置条件**：工作目录可写。

**执行**：
完整执行改写流程。

**验证点**：
- 所有中间产物（`requirements.md`、`plan_chapters.md`、`spec_chapter_N.md`、`spec.md`、`plan.md`）都在 `workspace/test_source/` 目录下
- 源文件同目录下只有改写文件和备份文件
- 没有其他临时文件污染用户文件系统

---

## TC-MR-19: System Rule — 改写文件和备份文件位置正确

**前置条件**：
- 源文件为 `/path/to/test_source.md`

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/setup_workspace.py "/path/to/test_source.md"
```

**验证点**：
- 改写文件：`/path/to/test_source_rewritten.md`
- 备份文件：`/path/to/test_source_backup.md`
- 工作区目录：`/path/to/workspace/test_source/`
- 路径推导符合规范

---

## 内容质量验证

## TC-MR-20: 内容质量 — 去除口语噪音

**前置条件**：
- 源文件为演讲转录稿，包含大量口语噪音（"啊啊"、"呃"、"呢"、"这个"、"大家知道"）

**执行**：
完整执行改写流程。

**验证点**：
- 改写文件不包含"啊啊"、"呃"、"呢"等语气词
- 改写文件不包含"这个"、"那个"等口头禅
- 改写文件不包含"大家好"、"欢迎来到"、"我是"等演讲串场词
- 改写文件使用正式书面语

---

## TC-MR-21: 内容质量 — 保留关键数据

**前置条件**：
- 源文件包含市场数据、时间节点、专业术语

**执行**：
完整执行改写流程。

**验证点**：
- 所有数字数据保留（如"超过17万就业"、"24倍估值"）
- 所有时间节点保留（如"6月18日"、"7-8月业绩期"）
- 所有专业术语保留（如"流动性紧缩"、"拥挤度"、"赔率胜率"）
- 关键逻辑和观点完整保留

---

## TC-MR-22: 内容质量 — 逻辑结构清晰

**前置条件**：
- 源文件为多章节演讲稿

**执行**：
完整执行改写流程。

**验证点**：
- 改写文件有清晰的章节划分
- 每章有明确的标题
- 段落之间的逻辑关系清晰
- 使用逻辑连接词（"因此"、"然而"、"总之"等）

---

## TC-MR-23: 内容质量 — 专业术语准确性

**前置条件**：
- 源文件包含金融、经济、技术等专业术语

**执行**：
完整执行改写流程。

**验证点**：
- 专业术语不被修改或简化
- 专业术语的上下文保持准确
- 缩写词在首次出现时有完整解释（如源文件中有）

---

## 边界情况和错误处理

## TC-MR-24: 错误处理 — 源文件为空

**前置条件**：
- 源文件 `empty.md` 存在但内容为空

**执行**：
```bash
python note-tool/skills/md-rewrite/scripts/setup_workspace.py "./empty.md"
```

**预期输出**：
- 脚本能够处理空文件
- 生成空的改写文件和备份文件
- 不抛出异常

---

## TC-MR-25: 错误处理 — 源文件包含非 UTF-8 编码

**前置条件**：
- 源文件包含非 UTF-8 字符（如 GBK 编码的中文）

**执行**：
尝试读取源文件。

**预期输出**：
- 脚本能检测编码问题
- 输出清晰的错误信息
- 不生成损坏的改写文件

---

## TC-MR-26: 边界情况 — 单章节文档

**前置条件**：
- 源文件只包含一个章节

**执行**：
完整执行改写流程（Option A）。

**验证点**：
- 只生成一个规格文件（`spec_chapter_1.md`）
- 改写文件包含该章的内容
- 流程正常完成，无错误

---

## TC-MR-27: 边界情况 — 超长文档（1000+ 行）

**前置条件**：
- 源文件包含超过 1000 行内容

**执行**：
完整执行改写流程。

**验证点**：
- 所有章节都被正确改写
- 不会因为内容过长而中断
- 改写文件内容完整

---

## TC-MR-28: 边界情况 — 文档包含代码块

**前置条件**：
- 源文件包含 Markdown 代码块（```bash ... ```）

**执行**：
完整执行改写流程。

**验证点**：
- 代码块内容完整保留
- 代码块的语法高亮标记保留
- 代码块内的缩进保留

---

## TC-MR-29: 边界情况 — 文档包含表格

**前置条件**：
- 源文件包含 Markdown 表格

**执行**：
完整执行改写流程。

**验证点**：
- 表格结构保留
- 表格内容不被修改
- 表格的格式正确

---

## TC-MR-30: 边界情况 — 文档包含链接

**前置条件**：
- 源文件包含 Markdown 链接和 Wiki-link

**执行**：
完整执行改写流程。

**验证点**：
- 链接目标地址保留
- 链接文本保留
- Wiki-link 格式（`[[...]]`）保留

---

## 集成测试

## TC-MR-31: 集成测试 — 完整流程（提供需求文件）

**前置条件**：
- 源文件为演讲转录稿
- 需求文件已提供
- 用户选择 Option A

**执行**：
完整执行 Phase 1-3。

**验证点**：
- Phase 1：工作目录、改写文件、备份文件创建成功
- Phase 2：需求文件被复制到工作区
- Phase 3：章拆分、逆序逐一改写完成
- 输出：改写文件符合质量标准
- 四级标题验证通过
- System Rules 被遵守

---

## TC-MR-32: 集成测试 — 完整流程（执行需求澄清）

**前置条件**：
- 源文件为演讲转录稿
- 未提供需求文件
- 测试模式开启

**执行**：
完整执行 Phase 1-3。

**验证点**：
- Phase 1：工作目录创建成功
- Phase 2：6 轮交互被跳过，使用预设需求
- Phase 3：改写流程正常执行
- 输出：改写文件符合质量标准

---

## TC-MR-33: 集成测试 — 多次改写同一文档

**前置条件**：
- 源文件存在
- 已执行过一次改写

**执行**：
再次执行完整改写流程。

**验证点**：
- 第二次改写正常执行
- 工作区被复用或重新创建
- 改写文件和备份文件被覆盖
- 不产生冲突或错误

---

## TC-MR-34: 集成测试 — 并发改写多个文档

**前置条件**：
- 工作目录下有多个源文件：`doc1.md`、`doc2.md`、`doc3.md`

**执行**：
并行执行多个改写任务。

**验证点**：
- 每个文档独立完成改写
- 每个文档有独立的工作区（`workspace/doc1/`、`workspace/doc2/`、`workspace/doc3/`）
- 每个文档生成独立的改写文件（`doc1_rewritten.md`、`doc2_rewritten.md`、`doc3_rewritten.md`）
- 不产生文件冲突或目录冲突

---

## 性能测试

## TC-MR-35: 性能测试 — 中等文档（500 行）处理时间

**前置条件**：
- 源文件包含 500 行内容

**执行**：
```bash
time /note-tool:md-rewrite "source.md" --requirements "requirements.md"
```

**预期输出**：
- 总处理时间在合理范围内（< 5 分钟）
- 不会出现超时或卡死

---

## TC-MR-36: 性能测试 — 大型文档（2000+ 行）处理时间

**前置条件**：
- 源文件包含 2000+ 行内容

**执行**：
```bash
time /note-tool:md-rewrite "large_source.md" --requirements "requirements.md"
```

**预期输出**：
- 总处理时间在可接受范围内（< 15 分钟）
- 不会出现内存溢出或崩溃

---

## 回归测试清单

### 必须通过的测试用例（最小集）

每次 skill 更新后，以下测试用例必须通过：

- TC-MR-01: Phase 1 工作环境准备
- TC-MR-04: Phase 2 跳过需求澄清
- TC-MR-07: Phase 3 Option A 执行
- TC-MR-12: 四级标题验证
- TC-MR-17: System Rule 源文件只读
- TC-MR-20: 内容质量去除口语噪音
- TC-MR-31: 集成测试完整流程

### 推荐通过的测试用例（标准集）

除了最小集外，建议以下测试用例也通过：

- TC-MR-02 到 TC-MR-03: Phase 1 边界情况
- TC-MR-05 到 TC-MR-06: Phase 2 变体
- TC-MR-08: Phase 3 Option B
- TC-MR-13 到 TC-MR-16: 四级标题验证错误情况
- TC-MR-18 到 TC-MR-19: System Rules 工作区隔离
- TC-MR-21 到 TC-MR-23: 内容质量保留
- TC-MR-26 到 TC-MR-29: 边界情况

### 完整测试集（发布前）

发布新版本前，建议运行所有测试用例（TC-MR-01 到 TC-MR-36）。

---

## 测试数据准备

### 标准测试源文件

创建以下测试文件用于回归测试：

1. **simple_speech.md** - 简单演讲稿（100 行）
   - 包含 3 个章节
   - 包含口语噪音
   - 包含市场数据

2. **complex_speech.md** - 复杂演讲稿（500 行）
   - 包含 5 个章节
   - 包含大量口语噪音
   - 包含专业术语和数据
   - 包含代码示例

3. **with_images.md** - 包含图片的文档
   - 包含 Wiki-link 图片
   - 包含标准 Markdown 图片
   - 包含 HTML 图片

4. **empty.md** - 空文档
5. **single_chapter.md** - 单章节文档
6. **very_long.md** - 超长文档（2000+ 行）

### 标准需求文件

创建以下需求文件：

1. **standard_requirements.md** - 标准改写需求
2. **technical_requirements.md** - 技术文档改写需求
3. **report_requirements.md** - 报告改写需求

---

## 测试执行自动化

### 批量测试脚本

创建 `run_regression_tests.sh` 脚本：

```bash
#!/bin/bash

# 设置
SOURCE_DIR="./test_sources"
REQUIREMENTS_DIR="./test_requirements"
OUTPUT_DIR="./test_outputs"

# 清理
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# 测试计数
TOTAL=0
PASSED=0
FAILED=0

# 运行单个测试
run_test() {
    local test_name=$1
    local test_func=$2
    
    TOTAL=$((TOTAL + 1))
    echo "Running: $test_name"
    
    if $test_func; then
        echo "✓ PASSED: $test_name"
        PASSED=$((PASSED + 1))
    else
        echo "✗ FAILED: $test_name"
        FAILED=$((FAILED + 1))
    fi
}

# 定义测试函数
test_tc_mr_01() {
    # TC-MR-01 测试实现
    # ...
    return 0  # 0=成功, 1=失败
}

# 运行所有测试
run_test "TC-MR-01: Phase 1 工作环境准备" test_tc_mr_01
run_test "TC-MR-02: Phase 1 源文件不存在" test_tc_mr_02
# ...

# 输出结果
echo ""
echo "================================"
echo "Total: $TOTAL"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "================================"

exit $FAILED
```

---

## 测试报告模板

### 测试执行报告

**日期**：YYYY-MM-DD
**版本**：md-rewrite v{version}
**测试环境**：Claude Code {version}, Python {version}
**测试人员**：{name}

#### 测试结果摘要

| 类别 | 总数 | 通过 | 失败 | 通过率 |
|------|------|------|------|--------|
| Phase 1 | 3 | 3 | 0 | 100% |
| Phase 2 | 3 | 3 | 0 | 100% |
| Phase 3 | 5 | 4 | 1 | 80% |
| 四级标题 | 5 | 5 | 0 | 100% |
| System Rules | 3 | 3 | 0 | 100% |
| 内容质量 | 4 | 4 | 0 | 100% |
| 边界情况 | 6 | 5 | 1 | 83% |
| 集成测试 | 4 | 4 | 0 | 100% |
| 性能测试 | 2 | 2 | 0 | 100% |
| **总计** | **35** | **33** | **2** | **94%** |

#### 失败用例详情

1. **TC-MR-08: Phase 3 Option B 执行**
   - 失败原因：...
   - 错误日志：...
   - 修复建议：...

#### 结论

[通过/不通过] 本次回归测试。建议[发布/不发布]当前版本。

---

## 维护说明

### 添加新测试用例

1. 选择合适的测试类别（Phase 1/2/3、四级标题、System Rules 等）
2. 分配测试编号（TC-MR-{N+1}）
3. 编写测试前置条件、执行步骤、预期输出、验证点
4. 更新测试数据准备部分
5. 更新集成测试清单

### 更新现有测试用例

1. 标注修改日期和修改人
2. 说明修改原因
3. 保持测试用例的向后兼容性

### 删除测试用例

1. 说明删除原因（功能废弃、重复等）
2. 在文档中标注"已废弃"
3. 保留历史记录
