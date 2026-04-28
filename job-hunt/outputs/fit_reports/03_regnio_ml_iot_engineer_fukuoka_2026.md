# Fit Report: 機械学習/IoTエンジニア (株式会社Regnio)

## Fit Score
- Overall fit score: 17/30
- Confidence: medium
- Priority: low

## Job Summary

| Field | Value |
|-------|-------|
| Company | 株式会社Regnio |
| Title | 機械学習/IoTエンジニア |
| Type | Full-time (正社員) |
| Location | Fukuoka (hybrid: リモート週1 + フレックス) |
| Compensation | 400万〜700万円 |
| Source | Green (job ID 283132) |
| Product | 人協調AIクレーン安全作業支援システム (製造業DX) |
| Required Skills | **Hidden behind Green login** — not visible in public posting |
| Preferred Skills | **Hidden behind Green login** — not visible in public posting |

**Domain:** Manufacturing DX — AI + IoT crane safety system for steel industry. Co-developing with 2 steel manufacturers.

**Core responsibilities:**
- ML model design for hazard detection
- Real-time detection system with cameras + LiDAR
- Image recognition (people, hooks, steel plates)
- Edge deployment on Jetson / Raspberry Pi
- AWS data management + UI
- Safety assessment algorithm development

**Visible tech stack:** Python, C/C++, PyTorch, YOLO, OpenCV, AWS, Docker, IoT, Lambda, Jetson, Raspberry Pi, LiDAR, Gstreamer, Linux, GitHub, CircleCI, Jupyter

## Score Breakdown

| Component | Score | Max | Rationale |
|-----------|-------|-----|-----------|
| Required skill match | 3 | 5 | Core CV/ML/edge stack aligns well (Python, PyTorch, OpenCV, YOLO). Requirements hidden behind login; assessment based on visible stack only. |
| Preferred skill match | 2 | 5 | Also hidden. Based on visible stack, candidate has edge AI experience but lacks C/C++, AWS, Docker, IoT, Gstreamer, LiDAR, and CI/CD tooling. |
| Domain alignment | 3 | 5 | Technical adjacency is strong (edge AI + object detection + real-time inference), but no direct manufacturing, industrial safety, or factory-floor experience. |
| Language alignment | 3 | 5 | JLPT N2 is functional for a Japanese workplace. Already living in Fukuoka (same city). N2 may not meet full business-level expectations in a manufacturing setting. English (TOEIC 750) is a plus. |
| Experience alignment | 2 | 5 | Relevant internship + research experience in edge AI, CV, and model compression. However, candidate is a current M.S. student (graduating 2028) — not available for full-time now. No production ML/IoT ownership. |
| Evidence strength | 4 | 5 | 3 peer-reviewed publications, 1 commercial deployment (Sony smart glasses), JLPT N2 + TOEIC 750 certified, GitHub profile. Strong paper trail. |
| **Total** | **17** | **30** | |

## Evidence Mapping

| Claim / Skill | Candidate Evidence | Support Level |
|---------------|-------------------|---------------|
| Python | Primary language across all positions | Supported |
| PyTorch | Used in all research + internship work | Supported |
| OpenCV | Used at Sony + Shanghai Polytech research | Supported |
| YOLO / Object Detection | YOLOv5 latency reduction paper + Sony object recognition | Supported |
| Model compression (quantization, pruning) | Sony Edge AI internship — shipped to commercial product | Supported |
| Edge AI deployment | Sony smart camera/glasses deployment | Partially supported — different hardware platform than Jetson/RPi |
| Image recognition | Sony object recognition + CV research papers | Supported |
| Real-time inference optimization | YOLOv5 latency paper for lightweight robots | Partially supported |
| C/C++ | Not evidenced in profile | Not evidenced |
| AWS / Docker / Lambda / IoT | Not evidenced in profile | Not evidenced |
| Gstreamer | Not evidenced in profile | Not evidenced |
| LiDAR | Not evidenced in profile | Not evidenced |
| CircleCI / CI/CD | Not evidenced in profile | Not evidenced |
| Jetson / Raspberry Pi | No direct experience; edge AI work is transferable | Not evidenced (transferable) |
| Manufacturing domain | Academic + consumer-device background only | Not evidenced |
| Japanese (business level) | JLPT N2 | Partially supported — N2 may fall short of business fluency |
| Full-time availability | Current M.S. student (graduating 2028) | Not supported |

