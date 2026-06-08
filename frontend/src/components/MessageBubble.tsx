import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface Props {
  content: string
  isUser: boolean
  children?: React.ReactNode
  onBranch?: () => void
  onRollback?: () => void
}

export default function MessageBubble({ content, isUser, children, onBranch, onRollback }: Props) {
  const bubbleClass = [
    "message-bubble",
    isUser ? "user" : "assistant",
    !isUser && onBranch ? "has-actions" : "",
    isUser && onRollback ? "has-actions" : "",
  ].filter(Boolean).join(" ")

  return (
    <div className={`message-row${isUser ? " user" : " assistant"}`}>
      <div className="message-bubble-wrapper">
        <div className={bubbleClass}>
          <div className="message-content">
            {isUser ? content : <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>}
          </div>
          {!isUser && onBranch && (
            <div className="message-actions">
              <div className="message-actions-btn-wrap">
                <button className="message-action-btn" title="更多操作" onClick={() => onBranch()}>
                  ...
                </button>
                {children}
              </div>
            </div>
          )}
          {isUser && onRollback && (
            <div className="message-actions user-actions">
              <div className="message-actions-btn-wrap">
                <button className="message-action-btn" title="回退" onClick={() => onRollback()}>
                  ↶
                </button>
                {children}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
