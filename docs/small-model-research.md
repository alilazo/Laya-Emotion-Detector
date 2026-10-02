# Small local models for the emotion showcase

Research date: October 2, 2026. Primary sources only. No models were installed, no application settings were changed, and no inference benchmarks were run.

## What we are choosing

The replacement needs to do two different jobs: produce concise conversational answers, and return the emotion verifier's JSON with faithful quotes, current-user attribution, negation handling, and supported intensity levels. Laya remains the intensity scorer. The hard limit here is **8 billion total parameters**, including embeddings and any encoders included in the model artifact; active/effective counts do not replace that limit.

**Provisional shortlist:** Qwen3-4B-Instruct-2507 is a particularly useful direct-response challenger; Qwen3.5-4B is a newer candidate worth comparing with thinking explicitly disabled; LFM's smaller instruction models need comparison alongside them. Gemma 4 E2B is another plausible compact option. None can be declared the fastest and most accurate for this app from public general-purpose benchmarks alone.

## Verified candidates

Package sizes below are the current Ollama download listings, not runtime VRAM requirements. Exact artifact counts use Hugging Face's `safetensors.total` metadata, fetched from the model owner's repository; they count stored tensor elements rather than relying on the model name. Quantization changes storage precision, not the original model's parameter budget.

| Candidate | Total artifact count | Specific Ollama option | Listed download | Role in the comparison |
| --- | ---: | --- | ---: | --- |
| Qwen3-4B-Instruct-2507 | 4,022,468,096 | `qwen3:4b-instruct-2507-q4_K_M` | 2.5 GB | Direct-response, text-only challenger; native non-thinking |
| Qwen3.5-4B | 4,659,865,088 | `qwen3.5:4b-q4_K_M` | 3.4 GB | Newer general capability candidate; compare with thinking off |
| Qwen3.5-2B | 2,274,069,824 | `qwen3.5:2b-q4_K_M` | 1.9 GB | Smaller speed candidate with a notable instruction-following tradeoff |
| Gemma 4 E2B IT | 5,123,178,051 | `gemma4:e2b-it-q4_K_M` | 4.6 GB | Compact effective compute, larger actual artifact |
| Gemma 4 E4B IT | 7,996,156,490 | `gemma4:e4b-it-q4_K_M` | 6.6 GB | Just within the total cap; a quality comparison, not the smallest option |
| Ministral 3 3B Instruct 2512 | 3,849,090,048 | `ministral-3:3b-instruct-2512-q4_K_M` | 3.0 GB | Non-reasoning instruction/data-extraction alternative |
| Phi-4-mini-instruct | 3,836,021,760 | `phi4-mini:3.8b-q4_K_M` | 2.5 GB | Established text-only instruction alternative |

