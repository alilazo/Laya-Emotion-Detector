/*
THESIS: The plotted conversation history is the workspace's center of gravity.
OWN-WORLD: Deep indigo instrument canvas, crisp ivory text, amber/blue/violet signal ink.
STORY: Write in a chat, watch independent gauges move, then explore every saved trajectory.
FIRST VIEWPORT: Narrow conversation rail, substantial active work area, compact signal details.
FORM: Operate mode; fixed geometric plot and clear controls, with no decorative graph edges.
*/
import { Profiler, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  ChevronRight,
  CircleHelp,
  Compass,
  Focus,
  LockKeyhole,
  LoaderCircle,
  MessageCircle,
  Minus,
  Plus,
  Search,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { api, hasAccessKey, setAccessKey } from "./api";
import { AssistantReply } from "./AssistantReply";
import { ChatHistoryItem } from "./ChatHistoryItem";
import { EMOTIONS, LABELS } from "./types";
import type {
  Analytics,
  Chat,
  ChatEmotion,
  Emotion,
  Mode,
  Node,
  Scores,
  TimelinePoint,
} from "./types";
import { nodePoint, radius, VERTICES } from "./math";

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
function round(value: number) {
  return Math.round(value);
}
function titleCase(value: string) {
  return value === "fear"
    ? "Scared"
    : value.charAt(0).toUpperCase() + value.slice(1);
}

function Gauge({ emotion, value }: { emotion: Emotion; value: number }) {
  return (
    <div className={`gauge gauge-${emotion}`}>
      <div className="gauge-head">
        <span className="gauge-name">
          <i className="signal-dot" />
          {LABELS[emotion]}
        </span>
        <strong>{round(value)}</strong>
      </div>
      <div
        className="gauge-track"
        role="meter"
        aria-label={`${LABELS[emotion]} conversation signal`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={round(value)}
      >
        <span style={{ transform: `scaleX(${value / 100})` }} />
      </div>
    </div>
  );
}

function ChatView({
  chat,
  onSend,
  sending,
  onAnalytics,
  onNewChat,
  modelReady,
  chatReady,
  chatModel,
}: {
  chat: Chat | null;
  onSend: (content: string) => void;
  sending: boolean;
  onAnalytics: () => void;
  onNewChat: () => void;
  modelReady: boolean;
  chatReady: boolean;
  chatModel: string;
}) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
  }, [chat?.messages?.length, sending]);
  useEffect(() => {
    setDraft("");
  }, [chat?.id]);
  if (!chat)
    return (
      <main className="empty-chat">
        <div className="empty-mark">
          <Sparkles size={32} />
        </div>
        <h1>Every conversation has a shape.</h1>
        <p>
          Start a chat to trace the signals in each message. Your history
          becomes a map you can explore. A local Ollama model replies to you.
        </p>
      </main>
    );
  const scores: Scores = {
    anxiety: chat.current_anxiety,
    sadness: chat.current_sadness,
    fear: chat.current_fear,
  };
  const submit = () => {
    if (draft.trim() && !sending) {
      onSend(draft.trim());
      setDraft("");
    }
  };
  return (
    <main className="chat-layout">
      <div className="chat-main">
        <header className="content-header">
          <div>
            {chat.source === "illustrative" && (
              <div className="section-kicker">ILLUSTRATIVE SAMPLE</div>
            )}
            <h1>{chat.title}</h1>
            <p>
              {chat.emotion_message_count} analyzed user{" "}
              {chat.emotion_message_count === 1 ? "message" : "messages"} ·
              Started {formatDate(chat.created_at)}
            </p>
          </div>
          <button
            className="text-button"
            aria-label="View in analytics"
            onClick={onAnalytics}
          >
            View in analytics <ArrowRight size={16} />
          </button>
        </header>
        <div className="messages" aria-live="polite">
          {!chat.messages?.length && (
            <div className="chat-intro">
              <div className="intro-icon">
                <MessageCircle size={28} />
              </div>
              <h2>Begin anywhere.</h2>
              <p>
                Write a message to see its instant signals and how this
                conversation’s gauges change. Only your messages are scored.
              </p>
              <div className="prompt-list">
                {[
                  "I keep worrying about tomorrow’s interview.",
                  "I really miss my dog today.",
                  "Someone was outside my window and I felt scared.",
                ].map((text) => (
                  <button key={text} onClick={() => setDraft(text)}>
                    {text}
                    <ChevronRight size={16} />
                  </button>
                ))}
              </div>
            </div>
          )}
          {chat.messages?.map((message) => (
            <div className={`message-row ${message.role}`} key={message.id}>
              <div className="message-bubble">
                {message.role === "assistant" ? (
                  <AssistantReply
                    message={message}
                    illustrative={chat.source === "illustrative"}
                  />
                ) : (
                  <>
                    <div className="message-role">YOU</div>
                    <p>{message.content}</p>
                  </>
                )}
                {message.role === "user" && (
                  <span
                    className={`message-status status-${message.emotion_status}`}
                  >
                    {message.emotion_status === "ready"
                      ? "Signals saved"
                      : message.emotion_status === "unavailable"
                        ? "Emotion signal unavailable"
                        : "Analyzing…"}
                  </span>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="message-row assistant" role="status">
              <div className="message-bubble">
                <p className="reply-loading">
                  <LoaderCircle size={16} aria-hidden="true" /> Laya is
                  responding and thinking
                </p>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
        {chat.source === "illustrative" ? (
          <div className="sample-footer">
            <span>
              This illustrative chat is read only. Its values were authored to
              demonstrate the map.
            </span>
            <button className="primary-button" onClick={onNewChat}>
              Start your own chat <ArrowRight size={16} />
            </button>
          </div>
        ) : (
          <div className="composer">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                submit();
              }}
            >
              <label className="sr-only" htmlFor="message-input">
                Your message
              </label>
              <textarea
                id="message-input"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submit();
                  }
                }}
                placeholder="Write a message…"
                rows={2}
                maxLength={20000}
              />
              <button
                className="send-button"
                disabled={!draft.trim() || sending}
                aria-label="Send message"
              >
                <Send size={20} />
              </button>
            </form>
            <div className="composer-note">
              Ollama {chatModel} · Enter to send · Shift+Enter for a new line
            </div>
          </div>
        )}
      </div>
      <aside className="signal-panel">
        <div className="panel-heading">
          <span className="panel-icon">
            <BarChart3 size={19} />
          </span>
          <div>
            <h2>Emotion gauge</h2>
            <p>Current conversation state</p>
          </div>
        </div>
        <div className="gauge-list">
          {EMOTIONS.map((emotion) => (
            <Gauge key={emotion} emotion={emotion} value={scores[emotion]} />
          ))}
        </div>
        <div className="panel-rule" />
        <div className="panel-explainer">
          <CircleHelp size={17} />
          <p>
            These are linguistic emotion signals, not a diagnosis. Each signal
            can rise independently.
          </p>
        </div>
        <div
          className={`model-indicator ${modelReady ? "ready" : "unavailable"}`}
        >
          <span />
          {modelReady ? "Local Laya ready" : "Local Laya unavailable"}
        </div>
        <div
          className={`model-indicator chat-indicator ${chatReady ? "ready" : "unavailable"}`}
        >
          <span />
          {chatReady ? "Ollama chat ready" : "Ollama chat unavailable"}
        </div>
      </aside>
    </main>
  );
}

