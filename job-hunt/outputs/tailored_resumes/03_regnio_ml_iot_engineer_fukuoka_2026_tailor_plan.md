# Resume Tailoring Plan

## Target Job

| Field | Value |
|-------|-------|
| Company | 株式会社Regnio |
| Title | 機械学習/IoTエンジニア |
| Type | Full-time (正社員) |
| Location | Fukuoka (hybrid) |
| Compensation | 400万〜700万円 |
| Source | Green (job ID 283132) |
| Basename | `03_regnio_ml_iot_engineer_fukuoka_2026` |

**Important caveat:** This is a full-time position. Candidate is an M.S. student at Kyushu University through March 2028. This tailoring plan assumes the candidate is either (a) inquiring about flexibility (new-grad entry, part-time) or (b) wants a prepared plan for future reference. Do not submit as if immediately available for full-time.

## Recommended Positioning

**Role positioning:** "Computer Vision / Edge AI engineer-researcher with published work in object detection, real-time inference optimization, and edge-device model deployment — seeking to apply CV/ML expertise to manufacturing DX and industrial safety systems."

**Key differentiators:**
- Edge AI deployment with commercial impact (Sony smart glasses — shipped product)
- Published research on real-time object detection optimization (YOLOv5 latency reduction)
- Already living in Fukuoka — no relocation needed
- Bilingual technical communication (JLPT N2 + TOEIC 750)

**What NOT to claim:**
- Do NOT claim C/C++, AWS, Docker, IoT, Gstreamer, LiDAR, or CI/CD experience — not evidenced
- Do NOT claim manufacturing or industrial-safety domain knowledge
- Do NOT claim full-time availability during M.S. studies
- Do NOT claim business-level Japanese — JLPT N2 is functional but not "business fluent"

## Top Experiences to Emphasize

### 1. Sony Edge AI Internship (2023-2024) — PRIMARY

**Why:** Directly parallels the role's edge deployment responsibility (Jetson/Raspberry Pi). End-to-end pipeline: data prep → training → compression → deployment. Commercial outcome: shipped in smart glasses product.

**Evidence from profile:**
- Company: Sony Semiconductor Solutions (Shanghai)
- Title: Edge AI Engineer Intern
- Stack: Python, PyTorch, OpenCV, Quantization, Pruning
- Outcome: Object recognition function implemented in commercial smart-glasses product

**Tailored positioning:** "Applied quantization and pruning to deploy object recognition models on resource-constrained edge devices (smart cameras, smart glasses), achieving commercial-grade performance. End-to-end ownership from data pipeline through model compression to production deployment."

### 2. YOLOv5 Detection Latency Reduction (2022-2024) — SECONDARY

**Why:** Directly addresses "real-time" requirement. Optimizing detection latency for constrained hardware parallels crane safety real-time constraints.

**Evidence from profile:**
- Role: Student Researcher / Co-author
- Publication: Conference paper (2024), DOI: 10.1145/3671016.3671392
- Domain: Object Detection / Real-time Inference
- Target: Lightweight robots

**Tailored positioning:** "Optimized YOLOv5 detection latency to prevent real-time tracking failures on lightweight robotic platforms — directly transferable to real-time hazard detection on edge hardware."

### 3. Lightweight Visual Backbone Research (2022-2024) — TERTIARY

**Why:** Demonstrates depth in CV architecture design. Published in Neurocomputing (2025). Shows research rigor and model design capability.

**Evidence from profile:**
- Role: Student Researcher / Co-author (2nd author)
- Publication: Neurocomputing (2025), DOI: 10.1016/j.neucom.2025.129449
- Topic: Context-aware dual attention for lightweight visual backbones

**Tailored positioning:** "Designed and evaluated lightweight visual backbones with context-aware attention mechanisms — demonstrates systematic approach to accuracy-efficiency trade-offs relevant to edge CV systems."

## Resume Summary Changes

**Before (generic):**
> CV/ML-focused researcher-engineer with strengths in lightweight models, object detection, and fast inference.

**After (Regnio-targeted):**
> エッジデバイス向け物体認識・モデル軽量化・リアルタイム推論最適化の研究開発経験を持つCV/MLエンジニア。Python/PyTorch/OpenCVを用いたエンドツーエンド開発（データパイプライン構築からエッジ実装まで）を実務インターンシップで経験し、成果の一部はスマートグラス商用製品に実装。物体検出・軽量バックボーン設計に関する査読付き論文3件（Neurocomputing 他）を発表。九州大学大学院にてマルチモーダル情報処理・エージェント技術の研究に従事中。福岡在住。

**Translation:**
> CV/ML engineer with R&D experience in edge-device object recognition, model compression, and real-time inference optimization. End-to-end development experience (data pipeline to edge deployment) using Python/PyTorch/OpenCV through industry internship; results partially implemented in a commercial smart-glasses product. 3 peer-reviewed publications (including Neurocomputing) on object detection and lightweight backbone design. Currently pursuing multimodal information processing and agent technology research at Kyushu University Graduate School. Based in Fukuoka.

## Technical Skills Ordering

**Target-role priority order (top = most relevant to Regnio):**

