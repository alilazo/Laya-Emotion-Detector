/* Extend the indigo chat surface with one quiet disclosure: thinking stays
   collapsed above the answer, with a native keyboard-operable summary. */
import { ChevronRight } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "./types";

function thinkingDuration(milliseconds: number) {
  if (milliseconds < 100) return "<0.1s";
  const seconds = milliseconds / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
}

export function AssistantReply({
  message,
  illustrative = false,
}: {
  message: Message;
  illustrative?: boolean;
}) {
  return (
    <>
      {message.reasoning ? (
        <details className="message-thoughts">
          <summary>
            <span>Thinking</span>
            {message.thinking_ms != null && (
              <span
                className="thinking-duration"
                title="Observed thinking time"
              >
                · {thinkingDuration(message.thinking_ms)}
              </span>
            )}
            <ChevronRight size={14} aria-hidden="true" />
          </summary>
          <div
            className="message-reasoning"
            role="region"
            aria-label="Assistant thinking"
            tabIndex={0}
          >
            <p>{message.reasoning}</p>
          </div>
        </details>
      ) : (
        <div className="message-role">
          {illustrative ? "SHOWCASE REPLY" : "ASSISTANT"}
        </div>
      )}
      <div className="markdown-content">
        <Markdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ children, href }) => (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ),
            pre: ({ children }) => (
              <pre tabIndex={0} aria-label="Code block">
                {children}
              </pre>
            ),
            table: ({ children }) => (
              <div
                className="markdown-table"
                role="region"
                aria-label="Response table"
                tabIndex={0}
              >
                <table>{children}</table>
              </div>
            ),
            img: ({ src, alt }) => (
              <img src={src} alt={alt || "Response image"} loading="lazy" />
            ),
          }}
        >
          {message.content || "No response text was returned."}
        </Markdown>
      </div>
    </>
  );
}