function Timeline({ points }: { points: TimelinePoint[] }) {
  const [hover, setHover] = useState<TimelinePoint | null>(null);
  const width = 570,
    height = 220,
    left = 35,
    right = 12,
    top = 18,
    bottom = 30;
  const x = (index: number) =>
    left +
    (points.length === 1
      ? (width - left - right) / 2
      : (index * (width - left - right)) / (points.length - 1));
  const y = (value: number) =>
    top + ((100 - value) * (height - top - bottom)) / 100;
  return (
    <div className="timeline-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Conversation emotion gauges by analyzed message"
      >
        {[0, 25, 50, 75, 100].map((mark) => (
          <g key={mark}>
            <line
              className="timeline-grid"
              x1={left}
              x2={width - right}
              y1={y(mark)}
              y2={y(mark)}
            />
            <text className="axis-text" x={0} y={y(mark) + 4}>
              {mark}
            </text>
          </g>
        ))}
        {EMOTIONS.map((emotion) => (
          <g key={emotion}>
            <polyline
              className={`line-${emotion}`}
              points={points
                .map((point, index) => `${x(index)},${y(point.gauge[emotion])}`)
                .join(" ")}
            />
            {points.map((point, index) => (
              <circle
                className={`point-${emotion}`}
                key={point.messageId}
                cx={x(index)}
                cy={y(point.gauge[emotion])}
                r="4"
                onMouseEnter={() => setHover(point)}
                onMouseLeave={() => setHover(null)}
              >
                <title>
                  Message {point.sequence}: {LABELS[emotion]}{" "}
                  {round(point.gauge[emotion])}
                </title>
              </circle>
            ))}
          </g>
        ))}
        <text className="axis-text" x={left} y={height - 5}>
          1
        </text>
        <text className="axis-text" x={width - right - 10} y={height - 5}>
          {points.length}
        </text>
      </svg>
      <div className="timeline-legend">
        {EMOTIONS.map((emotion) => (
          <span key={emotion} className={`legend-${emotion}`}>
            <i />
            {LABELS[emotion]}
          </span>
        ))}
      </div>
      {hover && (
        <div className="timeline-tooltip">
          Message {hover.sequence} ·{" "}
          {EMOTIONS.map(
            (emotion) => `${LABELS[emotion]} ${round(hover.gauge[emotion])}`,
          ).join(" · ")}
        </div>
      )}
    </div>
  );
}

