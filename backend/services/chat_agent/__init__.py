"""
主对话 Agent 模块。接收用户消息，调用 LLM 进行工具编排，流式返回结果。
## 简介

AI 对话执行模块。接收用户消息 → 解析命令 → 调用 LLM 进行工具编排 → 流式返回结果。

## 数据流（一次用户对话轮次）

```
HTTP 请求
  → chat_service.stream_topic_message()        # 薄封装入口
  → ChatAgent.run()                             # 总编排，异步生成器
      1. parse_command_match()                   #  解析用户输入的 /命令
      2. create_checkpoint()                     #  git 快照，用于事后 diff
      3. _setup_turn()                           #  构建 TopicContextManager + ToolCallLoop
      4. resolve_tools()                          #  合并基础工具 + 命令触发工具
      5. ToolCallLoop.run()                      #  LLM 流式调用 + 工具执行循环(≤15轮)
      6. collect_modified_files()                #  git diff 检测本轮文件变更
      7. append_action_messages()                #  追加 file_change / pattern_score_change
      8. TopicContextManager.commit_turn()       #  持久化新消息
  → SSE 事件流 → 前端
```

## 目录结构

```
chat_agent/
├── chat_agent.py          # [组装入口] 总编排器 ChatAgent —— 加新命令/工具从这里开始
├── chat_service.py        # [功能入口] HTTP 入口，薄封装
├── command/               # 命令系统：用户通过 /命令 手动触发额外能力
│   ├── registry.py        #   CommandDefinition / CommandHub / CommandRegistry
│   └── parser.py          #   解析用户输入中的 /命令
├── context/               # 对话上下文管理（持久化 + 临时）
│   └── topic_context_manager.py
├── loop/                  # LLM 调用 + 工具执行循环
│   ├── events.py          #   流式事件类型定义
│   └── tool_call_loop.py  #   ToolCallLoop：核心循环逻辑
├── post_turn/             # 每轮对话结束后的后处理
│   └── finalize.py        #   git diff + action message
├── prompt/                # 系统提示词 + 消息构建（"模型看到了什么"的完整答案）
│   ├── system_prompt.py   #   系统提示词模板
│   └── build_messages.py  #   组装完整消息列表（system + history + user）
├── skills/                # 技能定义（SKILL.md）
├── stream/                # SSE 事件编码
│   ├── sse.py             #   SSE 格式化
│   └── event_codec.py     #   LoopEvent → SSE 转换
├── tools/                 # 工具定义（list_pattern / append_log / get_time）
└── workspace/             # Git 工作区管理（checkpoint / diff / revert）
```

## 核心设计模式

Hub / Registry / Command 三层：
- Hub = 全局定义中心（存所有 tool/skill/command 的定义）
- Registry = 某个 agent 实例的白名单（按名字引用 hub 中的定义）
- Command = 用户手动触发的入口（通过 /命令）。命令触发后，系统将对应的 skill/tool 临时注入本轮对话。Agent 默认并不知道命令相关 tools/skills 的存在——主动权在用户。
- tools系统相比其它Agent多了ToolHub，就是因为要考虑到Command，有一部分命令是Agent一开始不知道的
## 修改指南

- 加新命令 → `chat_agent.py` 的 `_COMMANDS` 字典 + `command/` 子包
- 加新工具 → `tools/` 子包 + `chat_agent.py` 的 `_init_components()`
- 改系统提示词 → `prompt/system_prompt.py`
- 改消息格式 → `prompt/build_messages.py`
- 改 SSE 事件格式 → `stream/event_codec.py`
- 改工具执行逻辑 → `loop/tool_call_loop.py`

## 依赖

- 依赖 `library/agent_atoms/` — BaseModel、ToolHub、SkillHub、BaseContextManager 等基础组件
- 依赖 `backend/services/topic/` — topic_service 话题持久化
- 依赖 `backend/services/research/` — make_research_tool 研究工具
- 被 `backend/api/` 路由层调用，对外暴露 SSE 流式接口
- 工具执行需要 `code.config` 中的 `ALLOWED_ROOT`（工作区路径）

"""
