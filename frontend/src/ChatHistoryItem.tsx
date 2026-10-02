import { useRef, useState } from "react";
import { X } from "lucide-react";
import type { Chat } from "./types";

export function ChatHistoryItem({
  chat,
  active,
  busy,
  deleting,
  onOpen,
  onDelete,
}: {
  chat: Chat;
  active: boolean;
  busy: boolean;
  deleting: boolean;
  onOpen: () => void;
  onDelete: () => Promise<boolean>;
}) {
  const [confirming, setConfirming] = useState(false);
  const [failed, setFailed] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const cancel = () => {
    setConfirming(false);
    setFailed(false);
    closeRef.current?.focus();
  };
  return (
    <div className={`chat-history-item ${active ? "active" : ""}`}>
      <div className="chat-history-row">
        <button
          className="chat-history-open"
          onClick={onOpen}
          aria-current={active ? "page" : undefined}
          title={chat.title}
        >
          <span className="chat-list-title">{chat.title}</span>
        </button>
        <button
          ref={closeRef}
          className="chat-delete"
          aria-label={`Delete chat: ${chat.title}`}
          aria-expanded={confirming}
          title={busy ? "Wait for the current reply" : "Delete chat"}
          disabled={busy || deleting}
          onClick={() => {
            setFailed(false);
            setConfirming((value) => !value);
          }}
        >
          <X size={14} />
        </button>
      </div>
      {confirming && (
        <div
          className="chat-delete-confirm"
          role="group"
          aria-label={`Confirm deletion of ${chat.title}`}
          onKeyDown={(event) => {
            if (event.key === "Escape" && !deleting) cancel();
          }}
        >
          <p>Delete this chat and its signals?</p>
          {failed && (
            <p className="chat-delete-error" role="alert">
              Couldn’t delete this chat. Please try again.
            </p>
          )}
          <div>
            <button disabled={deleting} onClick={cancel}>
              Cancel
            </button>
            <button
              className="confirm-delete"
              disabled={busy || deleting}
              onClick={async () => {
                setFailed(false);
                setFailed(!(await onDelete()));
              }}
            >
              {deleting ? "Deleting…" : "Delete"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
