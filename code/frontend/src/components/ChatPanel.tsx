import { useState, useEffect, useRef, useCallback } from "react"
import type {
  ChatMessage,
  FileChangeActionData,
  ModifiedFile,
  PatternScoreActionData,
  SSEEvent,
  Topic,
  TopicSummary,
} from "../types/chat"
import type { ResearchMessage } from "./ResearchPanel"
import { sendMessage } from "../api/chat"
import {
  listTopics, getTopic, createTopic, renameTopic, deleteTopic,
  branchTopic, rollbackConversation, rollbackConversationAndFiles, rollbackFiles,
} from "../api/topics"
import TopicHeader from "./TopicHeader"
import HistoryPanel from "./HistoryPanel"
import ThinkingBlock from "./ThinkingBlock"
import MessageBubble from "./MessageBubble"
import ToolCallCard from "./ToolCallCard"
import FileChangesAction from "./FileChangesAction"
import PatternScoreAction from "./PatternScoreAction"
import BranchMenu from "./BranchMenu"

type StreamingBlock =
  | { type: "thinking"; content: string }
  | { type: "text"; content: string }
  | { type: "tool_call"; name: string; arguments: Record<string, unknown>; result?: string; status: "running" | "done" }

interface Props {
  onDiffView: (filePath: string, oldContent: string, newContent: string) => void
  onFileChanged: () => void
  onResearchUpdate: (tabId: string, topic: string, messages: ResearchMessage[], done: boolean) => void
}

