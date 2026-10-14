---
name: remotion-best-practices
description: |
  Best practices for Remotion video creation in React. Covers animations, audio, captions, 3D content, charts, transitions, and more.
  Use when: (1) writing or debugging Remotion code, (2) creating video compositions in React, (3) adding animations, audio, or captions to videos, (4) implementing or debugging this project's video renderer; mentioning video alone does not trigger this skill.
---

> 协作边界：自主选择、澄清、批准和完成统一按 `../../AGENTS.md` 的“自主执行、澄清与完成”；下文步骤不构成逐步审批，职责切换由当前 Agent 完成。

## When to use

Use this skills whenever you are dealing with Remotion code to obtain the domain-specific knowledge.

## How to use

Read only the individual rule files needed for the current implementation or defect. Do not load all rules or redesign working components merely because this skill is available:

- [规则/animations.md](规则/animations.md) - Fundamental animation skills for Remotion
- [规则/audio.md](规则/audio.md) - Using audio and sound in Remotion - importing, trimming, volume, speed, pitch
- [规则/compositions.md](规则/compositions.md) - Defining compositions, stills, folders, default props and dynamic metadata
- [规则/sequencing.md](规则/sequencing.md) - Sequencing patterns for Remotion - delay, trim, limit duration of items
- [规则/timing.md](规则/timing.md) - Interpolation curves in Remotion - linear, easing, spring animations
- [规则/transitions.md](规则/transitions.md) - Scene transition patterns for Remotion
- [规则/videos.md](规则/videos.md) - Embedding videos in Remotion - trimming, volume, speed, looping, pitch

<!-- 如需扩展更多规则（如 3d、captions、fonts、images 等），在 规则/ 目录下新建对应 .md 文件并在此处添加引用 -->
