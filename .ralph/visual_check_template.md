# Visual Check Report — iter \<N\>

> 这是 ralph loop multimodal 自检报告模板。
> 何时写：本轮改动了 `templates/` / `src/web/` / 任何影响 dashboard 渲染的代码 → **必须**填这份。
> 怎么写：跑 `bash scripts/visual_check.sh` → 用 Read 工具读 `.ralph/visual_check_iter<N>/dashboard.png` → 自己看图判断 → 填本报告。

## 1. 改动摘要

- 改了什么文件：
- 期望 UI 看到的变化：
- 不期望出现的回归：

## 2. 自检命令

```bash
bash scripts/visual_check.sh
# 或者 dashboard 已起：
bash scripts/visual_check.sh --no-flask
```

artifacts 路径：`.ralph/visual_check_iter<N>/`
- `dashboard.png` — 1440x900 截图
- `dom.yaml` — 结构化 DOM 快照
- `console.txt` — JS console 日志
- `title.txt` — 页面 title
- `flask.log` — Flask stderr/stdout

## 3. 看图判断（agent 用 Read 看 dashboard.png 后填）

### 3.1 必查项（PASS / FAIL / N/A）

- [ ] 页面正常渲染（非 5xx 错误页 / 非空白）
- [ ] 综合温度计 gauge 可见（顶部大数字 + 颜色环）
- [ ] 5 个维度分组（波动率/曲线/信用/流动性/跨市场）都在
- [ ] 每条指标显示：名 + 当前值 + 颜色 + 更新时间
- [ ] LLM 简报段（如本轮启用）渲染正常
- [ ] chatbot 浮窗按钮可见

### 3.2 本轮新增/改动专项

- [ ] <自己写：本轮期望出现的新元素是否在图中可见>
- [ ] <自己写：颜色/数值/排版是否符合预期>

### 3.3 回归检查

- [ ] 现有指标排版没乱
- [ ] 没有 console 报红（看 console.txt）

## 4. 看图发现的问题

- 问题 1：
- 问题 2：

## 5. 结论

- [ ] PASS — UI 符合预期，可以提交
- [ ] FAIL — 有问题，列下面 TODO 后回到代码改
- [ ] PARTIAL — 主体可用但有非阻塞瑕疵（写入 PLAN.md 后续修）

## 6. TODO（如果 FAIL）

-