Artifact counts: [Qwen3 4B API](https://huggingface.co/api/models/Qwen/Qwen3-4B-Instruct-2507), [Qwen3.5 4B API](https://huggingface.co/api/models/Qwen/Qwen3.5-4B), [Qwen3.5 2B API](https://huggingface.co/api/models/Qwen/Qwen3.5-2B), [Gemma E2B API](https://huggingface.co/api/models/google/gemma-4-E2B-it), [Gemma E4B API](https://huggingface.co/api/models/google/gemma-4-E4B-it), [Ministral 3B API](https://huggingface.co/api/models/mistralai/Ministral-3-3B-Instruct-2512), [Phi mini API](https://huggingface.co/api/models/microsoft/Phi-4-mini-instruct).

Ollama package listings: [Qwen3 tags](https://ollama.com/library/qwen3/tags), [Qwen3.5 4B Q4](https://ollama.com/library/qwen3.5:4b-q4_K_M), [Qwen3.5 2B Q4](https://ollama.com/library/qwen3.5:2b-q4_K_M), [Gemma 4 tags](https://ollama.com/library/gemma4/tags), [Ministral 3 tags](https://ollama.com/library/ministral-3/tags), [Phi mini tags](https://ollama.com/library/phi4-mini/tags).

### Qwen3-4B-Instruct-2507

This variant generates answers directly and does not support a separate thinking mode. Qwen reports IFEval 83.4 and WritingBench 83.4, both useful signals for instruction adherence and reply quality, although neither measures this emotion task. It is distinct from generic `qwen3:4b` and the 2507 thinking model. A text-only 2.5 GB package with no reasoning tokens is a sensible practical comparison for two short calls per message. Its actual speed relative to LFM must be measured. [Official model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)

### Qwen3.5-4B and 2B

Qwen3.5 uses a hybrid attention layout, and the 4B card reports strong general results, including IFEval 89.8. The models think by default and expose a way to disable thinking. The 4B score must not be advertised as its measured accuracy in the proposed non-thinking emotion verifier. Qwen's own 2B table makes the distinction explicit: IFEval is 61.2 in non-thinking mode and 78.6 with thinking. That makes the 2B an interesting latency experiment, not an assumption of equal correctness. [4B model card](https://huggingface.co/Qwen/Qwen3.5-4B), [2B model card](https://huggingface.co/Qwen/Qwen3.5-2B)

Default Ollama `qwen3.5:2b` is Q8 at 2.7 GB; its explicit Q4 tag is 1.9 GB. Specify quantization when comparing small models so a default Q8 versus Q4 comparison does not masquerade as an architecture-only comparison. [Default 2B package](https://ollama.com/library/qwen3.5:2b), [2B Q4 package](https://ollama.com/library/qwen3.5:2b-q4_K_M)

### Gemma 4 E2B and E4B

Google describes E2B as 2.3B effective / 5.1B including embeddings and E4B as 4.5B effective / 8B including embeddings. Per-layer embedding lookups explain the difference. Do not describe them as ordinary 2B and 4B total models. Both official full artifacts pass the cap according to the repository metadata above; E4B is only just under it. Native system-role support and configurable thinking make both relevant. Google reports MMLU-Pro 60.0 for E2B and 69.4 for E4B, which is general knowledge evidence, not an emotion accuracy comparison. [Google model card](https://ai.google.dev/gemma/docs/core/model_card_4)

Thinking is enabled through a control token in the system instruction; ordinary conversation history should strip generated thoughts. Ollama's supported thinking controls should be used instead of manually introducing special tokens into this application's prompts. [Google prompt formatting](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4)

### Other candidates

- **Ministral 3 3B Instruct:** Mistral states 3.4B language parameters plus a 0.4B vision encoder, and identifies native JSON, system prompts, text classification, and data extraction as supported uses. Choose the instruct model rather than its separate reasoning sibling. The 8B-name artifact has about 8.918B stored tensor elements, exceeding this strict cap. [3B model card](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512), [8B artifact metadata](https://huggingface.co/api/models/mistralai/Ministral-3-8B-Instruct-2512)
- **Phi-4-mini-instruct:** A 3.8B dense text model with function calling and chat-format support. Microsoft's evaluations and limitations support treating it as a capable small general model, without evidence of superiority on current-user emotion extraction. [Microsoft model card](https://huggingface.co/microsoft/Phi-4-mini-instruct)
- **SmolLM3-3B:** Approximately 3.075B stored parameters, supports non-thinking and thinking modes; its authors report non-thinking IFEval 76.7. Worth considering for an English-heavy small-model experiment, but no working official Ollama library page was verified in this research. Avoid adding a community upload to the primary download recommendation without provenance/template checks. [Author model card](https://huggingface.co/HuggingFaceTB/SmolLM3-3B), [Artifact metadata](https://huggingface.co/api/models/HuggingFaceTB/SmolLM3-3B)

## Ollama integration facts

Ollama supports schema-constrained structured output. The OpenAI-compatible endpoint supports `response_format`. A schema can force a valid shape, but cannot prove that a quote supports the emotion, that attribution is correct, or that the intensity is justified. Keep the application's semantic quote validation and evaluate false positives separately. [Structured output docs](https://docs.ollama.com/capabilities/structured-outputs)

For thinking-capable models, Ollama native requests use `think: false` where supported. Current compatibility documentation maps `reasoning_effort: "none"` to false for boolean thinking models; use `/api/show` to inspect actual supported controls. Installed-version support needs verification before implementation. Hiding a Thinking dropdown in the UI does not save reasoning compute. [Thinking docs](https://docs.ollama.com/capabilities/thinking), [OpenAI compatibility docs](https://docs.ollama.com/api/openai-compatibility)

## Speed and accuracy decision

No cited primary source establishes a matched Ollama comparison of these candidates against LFM2.5-8B-A1B on this machine's RTX 4060 Ti 16 GB / Ryzen 5800X. Download size and total parameters cannot by themselves rank generation latency, especially against a sparse model with a smaller active path. The initial package sizes suggest room in 16 GB for compact quantized weights, but do not establish simultaneous model residency after Laya, context state, and runtime allocations.

A useful future comparison should keep the verifier prompt, context, JSON schema, quantization, output budget, and chat prompt fixed. Measure warm and cold end-to-end latency, verifier latency, time to first visible answer, complete reply time, and token throughput separately. Use the same output length when interpreting throughput.

Evaluate verifier correctness on at least: direct sadness/worry/fear; negation; resolved past feelings; another person's emotions; quotations; hypothetical scenarios; mixed emotions; short contextual answers; and intensity changes. Check exact quote validity, attribution, unsupported positive scores, and level agreement. Evaluate reply quality separately for invented loss/death details, empathy, brevity, and Markdown readability. Prefer the fastest candidate that meets the task's correctness target; public math, coding, and general instruction scores are only shortlist evidence.

## LFM and application timing

### Current LFM model and strict size cap

Liquid's card describes LFM2.5-8B-A1B as 8.3B total / 1.5B active, while the official Ollama Q4 artifact lists 8.47B. Both total counts exceed a strict 8-billion limit. A1B is an active-compute label, and this project's `:32k` suffix configures context capacity; neither reduces the total parameters. A dense 4B model need not generate tokens faster than this sparse model, even though its weights occupy less memory. [Liquid model card](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B), [Ollama artifact](https://ollama.com/library/lfm2.5:8b-a1b-q4_K_M)

### LFM2.5-1.2B-Instruct: tiny speed candidate

Liquid specifies **1.17B total parameters**, a 32,768-token context, and a direct-answer instruction template. The company recommends data extraction and RAG, while cautioning against knowledge-intensive work and programming. This makes it relevant to concise chat and evidence extraction, but does not establish reliable emotion intensity judgments. Liquid's instruction benchmarks are encouraging; they use their own evaluation settings and should not be treated as a controlled ranking against another publisher's table. [Official model card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct)

The official GGUF repository provides **731 MB Q4_K_M** and **1.25 GB Q8_0** files, with an explicit Ollama example using `hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q4_K_M`. The Q8 variant is also a useful quality comparison on a 16 GB GPU. Liquid's published device throughput uses other hardware and runtimes, so it is not a speed prediction for this RTX 4060 Ti. [Official GGUF files and Ollama instructions](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF/tree/main)

### LFM2.5-2.6B: accuracy challenger with thinking cost

The newer model has **2.69B total parameters**, but Liquid explicitly describes it as a pure reasoning model that always thinks before answering. Its published instruction and structured-output results make it a useful quality challenger. For this showcase's fast short interactions, extra reasoning tokens can offset high decoding throughput. It is not the first low-latency replacement to try. [Official model card](https://huggingface.co/LiquidAI/LFM2.5-2.6B), [Release and comparisons](https://www.liquid.ai/blog/lfm2-5-2-6b)

Liquid also publishes DSpark speculative draft models and speedups in supported runtimes. Those are not established drop-in speedups for this project's current Ollama endpoint, so they are outside the initial recommendation. [Liquid DSpark release](https://www.liquid.ai/blog/lfm2.5-dspark)

### Verified local application observations

Read-only inspection on October 2 found an RTX 4060 Ti with 16,380 MiB VRAM, a Ryzen 7 5800X, and approximately 48 GiB system RAM. Ollama is version 0.34.4. At inspection, `ollama ps` showed `lfm2.5-8b-a1b:32k` fully on the GPU, about 5.7 GB loaded, with a 32,768-token context. This establishes the current chat model's residency, not the emotion checker's performance or a candidate benchmark.

The local `/api/show` response for that LFM profile reports thinking metadata with only `false` supported and `false` default, despite listing a thinking capability. Liquid's card describes reasoning output. These signals do not prove which traces an actual current request produces; verify behavior before promising that an API flag can suppress it.

Source inspection shows the user-visible request waits for these stages in order:

1. Laya prediction and emotion evidence verification (`backend/app/model.py`, `backend/app/evidence.py`).
2. Score persistence (`backend/app/service.py`).
3. Chat generation (`backend/app/chat_model.py`).
4. A completed response returned to the frontend (`backend/app/service.py`).

Although the backend requests streaming from Ollama, it assembles the reply before returning it to the frontend. The chat request has no explicit thinking suppression or output-token limit. The evidence request uses temperature 0, `reasoning_effort: "none"`, and an 800-token output limit. Consequently, changing only the chat model cannot remove the verification time or expose earlier answer tokens.

The configured verifier is `qwen3.6-35b-a3b:ud-iq3-s`; its documented package is about 13.7 GB, compared with about 5.2 GB for the current chat weights. Their sum exceeds the GPU's 16 GB before context and runtime memory. Model swapping/offloading is therefore a plausible latency contributor, not a confirmed measured bottleneck. Using one smaller model for two separately prompted calls could reduce this pressure. Laya would still score intensity. Local evidence: `backend/app/config.py`, `README.md`, and the service/model files above.

### Recommended order

1. **Qwen3-4B-Instruct-2507:** first balanced trial for both short chat replies and separately prompted evidence JSON. Native non-thinking and a modest text-only package make latency behavior straightforward.
2. **LFM2.5-1.2B-Instruct:** first tiny speed trial. Prefer it if it passes the same emotion and conversational checks; compare Q4 and Q8 if necessary.
3. **Qwen3.5-4B with thinking off:** newer capability challenger. Validate the actual non-thinking configuration and task results rather than assuming its reasoning benchmarks carry over.

This order is an engineering judgment from the cited properties, not a measured speed or emotion-accuracy leaderboard. Run the existing 50-case evaluation (`backend/evaluation/emotion_cases.json`) as an initial regression check, review its expected labels, and add held-out cases before replacing the checker. No model download, inference run, application setting, or README modification was made during this research.