function ChatDrawer({
  node,
  access,
  onClose,
  onOpenChat,
}: {
  node: Node;
  access: number;
  onClose: () => void;
  onOpenChat: (id: string) => void;
}) {
  const [data, setData] = useState<ChatEmotion | null>(null);
  const [error, setError] = useState("");
  const closeRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      } else if (event.key === "Tab") {
        const focusable = Array.from(
          drawerRef.current?.querySelectorAll<HTMLElement>(
            'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
          ) ?? [],
        );
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        } else if (!drawerRef.current?.contains(document.activeElement)) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previousFocus?.focus();
    };
  }, [onClose]);
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    api
      .chatEmotion(node.chatId)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [node.chatId, access]);
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside
        ref={drawerRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={`Analytics for ${node.title}`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="drawer-head">
          <button
            ref={closeRef}
            className="icon-button"
            onClick={onClose}
            aria-label="Close details"
          >
            <X size={20} />
          </button>
          <div className="section-kicker">CONVERSATION PROFILE</div>
          <h2>{node.title}</h2>
          <p>
            {formatDate(node.createdAt)} · {node.messageCount} analyzed messages{" "}
            {node.source === "illustrative" && "· Illustrative"}
          </p>
        </header>
        {error && <p className="error-banner">{error}</p>}
        {!data && !error && <p className="loading-text">Loading trajectory…</p>}
        {data && (
          <div className="drawer-body">
            {data.summary ? (
              <>
                <div className="summary-modes">
                  {(["final", "peak", "average"] as Mode[]).map((mode) => (
                    <section key={mode}>
                      <div className="mini-heading">
                        {mode === "final"
                          ? "Final state"
                          : mode === "peak"
                            ? "Peak signal"
                            : "Average gauge"}
                      </div>
                      {EMOTIONS.map((emotion) => (
                        <div className="score-row" key={emotion}>
                          <span>{LABELS[emotion]}</span>
                          <strong className={`text-${emotion}`}>
                            {round(data.summary![mode][emotion])}
                          </strong>
                        </div>
                      ))}
                    </section>
                  ))}
                </div>
                <h3>Emotion timeline</h3>
                <p className="subtle-copy">
                  Conversation gauges after each analyzed user message
                </p>
                <Timeline points={data.timeline} />
              </>
            ) : (
              <div className="no-data">
                No emotion data has been saved for this conversation.
              </div>
            )}
            <button
              className="primary-button open-chat"
              onClick={() => onOpenChat(node.chatId)}
            >
              Open conversation <ArrowRight size={17} />
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}

function Constellation({
  nodes,
  onSelect,
}: {
  nodes: Node[];
  onSelect: (node: Node) => void;
}) {
  const [hover, setHover] = useState<Node | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(
    null,
  );
  const reset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const zoomBy = (factor: number) =>
    setZoom((current) => Math.max(0.7, Math.min(3.2, current * factor)));
  const ordered = [...nodes].sort(
    (a, b) => b.overallIntensity - a.overallIntensity,
  );
  return (
    <div className="plot-shell">
      <div className="plot-toolbar">
        <div className="plot-key">
          <span>
            <i className="key-anxiety" />
            Anxiety
          </span>
          <span>
            <i className="key-sadness" />
            Sadness
          </span>
          <span>
            <i className="key-fear" />
            Scared
          </span>
          <span>
            <i className="key-neutral" />
            Neutral
          </span>
        </div>
        <div className="plot-actions">
          <button onClick={() => zoomBy(1.2)} aria-label="Zoom in">
            <Plus size={18} />
          </button>
          <button onClick={() => zoomBy(1 / 1.2)} aria-label="Zoom out">
            <Minus size={18} />
          </button>
          <button onClick={reset} aria-label="Reset view">
            <Focus size={18} />
          </button>
        </div>
      </div>
      <svg
        className="constellation"
        viewBox="0 0 900 500"
        role="img"
        aria-label={`Emotion constellation with ${nodes.length} chats. Anxiety at top, sadness bottom left, scared bottom right.`}
        onWheel={(event) => {
          event.preventDefault();
          zoomBy(event.deltaY < 0 ? 1.08 : 1 / 1.08);
        }}
        onPointerDown={(event) => {
          if (!(event.target as Element).closest(".plot-node")) {
            drag.current = {
              x: event.clientX,
              y: event.clientY,
              px: pan.x,
              py: pan.y,
            };
            event.currentTarget.setPointerCapture(event.pointerId);
          }
        }}
        onPointerMove={(event) => {
          if (drag.current) {
            const rect = event.currentTarget.getBoundingClientRect();
            setPan({
              x:
                drag.current.px +
                ((event.clientX - drag.current.x) * 900) / rect.width,
              y:
                drag.current.py +
                ((event.clientY - drag.current.y) * 500) / rect.height,
            });
          }
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        <defs>
          <linearGradient id="plotFill" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#26304a" stopOpacity=".68" />
            <stop offset="1" stopColor="#171e32" stopOpacity=".35" />
          </linearGradient>
        </defs>
        <g
          transform={`translate(${pan.x} ${pan.y}) translate(450 250) scale(${zoom}) translate(-450 -250)`}
        >
          <path
            d={`M ${VERTICES.anxiety.x} ${VERTICES.anxiety.y} L ${VERTICES.sadness.x} ${VERTICES.sadness.y} L ${VERTICES.fear.x} ${VERTICES.fear.y} Z`}
            fill="url(#plotFill)"
            stroke="#626c85"
            strokeWidth="1.5"
          />
          {[0.25, 0.5, 0.75].map((fraction) => (
            <path
              key={fraction}
              className="plot-guide"
              d={`M ${450 + (105 - 450) * fraction} ${50 + (440 - 50) * fraction} L ${450 + (795 - 450) * fraction} ${50 + (440 - 50) * fraction}`}
            />
          ))}
          <path
            className="plot-guide"
            d="M 450 50 L 450 440 M 105 440 L 622.5 245 M 795 440 L 277.5 245"
          />
          {ordered.map((node) => {
            const point = nodePoint(node);
            return (
              <g
                className={`plot-node node-${node.dominantEmotion}`}
                key={node.chatId}
                transform={`translate(${point.x} ${point.y})`}
                tabIndex={0}
                role="button"
                aria-label={`${node.title}, ${titleCase(node.dominantEmotion)}, intensity ${round(node.overallIntensity)}. Open details.`}
                onClick={(event) => {
                  event.stopPropagation();
                  onSelect(node);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(node);
                  }
                }}
                onMouseEnter={() => setHover(node)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(node)}
                onBlur={() => setHover(null)}
              >
                <circle className="node-hit" r="30" />
                <circle
                  className="node-halo"
                  r={radius(node.overallIntensity) + 6}
                />
                <circle
                  className="node-core"
                  r={radius(node.overallIntensity)}
                />
                <circle
                  className="node-shine"
                  cx={-radius(node.overallIntensity) * 0.28}
                  cy={-radius(node.overallIntensity) * 0.3}
                  r="2"
                />
                {node.mixed && (
                  <circle
                    className="node-mixed"
                    r={radius(node.overallIntensity) + 4}
                  />
                )}
              </g>
            );
          })}
        </g>
        <text className="vertex-label" x="450" y="29" textAnchor="middle">
          ANXIETY
        </text>
        <text className="vertex-label" x="85" y="480" textAnchor="start">
          SADNESS
        </text>
        <text className="vertex-label" x="815" y="480" textAnchor="end">
          SCARED
        </text>
      </svg>
      {nodes.length === 0 && (
        <div className="plot-empty">
          <Compass size={34} />
          <h3>No conversations in this view</h3>
          <p>Try another filter or start a chat to place the first node.</p>
        </div>
      )}
      {hover && (
        <div className="node-tooltip">
          <div className="tooltip-title">{hover.title}</div>
          <div className="tooltip-date">
            {formatDate(hover.createdAt)} · {hover.messageCount} messages{" "}
            {hover.source === "illustrative" && "· Illustrative"}
          </div>
          <div className="tooltip-scores">
            {EMOTIONS.map((emotion) => (
              <span key={emotion}>
                <i className={`key-${emotion}`} />
                {LABELS[emotion]} <b>{round(hover.values[emotion])}</b>
              </span>
            ))}
          </div>
          <div className="tooltip-foot">
            {titleCase(hover.dominantEmotion)} {hover.mixed ? "· Mixed" : ""} ·
            Intensity {round(hover.overallIntensity)}
          </div>
        </div>
      )}
      <div className="plot-caption">
        Position shows the signal mix. Size shows overall intensity. One node
        represents one conversation.
      </div>
    </div>
  );
}

function AnalyticsView({
  access,
  onOpenChat,
}: {
  access: number;
  onOpenChat: (id: string) => void;
}) {
  const [mode, setMode] = useState<Mode>("final");
  const [datePreset, setDatePreset] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [minimum, setMinimum] = useState<Scores>({
    anxiety: 0,
    sadness: 0,
    fear: 0,
  });
  const [dominant, setDominant] = useState("all");
  const [search, setSearch] = useState("");
  const [quick, setQuick] = useState("all");
  const [data, setData] = useState<Analytics | null>(null);
  const [selected, setSelected] = useState<Node | null>(null);
  const closeDrawer = useCallback(() => setSelected(null), []);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    const timer = setTimeout(() => {
      const dates = (() => {
        if (datePreset === "custom")
          return {
            start_date: startDate || undefined,
            end_date: endDate || undefined,
          };
        if (datePreset === "all") return {};
        const date = new Date();
        date.setDate(
          date.getDate() -
            (datePreset === "today" ? 0 : datePreset === "7" ? 6 : 29),
        );
        return {
          start_date: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`,
        };
      })();
      api
        .analytics({
          mode,
          ...dates,
          min_anxiety: minimum.anxiety,
          min_sadness: minimum.sadness,
          min_fear: minimum.fear,
          dominant,
          search,
        })
        .then((result) => {
          if (active) {
            setData(result);
            setError("");
          }
        })
        .catch((err) => {
          if (active) setError(err.message);
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 180);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [
    mode,
    datePreset,
    startDate,
    endDate,
    minimum.anxiety,
    minimum.sadness,
    minimum.fear,
    dominant,
    search,
    access,
  ]);
  const preset = (name: string) => {
    setQuick(name);
    setDominant("all");
    const next: Scores = { anxiety: 0, sadness: 0, fear: 0 };
    if (name === "anxiety" || name === "sadness" || name === "fear")
      next[name] = 70;
    if (name === "mixed") setDominant(name);
    if (name === "neutral") setDominant("low");
    setMinimum(next);
  };
  return (
    <main className="analytics-layout">
      <header className="analytics-header">
        <div>
          <div className="section-kicker">ALL CONVERSATIONS</div>
          <h1>Emotion analytics</h1>
          <p>
            Explore the shape and trajectory of every saved chat. Illustrative
            samples are labeled.
          </p>
        </div>
        <span className="analysis-note">
          <Sparkles size={15} /> Linguistic signals only
        </span>
      </header>
      <div className="summary-strip">
        <div className="summary-lead">
          <strong>{data?.summary.chatCount ?? "–"}</strong>
          <span>
            analyzed chats
            <br />
            <small>in date range</small>
          </span>
        </div>
        {EMOTIONS.map((emotion) => (
          <div key={emotion} className={`summary-signal summary-${emotion}`}>
            <span>Avg {LABELS[emotion]}</span>
            <strong>
              {data
                ? round(
                    data.summary[
                      `average${emotion.charAt(0).toUpperCase() + emotion.slice(1)}` as keyof Analytics["summary"]
                    ] as number,
                  )
                : "–"}
            </strong>
          </div>
        ))}
      </div>
      <div className="analytics-grid">
        <aside className="filter-panel">
          <div className="filter-title">
            <h2>Explore</h2>
            <p>Filters shape the map, not your saved history.</p>
          </div>
          <div className="filter-section">
            <h3>Node represents</h3>
            <div className="segmented">
              {(["final", "peak", "average"] as Mode[]).map((value) => (
                <button
                  key={value}
                  className={mode === value ? "selected" : ""}
                  onClick={() => setMode(value)}
                >
                  {titleCase(value)}
                </button>
              ))}
            </div>
            <p className="filter-hint">
              {mode === "final"
                ? "How each chat ended"
                : mode === "peak"
                  ? "The highest point reached"
                  : "The average gauge throughout"}
            </p>
          </div>
          <div className="filter-section">
            <label htmlFor="date-preset">Date range</label>
            <select
              id="date-preset"
              value={datePreset}
              onChange={(event) => setDatePreset(event.target.value)}
            >
              <option value="all">All time</option>
              <option value="today">Today</option>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="custom">Custom range</option>
            </select>
            {datePreset === "custom" && (
              <div className="date-inputs">
                <label>
                  From
                  <input
                    type="date"
                    value={startDate}
                    onChange={(event) => setStartDate(event.target.value)}
                  />
                </label>
                <label>
                  To
                  <input
                    type="date"
                    value={endDate}
                    onChange={(event) => setEndDate(event.target.value)}
                  />
                </label>
              </div>
            )}
          </div>
          <div className="filter-section">
            <h3>Quick view</h3>
            <div className="quick-list">
              {[
                ["all", "All chats"],
                ["anxiety", "High anxiety"],
                ["sadness", "High sadness"],
                ["fear", "High scared"],
                ["mixed", "Mixed high emotion"],
                ["neutral", "Low signal"],
              ].map(([value, label]) => (
                <button
                  className={quick === value ? "active" : ""}
                  key={value}
                  onClick={() => preset(value)}
                >
                  {label}
                  <ChevronRight size={15} />
                </button>
              ))}
            </div>
          </div>
          <div className="filter-section">
            <h3>Minimum signal</h3>
            {EMOTIONS.map((emotion) => (
              <label className={`range-control range-${emotion}`} key={emotion}>
                {LABELS[emotion]} <strong>{minimum[emotion]}</strong>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={minimum[emotion]}
                  onChange={(event) => {
                    setMinimum({
                      ...minimum,
                      [emotion]: Number(event.target.value),
                    });
                    setQuick("custom");
                  }}
                />
              </label>
            ))}
          </div>
          <div className="filter-section last">
            <label htmlFor="dominant-filter">Profile</label>
            <select
              id="dominant-filter"
              value={dominant}
              onChange={(event) => {
                setDominant(event.target.value);
                setQuick("custom");
              }}
            >
              <option value="all">Any profile</option>
              <option value="anxiety">Anxiety dominant</option>
              <option value="sadness">Sadness dominant</option>
              <option value="fear">Scared dominant</option>
              <option value="mixed">Mixed</option>
              <option value="low">Low signal</option>
              <option value="neutral">Neutral</option>
            </select>
          </div>
        </aside>
        <section className="map-section">
          <div className="map-header">
            <div>
              <h2>Emotion constellation</h2>
              <p>
                {data?.chats.length ?? 0} of {data?.totalInDateRange ?? 0}{" "}
                conversations shown · {mode} values
              </p>
            </div>
            <div className="search-box">
              <Search size={17} />
              <label className="sr-only" htmlFor="chat-search">
                Search chat titles
              </label>
              <input
                id="chat-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search chats"
              />
            </div>
          </div>
          {error && <p className="error-banner">{error}</p>}
          {loading && <div className="loading-indicator">Updating map…</div>}
          <Profiler
            id="constellation"
            onRender={(_id, _phase, duration) =>
              console.debug(`constellation_render_ms=${duration.toFixed(1)}`)
            }
          >
            <Constellation nodes={data?.chats ?? []} onSelect={setSelected} />
          </Profiler>
          {!!data?.chats.length && (
            <div
              className="mobile-node-list"
              aria-label="Conversations on the map"
            >
              <h3>Conversations on the map</h3>
              {data.chats.map((node) => (
                <button key={node.chatId} onClick={() => setSelected(node)}>
                  <span>
                    <strong>{node.title}</strong>
                    <small>
                      {titleCase(node.dominantEmotion)} ·{" "}
                      {formatDate(node.createdAt)}
                      {node.source === "illustrative" && " · Illustrative"}
                    </small>
                  </span>
                  <span className="mobile-node-scores">
                    A {round(node.values.anxiety)} · S{" "}
                    {round(node.values.sadness)} · F {round(node.values.fear)}
                  </span>
                  <ChevronRight size={16} />
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
      {selected && (
        <ChatDrawer
          node={selected}
          access={access}
          onClose={closeDrawer}
          onOpenChat={onOpenChat}
        />
      )}
    </main>
  );
}

export default function App() {
  const [keyPresent, setKeyPresent] = useState(hasAccessKey());
  const [keyDraft, setKeyDraft] = useState("");
  const [view, setView] = useState(
    location.pathname.startsWith("/analytics") || location.pathname === "/"
      ? "analytics"
      : "chat",
  );
  const [chatId, setChatId] = useState(
    location.pathname.match(/^\/chats\/([^/]+)/)?.[1] || "",
  );
  const [chats, setChats] = useState<Chat[]>([]);
  const [chat, setChat] = useState<Chat | null>(null);
  const [sendingChatId, setSendingChatId] = useState("");
  const [error, setError] = useState("");
  const [health, setHealth] = useState<{
    emotion: string;
    checkpoint: string;
    error: string | null;
    chat: string;
    chat_model: string;
  } | null>(null);
  const [revision, setRevision] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [deletingChatId, setDeletingChatId] = useState("");
  const historyPanelRef = useRef<HTMLDivElement>(null);
  const historyTriggerRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!historyOpen) return;
    const panel = historyPanelRef.current;
    const trigger = historyTriggerRef.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel?.querySelector<HTMLButtonElement>("button")?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setHistoryOpen(false);
      } else if (event.key === "Tab") {
        const controls = panel?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), [tabindex="0"]',
        );
        if (!controls?.length) return;
        const first = controls[0],
          last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", keydown);
      trigger?.focus();
    };
  }, [historyOpen]);
  const navigate = useCallback((path: string) => {
    history.pushState(null, "", path);
    setView(path.startsWith("/analytics") ? "analytics" : "chat");
    setChatId(path.match(/^\/chats\/([^/]+)/)?.[1] || "");
    setHistoryOpen(false);
  }, []);
  useEffect(() => {
    const pop = () => {
      setView(
        location.pathname.startsWith("/analytics") || location.pathname === "/"
          ? "analytics"
          : "chat",
      );
      setChatId(location.pathname.match(/^\/chats\/([^/]+)/)?.[1] || "");
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  const refresh = useCallback(() => {
    if (!keyPresent) return;
    api
      .chats()
      .then(setChats)
      .catch((err) => {
        setError(err.message);
        if (err.message.includes("access key")) setKeyPresent(false);
      });
  }, [keyPresent]);
  useEffect(() => {
    refresh();
    api
      .health()
      .then(setHealth)
      .catch(() => {});
  }, [refresh, revision]);
  useEffect(() => {
    let active = true;
    if (keyPresent && chatId)
      api
        .chat(chatId)
        .then((result) => {
          if (active) setChat(result);
        })
        .catch((err) => {
          if (active) setError(err.message);
        });
    else setChat(null);
    return () => {
      active = false;
    };
  }, [keyPresent, chatId, revision]);
  const create = async () => {
    try {
      const next = await api.createChat();
      setRevision((value) => value + 1);
      navigate(`/chats/${next.id}`);
      setChat({ ...next, messages: [] });
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const removeChat = async (id: string) => {
    if (deletingChatId || sendingChatId === id) return false;
    setDeletingChatId(id);
    try {
      await api.deleteChat(id);
      const remaining = chats.filter((item) => item.id !== id);
      setChats(remaining);
      if (location.pathname === `/chats/${id}`) {
        setChat(null);
        navigate(remaining.length ? `/chats/${remaining[0].id}` : "/chats");
      }
      setRevision((value) => value + 1);
      setError("");
      requestAnimationFrame(() =>
        (
          historyPanelRef.current?.querySelector<HTMLButtonElement>(
            ".chat-history-item.active .chat-history-open, button",
          ) ||
          (window.matchMedia("(max-width: 850px)").matches
            ? historyTriggerRef.current
            : document.querySelector<HTMLButtonElement>(
                ".sidebar .chat-history-item.active .chat-history-open",
              ) ||
              document.querySelector<HTMLButtonElement>(".sidebar .new-chat"))
        )?.focus(),
      );
      return true;
    } catch (err) {
      setError((err as Error).message);
      return false;
    } finally {
      setDeletingChatId("");
    }
  };
  const send = async (content: string) => {
    if (!chatId) return;
    const targetId = chatId;
    setSendingChatId(targetId);
    setError("");
    setChat((current) =>
      current?.id === targetId
        ? {
            ...current,
            messages: [
              ...(current.messages ?? []),
              {
                id: `pending-${crypto.randomUUID()}`,
                role: "user",
                content,
                emotion_status: "pending",
                created_at: new Date().toISOString(),
              },
            ],
          }
        : current,
    );
    try {
      const result = await api.send(targetId, content);
      if (location.pathname === `/chats/${targetId}`) setChat(result.chat);
      if (result.replyStatus !== "ready")
        setError(
          result.replyError ||
            "Ollama could not generate a reply. Your message was saved.",
        );
      setRevision((value) => value + 1);
    } catch (err) {
      setError((err as Error).message);
      api
        .chat(targetId)
        .then((result) => {
          if (location.pathname === `/chats/${targetId}`) setChat(result);
        })
        .catch(() => {});
    } finally {
      setSendingChatId((current) => (current === targetId ? "" : current));
    }
  };
  if (!keyPresent)
    return (
      <div className="access-screen">
        <div className="access-card">
          <div className="brand-mark">
            <Sparkles size={25} />
          </div>
          <div className="section-kicker">LOCAL SHOWCASE</div>
          <h1>Emotion Constellation</h1>
          <p>
            Enter the local access key printed in the backend terminal. Your
            conversations and emotion data remain on this computer.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setAccessKey(keyDraft);
              setKeyPresent(true);
              setError("");
            }}
          >
            <label htmlFor="access-key">Local access key</label>
            <div className="access-input">
              <LockKeyhole size={18} />
              <input
                id="access-key"
                autoFocus
                type="password"
                value={keyDraft}
                onChange={(event) => setKeyDraft(event.target.value)}
                required
              />
            </div>
            <button className="primary-button">
              Open showcase <ArrowRight size={17} />
            </button>
          </form>
          {error && <p className="error-banner">{error}</p>}
        </div>
      </div>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Sparkles size={21} />
          </span>
          <div>
            <strong>
              Emotion
              <br />
              Constellation
            </strong>
            <small>LOCAL SHOWCASE</small>
          </div>
        </div>
        <nav className="main-nav" aria-label="Main navigation">
          <button
            className={view === "chat" ? "active" : ""}
            aria-label="Conversations"
            ref={historyTriggerRef}
            aria-controls="compact-history-panel"
            aria-expanded={historyOpen}
            onClick={() => {
              if (window.matchMedia("(max-width: 850px)").matches)
                setHistoryOpen((open) => !open);
              else navigate(chatId ? `/chats/${chatId}` : "/chats");
            }}
          >
            <MessageCircle size={19} /> Conversations
          </button>
          <button
            className={view === "analytics" ? "active" : ""}
            onClick={() => navigate("/analytics")}
          >
            <Compass size={19} /> Analytics
          </button>
        </nav>
        <div className="sidebar-chats">
          <div className="sidebar-label">
            <span>Your chats</span>
            <span>{chats.length}</span>
          </div>
          <button className="new-chat" onClick={create}>
            <Plus size={18} /> New conversation
          </button>
          <div className="chat-list">
            {chats.map((item) => (
              <ChatHistoryItem
                key={item.id}
                chat={item}
                active={view === "chat" && item.id === chatId}
                busy={
                  sendingChatId === item.id ||
                  (!!deletingChatId && deletingChatId !== item.id)
                }
                deleting={deletingChatId === item.id}
                onOpen={() => navigate(`/chats/${item.id}`)}
                onDelete={() => removeChat(item.id)}
              />
            ))}
            {chats.length === 0 && (
              <p className="sidebar-empty">
                Your conversations will appear here.
              </p>
            )}
          </div>
        </div>
        <div className="sidebar-footer">
          <span
            className={`connection-dot ${health?.emotion === "ready" && health?.chat === "ready" ? "ready" : ""}`}
          />
          {health?.emotion === "ready" && health?.chat === "ready"
            ? "Local models connected"
            : "Check local models"}
          <small>
            Laya {health?.checkpoint || "typed-decisions"} · Ollama{" "}
            {health?.chat_model || "lfm2.5-8b-a1b:32k"}
          </small>
        </div>
      </aside>
      {historyOpen && (
        <div className="history-scrim" onClick={() => setHistoryOpen(false)}>
          <div
            id="compact-history-panel"
            className="history-panel"
            ref={historyPanelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Your conversations"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="history-head">
              <h2>Your conversations</h2>
              <button
                aria-label="Close conversations"
                onClick={() => setHistoryOpen(false)}
              >
                <X size={19} />
              </button>
            </div>
            <button className="new-chat history-new" onClick={create}>
              <Plus size={18} /> New conversation
            </button>
            <div className="history-items">
              {chats.map((item) => (
                <ChatHistoryItem
                  key={item.id}
                  chat={item}
                  active={view === "chat" && item.id === chatId}
                  busy={
                    sendingChatId === item.id ||
                    (!!deletingChatId && deletingChatId !== item.id)
                  }
                  deleting={deletingChatId === item.id}
                  onOpen={() => navigate(`/chats/${item.id}`)}
                  onDelete={() => removeChat(item.id)}
                />
              ))}
              {chats.length === 0 && (
                <p>Your conversations will appear here.</p>
              )}
            </div>
          </div>
        </div>
      )}
      <div className="main-frame">
        {error && (
          <div className="global-error" role="alert">
            {error}
            <button onClick={() => setError("")} aria-label="Dismiss error">
              <X size={15} />
            </button>
          </div>
        )}
        {view === "analytics" ? (
          <AnalyticsView
            access={revision}
            onOpenChat={(id) => navigate(`/chats/${id}`)}
          />
        ) : (
          <ChatView
            chat={chat?.id === chatId ? chat : null}
            onSend={send}
            sending={sendingChatId === chatId}
            onAnalytics={() => navigate("/analytics")}
            onNewChat={create}
            modelReady={health?.emotion === "ready"}
            chatReady={health?.chat === "ready"}
            chatModel={health?.chat_model || "lfm2.5-8b-a1b:32k"}
          />
        )}
      </div>
    </div>
  );
}
