# RecruitIQ V4.5.2 Engine: System Architecture & Reliability

The RecruitIQ V4.5.2 Engine is a hybrid AI system designed for **high consistency, explainability, and fault-tolerant decision-making**, rather than relying on a single probabilistic model.

---

## 🎯 Core Engine Architecture

The system operates through **four coordinated reasoning layers**, each contributing distinct signals:

### 1. Heuristic Layer (Deterministic Parsing)
* Catalog-based keyword and pattern extraction
* Ensures **high recall for known skills**
* Acts as a **baseline signal**, not a final decision-maker

### 2. Semantic Layer (Embedding Alignment)
* SentenceTransformers (all-MiniLM-L6-v2)
* Measures **contextual similarity between resume and JD**
* Provides robustness against phrasing variation

### 3. ML Inference Layer (Structured Decisioning)
* XGBoost trained on engineered features:
  * semantic similarity
  * skill contribution
  * experience alignment
* Evaluated using ROC-AUC (~0.75–0.90 depending on dataset)

### 4. Cognitive Layer (LLM-Assisted Interpretation)
* LLaMA3 (Groq) used for:
  * explanation
  * reasoning augmentation
* **Strictly constrained** to avoid overriding deterministic outputs

---

## 🛠️ System Reliability Principles

### ✅ Signal Redundancy
Multiple independent signals (heuristic + semantic + ML) reduce reliance on any single component.

### ✅ Deterministic Feature Pipeline
* Fixed feature ordering
* Stable preprocessing
* Ensures **repeatable outputs for identical inputs**

### ✅ Consistency by Design
All outputs (score, skill gaps, insights) are derived from a **shared skill representation layer**, preventing contradictions.

### ✅ Controlled LLM Usage
* LLM does not generate ground truth
* It explains structured outputs only
* Prevents hallucination-driven errors

### ✅ Conservative Scoring Strategy
The system is calibrated to:
* prioritize **explicit evidence over inferred skills**
* avoid inflated scores from vague matches

---

## ⚠️ Practical Considerations
* Performance varies based on:
  * resume quality
  * JD clarity
  * domain specificity
* Skill gap detection is **relative to extracted signals**, not absolute ground truth

---

## 🚀 Summary
RecruitIQ is not a single-model predictor, but a **composite decision engine** designed for consistency, interpretability, and robustness under imperfect data. This makes it suitable for **real-world hiring scenarios where reliability matters more than optimistic scoring**.
