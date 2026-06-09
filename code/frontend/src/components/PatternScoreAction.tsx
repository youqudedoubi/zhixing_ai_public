import type { PatternScoreActionData, PatternScoreEvent } from "../types/chat"

interface Props {
  data: PatternScoreActionData
}

function isCelebration(event: PatternScoreEvent): boolean {
  return (
    (event.category === "positive" && event.delta > 0) ||
    (event.category === "negative" && event.delta < 0)
  )
}

export default function PatternScoreAction({ data }: Props) {
  return (
    <div className="pattern-score-container">
      {data.events.map((event, idx) => (
        <div key={`${event.pattern_name}-${idx}`} className="pattern-score-card">
          <span className="pattern-score-name">
            {event.pattern_name}
            {isCelebration(event) ? " 🎆" : ""}
          </span>
          <span className={`pattern-score-delta ${event.delta >= 0 ? "up" : "down"}`}>
            {event.delta >= 0 ? `+${event.delta}` : event.delta}
          </span>
        </div>
      ))}
    </div>
  )
}