1. Edge AI (モデル軽量化・エッジ実装) — matches Jetson/RPi deployment
2. Object Detection (物体検出) — matches YOLO, LiDAR+camera detection
3. Model Compression (量子化・枝刈り) — matches edge optimization
4. Computer Vision (コンピュータビジョン) — core to role
5. Python — primary language
6. PyTorch — primary framework
7. OpenCV — image processing
8. Inference Optimization (推論最適化) — real-time constraint
9. Image Processing (画像処理) — camera sensor pipeline
10. Multimodal AI / Agentic AI — secondary (not role-primary but shows range)

**De-emphasize (less relevant to this role):**
- LangGraph, LlamaIndex — agentic AI tools (not directly role-relevant)
- Data Analysis — too generic, fold into specific experiences
- Experimental Design — fold into research experience descriptions

## Bullets to Strengthen

These bullets should be promoted/expanded in the tailored resume:

| Original Bullet | Strengthened Version | Evidence |
|-----------------|---------------------|----------|
| "Applied quantization and pruning for model compression" | "量子化・枝刈りにより物体認識モデルを軽量化し、リソース制約のあるエッジデバイス（スマートカメラ、スマートグラス）への実装を実現" | Sony internship |
| "Evaluated object recognition models" | "物体認識モデルの精度・速度評価を実施し、エッジデバイス上の推論要件を満たすモデルを選定" | Sony internship |
| "Optimized model size and inference speed under limited compute resources" | "限られた計算リソース下でモデルサイズ削減と推論速度向上を両立させ、商用スマートグラス製品への実装に貢献" | Sony internship — commercial outcome |
| YOLOv5 latency work | "YOLOv5の検出遅延を低減し、軽量ロボットにおけるリアルタイムトラッキングの安定化を達成（査読付き国際会議に採録）" | YOLOv5 paper |
| Lightweight backbone paper | "文脈適応型デュアルアテンション機構を導入した軽量ビジュアルバックボーンの設計・評価（Neurocomputing誌、第二著者）" | Neurocomputing paper |

## Bullets to De-emphasize or Remove

| Bullet to Adjust | Reason |
|-----------------|--------|
| "Explored multimodal processing and agent-related technologies" | Too vague; not role-primary. Replace with specific transferable framing or move to end. |
| "Studied task design using LangGraph and LlamaIndex" | Agentic AI tools are not relevant to this ML/IoT role. Remove from primary experience section. |
| "Built research frameworks and experimental settings" | Too generic. Replace with specific quantifiable contributions. |
| Any bullet starting with "Participated in" or "Supported" | Passive framing — rewrite as active contributions. |

## Keywords to Add

Keywords from the job posting to naturally incorporate where truthful:

**Already evidenced — can use:**
- 物体検出 (Object Detection) ✓
- エッジ実装 (Edge Deployment) — via Sony internship (transferable to Jetson/RPi context)
- モデル軽量化 (Model Compression) ✓
- リアルタイム推論 (Real-time Inference) ✓
- 画像認識 (Image Recognition) ✓
- Python ✓
- PyTorch ✓
- OpenCV ✓
- YOLO ✓
- Jupyter ✓
- Linux — assumed through all work (acceptable to claim basic proficiency)
- GitHub ✓

**Not evidenced — do NOT claim:**
- C/C++ — no evidence in profile
- AWS / Lambda — no evidence
- Docker — no evidence
- IoT — no evidence
- Jetson / Raspberry Pi — no direct experience (frame Sony edge work as transferable)
- Gstreamer — no evidence
- LiDAR — no evidence
- CircleCI — no evidence

**Bridge language (where truthful transfer exists):**
- Instead of "Jetson経験": "エッジデバイス上でのモデル推論最適化経験（スマートカメラ・スマートグラス）"
- Instead of "AWS経験": Do not claim — leave gap visible

## Risks and Missing Information

| Risk | Severity | Mitigation |
|------|----------|------------|
| Full-time vs. student status | Critical | Do not apply as if available for full-time. Use inquiry approach or wait for new-grad opening. |
| Requirements hidden behind login | High | Tailoring is based on visible stack only. Actual must-have skills may include items candidate lacks entirely. |
| No C/C++ | Medium | Cannot be mitigated — visible stack includes C/C++. Leave gap visible; emphasize Python depth. |
| No AWS/Docker/IoT | Medium | Cannot be mitigated — these are explicit in the visible stack. Honest gap. |
| No manufacturing domain | Medium | Position as "製造業DXに関心" rather than claiming experience. |
| JLPT N2 (not N1) | Medium | Include JLPT N2 honestly. If the hidden language requirement demands N1, this is a blocker. |
| No LiDAR/Gstreamer | Low | Niche tools — unlikely to be hard blockers for CV/ML engineers. |
| master_experiences.json missing | Low | Using candidate_profile.json as primary evidence source. Less granular evidence available. |

## Human Review Notes

- [ ] Verify candidate is comfortable with the "inquire, don't apply" positioning given full-time vs. student mismatch
- [ ] Confirm whether any C/C++ or cloud (AWS/Docker) experience exists but was omitted from profile — if so, update `candidate_profile.json` first
- [ ] Review Japanese phrasing for naturalness — especially the suggested resume summary
- [ ] Decide whether to generate full resume/CV artifacts or wait until requirements are unlocked (login to Green)
- [ ] If proceeding, mark generated artifacts as `draft_requires_review` in manifest (not `ready_for_submission_review`)
- [ ] Confirm Fukuoka address is current and can be stated in application
