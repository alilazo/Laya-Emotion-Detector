# LFM2.5-1.2B emotion verifier trial

October 2, 2026.

**Trial ended:** Qwen 3.6 was restored at the user's request. The LFM 1.2B profile and both downloaded quantizations were removed from Ollama. This document records the previous trial, not the active configuration.

## Installed configuration

- Official source: `hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF:Q8_0`.
- Local Ollama profile: `lfm2.5-1.2b-instruct:32k`.
- Verified profile parameter: `num_ctx 32768`.
- Q8_0 weights: approximately 1.25 GB; 1.17B parameters.
- During the trial, the app used this profile for emotion evidence checking. Chat continued to use `lfm2.5-8b-a1b:32k`; Laya continued to score intensity.
- Existing system prompt, JSON schema, and evidence validation are unchanged.

## Observed results

Both Q4_K_M and Q8_0 passed **1 of 10** basic checks using the current verifier request. A pass requires all three emotions to have the expected present/absent result. This small authored sample is a compatibility and regression probe, not a representative accuracy benchmark or an intensity evaluation.

Failures included attributing emotions to neutral text, carrying a fictional speaker's emotions to the user, and inferring anxiety/fear from sadness. Some replies also failed the existing verbatim-quote validation. The stronger quantization did not resolve these errors.

Q8 warm calls in this sample took approximately 0.46–0.68 seconds; the first load/request took approximately 3.08 seconds. These times cover only evidence verification, not Laya or the final chat reply, and are not a matched comparison with Qwen.

Detailed local results were saved as `data/lfm-verifier-smoke-q4.json` and `data/lfm-verifier-smoke-q8.json`; local reports are excluded from the repository. Run the same authored checks against the currently configured verifier with `.venv-local\Scripts\python.exe backend/evaluation/check_verifier.py`. Use `--model <installed-model-name>` to select another installed profile. The removed LFM profiles must be downloaded and created again before testing them.

These results do **not** support recommending this model as an accurate drop-in replacement with the current prompt. The active verifier is again `qwen3.6-35b-a3b:ud-iq3-s`.

The backend's existing suite passed: **27 tests**. Those tests establish application behavior, not the new model's emotion accuracy. Evidence metadata was corrected to record the verifier's model name rather than the chat model's name.

After restoring Qwen 3.6, it passed **10 of 10** of these same basic emotion-presence checks. This remains a small regression sample, not a general accuracy claim.
