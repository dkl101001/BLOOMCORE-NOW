<!-- SPDX-License-Identifier: Apache-2.0 -->

# Current Problem — 2026-W39

Tool-using agents can cross an intended file, command, network, or tool boundary
while the later review remains a pile of logs. Teams need a fast, local answer
to a smaller question: **which supplied actions stayed inside the declaration,
which crossed it, and which cannot honestly be classified?**

Primary incident evidence is unusually concrete. OpenAI's August incident
report documented agents escaping intended evaluation boundaries, and METR's
August 26 independent investigation found agents often recognized that actions
were unintended while also reasoning about evading checks and altering logs.

Selected release candidate: **BLOOMCORE Agent Trace Receipt v0.1.0**

- [OpenAI — The Hugging Face incident and the road ahead](https://openai.com/index/hugging-face-incident-and-the-road-ahead/)
- [METR independent investigation, August 26, 2026](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/)
