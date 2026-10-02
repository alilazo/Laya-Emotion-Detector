# Product

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
People exploring a local showcase of linguistic emotion signals in their own conversations.

## Product Purpose
A chat workspace that scores each user message for independent anxiety, sadness, and fear signals, maintains per-chat gauges, and makes saved conversations explorable in an emotion constellation.

## Operating Context
Single-user, local-only showcase. Historical analysis spans all chats. New chats start with empty gauges. Live assistant replies come from the configured Ollama chat model through its OpenAI-compatible endpoint. Illustrative sample replies remain clearly identified and read only. The assistant is not a therapeutic or diagnostic service.

## Capabilities and Constraints
Local Laya inference; SQLite persistence; one Laya request for three ordinal questions per user message; message-order updates; no external emotion API; no diagnosis. Fear is labeled “Scared” in the UI. Model failure preserves prior gauges and records unavailable status.

## Evidence on Hand
The supplied 62-section feature brief is the authoritative spec. The seeded showcase content is illustrative and labeled as such. No clinical validation data or user accounts were provided.

## Product Principles
- Show independent signals, never a single winning emotion.
- Preserve message-level history and distinguish instant signals from conversation gauges.
- Make the visualization mathematically meaningful.
- Keep private text on the local machine.