export default function ChatPanel({ onDiffView, onFileChanged, onResearchUpdate }: Props) {
  const [topics, setTopics] = useState<TopicSummary[]>([])
  const [currentTopicId, setCurrentTopicId] = useState<string | null>(null)
  const [currentTopic, setCurrentTopic] = useState<Topic | null>(null)
  const [loading, setLoading] = useState(true)
  const [inputText, setInputText] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [streamingBlocks, setStreamingBlocks] = useState<StreamingBlock[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [branchMenuMsgIdx, setBranchMenuMsgIdx] = useState<number | null>(null)
  const [rollbackMenuMsgIdx, setRollbackMenuMsgIdx] = useState<number | null>(null)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatMessagesRef = useRef<HTMLDivElement>(null)
  const userScrolledRef = useRef(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const currentTopicIdRef = useRef<string | null>(null)
  currentTopicIdRef.current = currentTopicId  // keep ref in sync for SSE callbacks

  // Research state — research runs as a background task via the chat SSE stream.
  // When the user switches topics while research is active, we keep the SSE alive
  // and route completion to the original topic. researchSourceTopicIdRef tracks
  // where /research was issued so done messages land in the right place.
  const [researchTopic, setResearchTopic] = useState<string | null>(null)
  const researchMessagesRef = useRef<ResearchMessage[]>([])
  const researchTabIdRef = useRef<string | null>(null)
  const researchSourceTopicIdRef = useRef<string | null>(null)

  // streamingSourceTopicIdRef tracks which topic the current SSE stream belongs to,
  // for both research and regular chat. When the user switches topics mid-stream,
  // we suppress chat events on the wrong topic and route done messages correctly.
  const streamingSourceTopicIdRef = useRef<string | null>(null)

  // Load topics on mount
  useEffect(() => {
    (async () => {
      try {
        const list = await listTopics()
        setTopics(list)
        if (list.length > 0) {
          setCurrentTopicId(list[0].id)
        } else {
          const t = await createTopic()
          setCurrentTopicId(t.id)
          setTopics([{ id: t.id, topic_name: t.topic_name, created_at: t.created_at, message_count: 0 }])
        }
      } catch {
        try {
          const t = await createTopic()
          setCurrentTopicId(t.id)
        } catch { /* backend unavailable */ }
      } finally {
        setLoading(false)
      }
    })()
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  useEffect(() => {
    if (!currentTopicId) return
    (async () => {
      try {
        const t = await getTopic(currentTopicId)
        setCurrentTopic(t)
      } catch {
        setCurrentTopic(null)
      }
    })()
  }, [currentTopicId])

  useEffect(() => {
    if (!userScrolledRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [streamingBlocks, currentTopic?.messages.length])

  const handleScroll = useCallback(() => {
    const el = chatMessagesRef.current
    if (!el) return
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
    userScrolledRef.current = !isNearBottom
  }, [])

  const refreshTopics = async () => {
    try { setTopics(await listTopics()) } catch { /* ignore */ }
  }

  const sendText = useCallback(async (rawText: string) => {
    const text = rawText.trim()
    if (!text || !currentTopicId || streaming) return

    setInputText("")
    setStreamingBlocks([])
    userScrolledRef.current = false
    setStreaming(true)
    setRollbackMenuMsgIdx(null)

    // Add user message optimistically
    const userMsg: ChatMessage = {
      role: "user", timestamp: new Date().toISOString(), content: text,
    }
    setCurrentTopic((prev) =>
      prev ? { ...prev, messages: [...prev.messages, userMsg] } : prev,
    )

    abortRef.current?.abort()
    const abort = new AbortController()
    abortRef.current = abort
    streamingSourceTopicIdRef.current = currentTopicId

    try {
      await sendMessage(currentTopicId, text, (event: SSEEvent) => {
        // When the SSE belongs to a different topic than the one currently
        // displayed (user switched topics mid-stream), suppress chat events.
        // Research messages, done, and errors always pass through.
        const sseSrcTopic = researchSourceTopicIdRef.current || streamingSourceTopicIdRef.current
        const onOtherTopic = sseSrcTopic !== null && sseSrcTopic !== currentTopicIdRef.current
        if (onOtherTopic && event.type !== "research_message" && event.type !== "done" && event.type !== "error") {
          return
        }

        switch (event.type) {
          case "thinking_start":
            setStreamingBlocks(prev => [...prev, { type: "thinking" as const, content: "" }])
            break
          case "thinking_token":
            setStreamingBlocks(prev => {
              const last = prev[prev.length - 1]
              if (last?.type === "thinking") {
                return [...prev.slice(0, -1), { ...last, content: last.content + event.token }]
              }
              return [...prev, { type: "thinking" as const, content: event.token }]
            })
            break
          case "thinking_end":
            break
          case "text_token":
            setStreamingBlocks(prev => {
              const last = prev[prev.length - 1]
              if (last?.type === "text") {
                return [...prev.slice(0, -1), { ...last, content: last.content + event.token }]
              }
              return [...prev, { type: "text" as const, content: event.token }]
            })
            break
          case "tool_call":
            setStreamingBlocks(prev => [
              ...prev,
              { type: "tool_call" as const, name: event.name, arguments: event.arguments, status: "running" as const },
            ])
            // Capture research topic from tool call arguments
            if (event.name === "research" && typeof event.arguments.topic === "string") {
              const topic = event.arguments.topic as string
              researchTabIdRef.current = `research:${Date.now()}`
              researchMessagesRef.current = []
              researchSourceTopicIdRef.current = currentTopicId
              setResearchTopic(topic)
              onResearchUpdate(researchTabIdRef.current, topic, [], false)
            }
            break
          case "tool_result":
            setStreamingBlocks(prev => {
              // Find the last matching running tool_call by name
              const idx = prev
                .map((b, i) => (b.type === "tool_call" && b.name === event.name && b.status === "running" ? i : -1))
                .filter(i => i >= 0)
                .pop()
              if (idx === undefined) return prev
              return prev.map((b, i) =>
                i === idx ? { ...b, result: event.result, status: "done" as const } : b,
              )
            })
            break
          case "research_message": {
            const newMsg: ResearchMessage = {
              agent_name: event.agent_name,
              content: event.content,
              msg_type: event.msg_type,
              timestamp: new Date().toISOString(),
            }
            if (researchTabIdRef.current) {
              researchMessagesRef.current = [...researchMessagesRef.current, newMsg]
              onResearchUpdate(researchTabIdRef.current, researchTopic ?? "研究", researchMessagesRef.current, false)
            }
            break
          }
          case "done":
            setStreamingBlocks([])
            // Route new_messages to the topic where the request originated.
            // Uses the same source-topic tracking for both research and regular chat.
            {
              const doneTargetTopic = researchSourceTopicIdRef.current || streamingSourceTopicIdRef.current
              if (doneTargetTopic === currentTopicIdRef.current) {
                setCurrentTopic((prev) => {
                  if (!prev) return prev
                  return { ...prev, messages: [...prev.messages, ...event.new_messages] }
                })
              }
              // Otherwise: messages belong to a different topic — the topic list
              // will be refreshed below, and getTopic() picks up changes when the
              // user switches back.
            }
            refreshTopics()
            if (event.modified_files.length > 0) onFileChanged()
            // Mark research as done
            if (researchTabIdRef.current) {
              onResearchUpdate(researchTabIdRef.current, researchTopic ?? "研究", researchMessagesRef.current, true)
              researchTabIdRef.current = null
              researchMessagesRef.current = []
              setResearchTopic(null)
              researchSourceTopicIdRef.current = null
            }
            break
          case "error":
            setStreamingBlocks(prev => {
              const last = prev[prev.length - 1]
              const errText = `\n[错误: ${event.message}]`
              if (last?.type === "text") {
                return [...prev.slice(0, -1), { ...last, content: last.content + errText }]
              }
              return [...prev, { type: "text" as const, content: errText }]
            })
            break
        }
      }, abort.signal)
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setStreamingBlocks(prev => {
        const last = prev[prev.length - 1]
        const errText = `\n[请求失败: ${String(err)}]`
        if (last?.type === "text") {
          return [...prev.slice(0, -1), { ...last, content: last.content + errText }]
        }
        return [...prev, { type: "text" as const, content: errText }]
      })
    } finally {
      setStreaming(false)
      abortRef.current = null
      streamingSourceTopicIdRef.current = null
    }
  }, [currentTopicId, streaming, onFileChanged])

  const handleSend = useCallback(async () => {
    await sendText(inputText)
  }, [inputText, sendText])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const path = e.dataTransfer.getData("text/plain")
    if (path) { setInputText((prev) => prev + `@${path} `) }
  }, [])

  const handleNewTopic = async () => {
    // Don't abort the SSE while streaming — same reasoning as handleSelectTopic.
    if (streaming) {
      setStreamingBlocks([])
    } else {
      abortRef.current?.abort()
      setStreamingBlocks([])
      researchTabIdRef.current = null
      researchMessagesRef.current = []
      setResearchTopic(null)
      researchSourceTopicIdRef.current = null
    }
    setRollbackMenuMsgIdx(null)
    try {
      const t = await createTopic()
      setTopics((prev) => [{
        id: t.id, topic_name: t.topic_name, created_at: t.created_at, message_count: 0,
      }, ...prev])
      setCurrentTopic({ id: t.id, topic_name: t.topic_name, created_at: t.created_at, messages: [] })
      setCurrentTopicId(t.id)
    } catch { /* ignore */ }
  }

  const handleRenameTopic = async (id: string, newName: string) => {
    try {
      await renameTopic(id, newName)
      refreshTopics()
      if (id === currentTopicId && currentTopic) {
        setCurrentTopic({ ...currentTopic, topic_name: newName })
      }
    } catch { /* ignore */ }
  }

  const handleDeleteTopic = async (id: string) => {
    try {
      await deleteTopic(id)
      const list = await listTopics()
      setTopics(list)
      if (id === currentTopicId) {
        if (list.length > 0) {
          setCurrentTopicId(list[0].id)
        } else {
          const t = await createTopic()
          setCurrentTopicId(t.id)
          setTopics([{ id: t.id, topic_name: t.topic_name, created_at: t.created_at, message_count: 0 }])
        }
      }
    } catch { /* ignore */ }
  }

  const handleSelectTopic = (id: string) => {
    // Don't abort the SSE while streaming — the response belongs to the source
    // topic regardless of what the user is viewing. The guard in the SSE callback
    // will suppress chat events on the wrong topic and done will route correctly.
    if (streaming) {
      setStreamingBlocks([])
    } else {
      abortRef.current?.abort()
      setStreamingBlocks([])
      researchTabIdRef.current = null
      researchMessagesRef.current = []
      setResearchTopic(null)
      researchSourceTopicIdRef.current = null
    }
    setRollbackMenuMsgIdx(null)
    setCurrentTopicId(id)
    setShowHistory(false)
  }

  const handleBranch = async (messageIndex: number) => {
    if (!currentTopicId) return
    try {
      const t = await branchTopic(currentTopicId, messageIndex)
      setTopics((prev) => [{
        id: t.id, topic_name: t.topic_name, created_at: t.created_at, message_count: t.messages.length,
      }, ...prev])
      setCurrentTopic(t)
      setCurrentTopicId(t.id)
    } catch { /* ignore */ }
  }

  const handleRollbackConversation = async (messageIndex: number) => {
    if (!currentTopicId || !currentTopic) return
    try {
      const userMessage = currentTopic.messages[messageIndex]
      const topic = await rollbackConversation(currentTopicId, messageIndex)
      setCurrentTopic(topic)
      setInputText(userMessage?.content || "")
      setRollbackMenuMsgIdx(null)
      refreshTopics()
      setTimeout(() => inputRef.current?.focus(), 0)
    } catch { /* ignore */ }
  }

  const handleRollbackFiles = async (messageIndex: number) => {
    if (!currentTopicId) return
    try {
      await rollbackFiles(currentTopicId, messageIndex)
      setRollbackMenuMsgIdx(null)
      onFileChanged()
    } catch { /* ignore */ }
  }

  const handleRollbackConversationAndFiles = async (messageIndex: number) => {
    if (!currentTopicId || !currentTopic) return
    try {
      const userMessage = currentTopic.messages[messageIndex]
      const topic = await rollbackConversationAndFiles(currentTopicId, messageIndex)
      setCurrentTopic(topic)
      setInputText(userMessage?.content || "")
      setRollbackMenuMsgIdx(null)
      refreshTopics()
      onFileChanged()
      setTimeout(() => inputRef.current?.focus(), 0)
    } catch { /* ignore */ }
  }

  // --- action message handlers ---

  const getFileChangeActionData = (msg: ChatMessage): FileChangeActionData | null => {
    if (!msg.action_data) return null
    const files = (msg.action_data as Record<string, unknown>).files
    if (!Array.isArray(files) || files.length === 0) return null
    return { files: files as ModifiedFile[] }
  }

  const getPatternScoreActionData = (msg: ChatMessage): PatternScoreActionData | null => {
    if (!msg.action_data) return null
    const events = (msg.action_data as Record<string, unknown>).events
    if (!Array.isArray(events) || events.length === 0) return null
    return { events: events as PatternScoreActionData["events"] }
  }

  // --- rendering helpers ---

  const renderMessage = (msg: ChatMessage, i: number) => {
    if (msg.role === "user") {
      return (
        <MessageBubble
          key={i}
          content={msg.content}
          isUser
          onRollback={() => setRollbackMenuMsgIdx(rollbackMenuMsgIdx === i ? null : i)}
        >
          {rollbackMenuMsgIdx === i && (
            <div className="rollback-menu">
              <button className="rollback-menu-item" onClick={() => handleRollbackConversation(i)}>
                回退对话到此处
              </button>
              <button className="rollback-menu-item" onClick={() => handleRollbackFiles(i)}>
                回退文件到此处
              </button>
              <button className="rollback-menu-item" onClick={() => handleRollbackConversationAndFiles(i)}>
                回退对话和文件到此处
              </button>
            </div>
          )}
        </MessageBubble>
      )
    }

    if (msg.role === "action") {
      if (msg.action_type === "file_change" && msg.action_data) {
        const data = getFileChangeActionData(msg)
        if (!data) return null
        return (
          <FileChangesAction
            key={i}
            data={data}
            onViewDiff={(file) => onDiffView(file.path, file.pre_content, file.post_content)}
          />
        )
      }
      if (msg.action_type === "pattern_score_change" && msg.action_data) {
        const data = getPatternScoreActionData(msg)
        if (!data) return null
        return <PatternScoreAction key={i} data={data} />
      }
      return null
    }

    const hasContent = msg.content.trim().length > 0

    // Assistant message
    return (
      <div key={i}>
        {/* REFACTORED v2 */}
        {msg.reasoning_content && (
          <ThinkingBlock content={msg.reasoning_content} streaming={false} />
        )}
        {msg.tool_calls?.map((tc, j) => (
          <ToolCallCard key={j} name={tc.tool_name} arguments_={tc.arguments}
            result={tc.result} status="done" />
        ))}
        {hasContent && (
          <MessageBubble
            content={msg.content}
            isUser={false}
            onBranch={() => setBranchMenuMsgIdx(branchMenuMsgIdx === i ? null : i)}
          >
            {branchMenuMsgIdx === i && (
              <BranchMenu
                show
                onCopy={() => { navigator.clipboard.writeText(msg.content); setCopiedIdx(i); setTimeout(() => setCopiedIdx(null), 2000) }}
                onBranch={() => handleBranch(i)}
                onClose={() => setBranchMenuMsgIdx(null)}
              />
            )}
            {copiedIdx === i && <div className="copy-toast">已复制到剪贴板</div>}
          </MessageBubble>
        )}
      </div>
    )
  }

  if (loading) return <div className="chat-panel"><div className="chat-loading">加载中...</div></div>

  return (
    <div className="chat-panel">
      <TopicHeader
        topicName={currentTopic?.topic_name || "新对话"}
        onNewTopic={handleNewTopic}
        onToggleHistory={() => setShowHistory(!showHistory)}
        onRename={(name) => currentTopicId && handleRenameTopic(currentTopicId, name)}
      />

      <HistoryPanel
        topics={topics} currentTopicId={currentTopicId} show={showHistory}
        onClose={() => setShowHistory(false)} onSelect={handleSelectTopic}
        onNew={handleNewTopic} onRename={handleRenameTopic} onDelete={handleDeleteTopic}
      />

      <div className="chat-messages" ref={chatMessagesRef} onScroll={handleScroll} onDragOver={(e) => e.preventDefault()} onDrop={handleDrop}>
        {currentTopic?.messages.map((msg, i) => renderMessage(msg, i))}

        {/* Streaming state — stays visible on error until next send */}
        {streamingBlocks.length > 0 && (
          <div>
            {streamingBlocks.map((block, i) => {
              const isLast = i === streamingBlocks.length - 1
              if (block.type === "thinking") {
                return <ThinkingBlock key={i} content={block.content} streaming={streaming && isLast} />
              }
              if (block.type === "text") {
                return block.content ? <MessageBubble key={i} content={block.content} isUser={false} /> : null
              }
              return <ToolCallCard key={i} name={block.name} arguments_={block.arguments} result={block.result} status={block.status} />
            })}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-box" onDragOver={(e) => e.preventDefault()} onDrop={handleDrop}>
        <textarea ref={inputRef} className="chat-input" rows={2}
          placeholder={"输入消息... (Enter发送, Shift+Enter换行)"}
          value={inputText} onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown} disabled={streaming}
        />
        <button className="send-btn" onClick={handleSend}
          disabled={streaming || !inputText.trim()} title="发送">➤</button>
      </div>
    </div>
  )
}