## Strongest Matches

- **Location:** Candidate already lives in Fukuoka — zero relocation friction.
- **Core CV/ML stack:** Python, PyTorch, OpenCV, YOLO, object detection — all strongly evidenced with publications and commercial deployment.
- **Edge AI experience:** Sony internship directly involved model compression (quantization, pruning) for edge devices, with results shipped in a commercial product (smart glasses).
- **Research rigor:** 3 peer-reviewed papers on object detection, lightweight backbones, and real-time inference — demonstrates depth beyond coursework.
- **Language base:** JLPT N2 + TOEIC 750 + daily life in Fukuoka provides functional working Japanese and supplementary English.

## Gaps and Risks

- **Timing mismatch (critical):** This is a full-time (正社員) position. Candidate is an M.S. student at Kyushu University through March 2028. Full-time commitment is not feasible during studies. Unless the company offers part-time or new-grad entry for 2028, this role is not currently actionable.
- **Hidden requirements:** All application-condition details (必須スキル, 歓迎スキル, 語学要件) are behind Green's login wall. The fit score is based on inferred requirements from the visible stack — actual requirements may be stricter or include disqualifiers.
- **Infra / IoT gap:** AWS, Docker, IoT, Lambda, Linux sysadmin, and CI/CD pipeline experience are absent from the candidate profile. This role expects end-to-end ownership from edge to cloud.
- **C/C++ gap:** The visible stack includes C/C++ (common in embedded/IoT contexts). Candidate only has Python.
- **No manufacturing domain experience:** Factory-floor familiarity, safety-critical systems, and industrial sensor integration (LiDAR) are all new territory.
- **JLPT N2 ceiling:** Manufacturing settings in Japan often expect N1-level or equivalent business Japanese for full-time engineers. The actual language bar is hidden behind login, but N2 may be a risk.

## Experiences To Emphasize

If applying (e.g., inquiring about new-grad or internship options), emphasize these specific experiences:

1. **Sony Edge AI Internship (2023-2024):** Object recognition for edge devices — quantization, pruning, data pipeline, model evaluation. Commercial deployment on smart glasses. Directly parallels the Jetson/RPi edge work in this role.
2. **YOLOv5 Latency Reduction Research:** Real-time detection optimization for lightweight robots. Shows ability to balance accuracy vs. speed on constrained hardware — highly relevant to crane safety real-time requirements.
3. **Lightweight Visual Backbone Paper (Neurocomputing, 2025):** Demonstrates deep understanding of model architecture design and trade-offs.
4. **Current Kyushu University Research:** ML/CV + multimodal + LLM/agentic AI exploration. Shows continuous skill growth and curiosity beyond core CV.

## Resume Tailoring Suggestions

- **Reorder projects:** Lead with Sony Edge AI work, then YOLOv5 latency paper, then lightweight backbone paper.
- **Add transferable framing:** Frame Sony edge-device work as "Edge AI deployment on resource-constrained hardware" to bridge the Jetson/RPi gap. Emphasize the end-to-end nature (data prep → training → compression → deployment).
- **Address C/C++ gap honestly:** If the candidate has even basic C/C++ exposure from undergraduate coursework, include it. Do not fabricate.
- **Add Fukuoka availability:** Explicitly mention current residence in Fukuoka — this is a genuine advantage the company will value.
- **Consider inquiry-first approach:** Rather than a direct application, consider a casual inquiry through Green to ask about new-grad or internship openings, since the full-time timing doesn't align.

## Recommendation

**Low priority** — revisit closer to graduation or if the company opens new-grad/internship positions.

- Strong technical alignment in CV/ML/edge AI, and the candidate is already in Fukuoka — the fundamentals are right.
- However, this is a full-time position and the candidate is a current M.S. student (graduating 2028). Full-time commitment is not feasible.
- Key requirements (skills, language level) are hidden behind login, introducing additional uncertainty.
- If the company offers new-grad hiring for 2028 graduates or internship positions, this becomes a high-priority target. Monitor Regnio's Green page for future openings.
- For now, focus energy on roles that match the candidate's current availability (internship, new-grad for 2026-2028) while building the missing infra skills (AWS, Docker) through coursework or side projects.
