import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AssistantReply } from "./AssistantReply";
import type { Message } from "./types";

function reply(content: string, reasoning?: string) {
  const message: Message = {
    id: "test",
    role: "assistant",
    content,
    reasoning,
    emotion_status: "not_applicable",
    created_at: "2026-10-02",
  };
  return renderToStaticMarkup(<AssistantReply message={message} />);
}

describe("assistant Markdown replies", () => {
  it("formats structure and keeps thinking collapsed above the answer", () => {
    const html = reply(
      "## A simple plan\n\n**Start small.**\n\n- One\n- Two\n\n```css\nbutton { color: blue; }\n```\n\n| Step | Status |\n| --- | --- |\n| 1 | Ready |",
      "Private draft",
    );
    expect(html).toContain("<h2>A simple plan</h2>");
    expect(html).toContain("<strong>Start small.</strong>");
    expect(html).toContain("<li>One</li>");
    expect(html).toContain('class="language-css"');
    expect(html).toContain("<table>");
    expect(html).toContain('<details class="message-thoughts">');
    expect(html).not.toContain("<details open");
    expect(html.indexOf("Private draft")).toBeLessThan(
      html.indexOf("A simple plan"),
    );
  });

  it("renders raw HTML as text and blocks unsafe link URLs", () => {
    const html = reply(
      "<script>alert(1)</script>\n\n[Unsafe](javascript:alert%281%29)\n\n[Docs](https://example.com)",
    );
    expect(html).not.toContain("<script>");
    expect(html).not.toContain('href="javascript:');
    expect(html).toContain('href="https://example.com"');
    expect(html).toContain('rel="noopener noreferrer"');
  });
});
