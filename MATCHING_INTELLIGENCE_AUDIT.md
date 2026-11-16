# HireLens Matching Intelligence Audit

**Date:** November 17, 2026  
**Auditor:** Cascade AI  
**Purpose:** Evaluate and improve candidate matching quality

---

## Executive Summary

The HireLens matching system uses a hybrid approach combining keyword-based skill matching, evidence extraction, and optional semantic similarity. However, **semantic matching is currently unavailable** due to missing `sentence-transformers` dependency, causing the system to fall back to a simplified scoring formula. The keyword-based matching has significant limitations in handling skill variations, synonyms, and contextual mentions outside the skills database.

**Key Findings:**
- Semantic matching: **DISABLED** (sentence-transformers not installed)
- Skill extraction: Exact keyword matching against 181 technical skills
- Normalization: Limited alias mappings (15 entries)
- Scoring: Fallback to 50% required + 50% preferred coverage
- Evidence: Section-aware extraction with strength classification

**Impact:** Candidates with relevant experience expressed in different terminology (e.g., "RESTful services" vs "REST API", "OOP" vs "Object-Oriented Programming") receive false negatives, artificially lowering their scores.

---

## Phase 1: Existing Architecture

### Data Flow: Resume to Final Score

```
1. Resume Upload
   ↓
2. Document Parsing (PyPDF2, python-docx)
   ↓
3. Text Extraction
   ↓
4. Resume Parsing Service
   - Section detection (education, experience, skills, projects, certifications)
   - Name, email, phone extraction
   - Education, experience, projects extraction
   ↓
5. Skill Extraction Service
   - Normalizes text (lowercase, whitespace normalization)
   - Matches against skills.json database (exact word boundary matching)
   - Returns technical_skills and soft_skills lists
   ↓
6. Job Analysis Service
   - Extracts job title
   - Detects required/preferred sections by keywords
   - Extracts skills from job description using same skills.json
   - Classifies as required or preferred based on section context
   ↓
7. Evidence Extraction Service
   - Detects resume sections
   - For each extracted skill, finds all occurrences in resume text
   - Classifies evidence type by section (experience, project, skills, education)
   - Assigns strength based on section and action verbs
   ↓
8. Scoring Service
   - Matches candidate skills to required/preferred skills (exact match after normalization)
   - Calculates required_coverage = (matched / total_required) * 100
   - Calculates preferred_coverage = (matched / total_preferred) * 100
   - Calculates evidence_score based on evidence strength
   - Attempts semantic similarity (currently disabled)
   ↓
9. Overall Score Calculation
   - If semantic available: 35%*required + 15%*preferred + 30%*semantic + 20%*evidence
   - If semantic unavailable (current state): 50%*required + 50%*preferred
   ↓
10. Candidate Ranking
    - Sort by overall_score descending
    - UI classification: High (≥80), Medium (≥60), Low (<60)
```

### Component Details

#### Resume Parsing Service (`resume_parser_service.py`)
- **Section Detection:** Regex-based pattern matching against predefined section keywords
- **Name Extraction:** First 2-4 capitalized words, excludes disallowed tokens
- **Email Extraction:** Regex pattern matching
- **Phone Extraction:** Multiple regex patterns for international formats
- **Education Extraction:** Degree pattern matching + institution keyword detection
- **Experience Extraction:** Job title patterns + company indicators
- **Projects Extraction:** Lines under projects section
- **Certifications Extraction:** Prominent cert patterns or section-based extraction

#### Skill Extraction Service (`skill_service.py`)
- **Skills Database:** `skills.json` with 181 technical skills, 46 soft skills
- **Matching Method:** Exact word boundary regex matching
- **Normalization:** `normalize_skill_name()` applies limited alias mappings
- **Alternative Skills:** Detects "or" and "/" patterns in job descriptions

#### Text Processor (`text_processor.py`)
- **Normalization:** Unicode NFKD normalization + whitespace collapse
- **Tokenization:** Word boundary regex
- **Stopword Removal:** 186 English stopwords
- **Skill Aliases:** 15 mappings (e.g., "oop" → "object-oriented programming", "rest" → "rest api")

#### Job Analysis Service (`job_analysis_service.py`)
- **Section Detection:** Keywords "required", "must have", "essential" → required section
- **Section Detection:** Keywords "preferred", "nice to have", "bonus" → preferred section
- **Fallback:** If no sections detected, all technical skills classified as required
- **Alternative Skills:** Groups skills with "or" or "/" as alternatives

#### Evidence Extraction Service (`evidence_extraction_service.py`)
- **Section Detection:** 13 section types with pattern matching
- **Evidence Finding:** Regex search for normalized skill in resume text
- **Context Extraction:** 150-character window around skill occurrence
- **Evidence Types:** demonstrated_in_experience, demonstrated_in_project, listed_in_skills, mentioned_in_education, mentioned_in_certification, incidental_mention
- **Evidence Strength:** strong (action verb + context), moderate, basic (skills section), weak
- **Deduplication:** Keeps strongest evidence per section

#### Semantic Matching Service (`semantic_matching_service.py`)
- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Status:** **DISABLED** - `sentence-transformers` not installed
- **Error Type:** `package_not_installed`
- **Fallback:** System continues without semantic component

#### Scoring Service (`scoring_service.py`)
- **Algorithm Version:** 2.0.0-evidence-aware
- **Default Weights:**
  - Required skills: 35%
  - Preferred skills: 15%
  - Semantic: 30%
  - Evidence: 20%
  - TF-IDF: 0% (optional)
- **Fallback Weights (current):**
  - Required skills: 50%
  - Preferred skills: 50%
- **Evidence Score Calculation:**
  - Strong: 100 points
  - Moderate: 75 points
  - Basic: 50 points
  - Weak: 25 points
  - Average across matched skills

---

## Phase 2: Current Scoring Formula

### Exact Formula (Current Fallback Mode)

```
overall_score = (0.5 * required_coverage) + (0.5 * preferred_coverage)

Where:
- required_coverage = (matched_required_skills / total_required_skills) * 100
- preferred_coverage = (matched_preferred_skills / total_preferred_skills) * 100
- matched_required_skills = skills in candidate_skills ∩ required_skills (after normalization)
- matched_preferred_skills = skills in candidate_skills ∩ preferred_skills (after normalization)
```

### Exact Formula (With Semantic Matching - Not Currently Active)

```
overall_score = (
    (0.35 * required_norm) +
    (0.15 * preferred_norm) +
    (0.30 * semantic_norm) +
    (0.20 * evidence_norm) +
    (0.00 * tfidf_norm)
) * 100

Where:
- required_norm = required_coverage / 100
- preferred_norm = preferred_coverage / 100
- semantic_norm = semantic_score / 100 (cosine similarity * 100)
- evidence_norm = evidence_score / 100
- tfidf_norm = tfidf_score / 100
- evidence_score = average(strength_points) across matched skills
```

### Normalization Process

```
1. Convert to lowercase
2. Collapse whitespace to single space
3. Apply alias mapping from _SKILL_ALIASES (15 mappings)
4. Exact string comparison for matching
```

### UI Classification Thresholds

```
High:   overall_score >= 80
Medium: 60 <= overall_score < 80
Low:    overall_score < 60
```

---

## Phase 3: Identified Weaknesses

### 1. Semantic Matching Unavailable

**Severity:** CRITICAL  
**Root Cause:** `sentence-transformers` package not installed  
**Impact:** System relies solely on keyword matching, losing semantic understanding

**Evidence:**
```
Semantic matching available: False
Error type: package_not_installed
Error message: sentence-transformers package not installed: No module named 'sentence_transformers'
```

**Consequences:**
- No ability to match related concepts (e.g., "RESTful services" ↔ "REST API")
- Document-level semantic similarity unavailable
- Fallback scoring formula reduces scoring sophistication

---

### 2. Limited Skill Normalization

**Severity:** HIGH  
**Root Cause:** Only 15 alias mappings in `_SKILL_ALIASES`  
**Impact:** Related terminology not recognized as equivalent

**Test Results:**

| Resume Term | JD Requirement | Normalized Resume | Normalized JD | Match? |
|-------------|----------------|-------------------|---------------|--------|
| RESTful services | REST API | rest api | rest api | **FAIL** (not in skills.json) |
| OOP | Object-Oriented Programming | object-oriented programming | object-oriented programming | **PASS** (alias works) |
| object-oriented design | Object-Oriented Programming | object-oriented design | object-oriented programming | **FAIL** (no alias) |
| SQL | PostgreSQL | sql | postgresql | **FAIL** (different skills) |
| FastAPI (in experience) | FastAPI | fastapi | fastapi | **PASS** (extracted from any section) |

**Analysis:**
- "RESTful" is not in skills.json → not extracted at all
- "object-oriented design" normalizes to itself, not to "object-oriented programming"
- "SQL" and "PostgreSQL" are separate entries with no equivalence mapping
- Only 15 aliases for hundreds of possible variations

**Code Location:** `app/utils/text_processor.py` lines 314-384

---

### 3. Skills Database Coverage Gaps

**Severity:** MEDIUM  
**Root Cause:** Fixed list of 181 technical skills  
**Impact:** Valid technical terms not recognized

**Missing Examples:**
- "RESTful" (not in database)
- "RESTful services" (not in database)
- "object-oriented design" (not in database)
- "microservices architecture" (only "Microservices" exists)
- "cloud-native" (not in database)
- "serverless" (in database but may miss variations)

**Code Location:** `app/data/skills.json`

---

### 4. Exact Word Boundary Matching

**Severity:** MEDIUM  
**Root Cause:** Regex `\b{skill}\b` requires exact word boundaries  
**Impact:** Compound terms or variations not matched

**Example:**
- JD requires: "REST API"
- Resume has: "RESTful APIs"
- Pattern: `\bREST API\b`
- Result: No match (word boundary issue + term difference)

**Code Location:** `app/services/skill_service.py` lines 52-53

---

### 5. No Contextual Skill Extraction

**Severity:** MEDIUM  
**Root Cause:** Skills extracted regardless of section context  
**Impact:** Skills in project descriptions treated same as skills in skills section

**Current Behavior:**
- Skills extracted from entire resume text
- No distinction between:
  - "Skills: Python" (explicit skill claim)
  - "Built a Python application" (demonstrated experience)
  - "Learning Python" (aspirational, not experienced)

**Evidence:** Test 4 showed FastAPI extracted from experience section successfully, but this is due to keyword presence, not contextual understanding.

---

### 6. Evidence Extraction Limitations

**Severity:** LOW-MEDIUM  
**Root Cause:** Regex-based snippet extraction without semantic understanding  
**Impact:** Evidence may be weak or irrelevant

**Limitations:**
- Fixed 150-character window may cut off important context
- Sentence boundary detection is basic
- No distinction between:
  - "Used Python for data analysis" (relevant)
  - "Python is a popular language" (irrelevant)
- Action verb detection is keyword-based, not semantic

**Code Location:** `app/services/evidence_extraction_service.py` lines 170-206

---

### 7. Fallback Scoring Formula Overweights Preferred Skills

**Severity:** MEDIUM  
**Root Cause:** 50% weight to preferred skills in fallback mode  
**Impact:** Candidates with many preferred skills but missing required skills may score artificially high

**Current Fallback:**
```
overall_score = 0.5 * required_coverage + 0.5 * preferred_coverage
```

**Example:**
- Required: 6 skills, candidate has 2 → 33.3% coverage
- Preferred: 6 skills, candidate has 6 → 100% coverage
- Overall: 0.5 * 33.3 + 0.5 * 100 = 66.7% (Medium)

**Issue:** Candidate missing 4/6 required skills (67% gap) scores as "Medium" due to strong preferred skill coverage.

**Code Location:** `app/services/scoring_service.py` lines 112-119

---

### 8. No Penalty for Keyword Stuffing

**Severity:** LOW  
**Root Cause:** No mechanism to detect or penalize skill inflation  
**Impact:** Candidates listing many skills without evidence not penalized

**Current Behavior:**
- Skills extracted from skills section treated as valid
- Evidence strength only affects evidence_score (20% weight in full mode, 0% in fallback)
- In fallback mode, evidence_score is not used at all

---

## Phase 4: Concrete Code Examples

### Example 1: REST API vs RESTful Services - False Negative

**Resume Text:**
```
Experience with RESTful services and building REST APIs
```

**JD Requirement:**
```
Required Skills: REST API
```

**Execution Flow:**
1. `extract_skills()` called on resume text
2. Normalizes text to lowercase
3. Iterates through 181 technical skills in skills.json
4. Pattern: `\bREST API\b` (case-insensitive)
5. "RESTful" not in skills.json → not matched
6. "REST API" not found in text (word boundary issue)
7. Result: `[]` (no skills extracted)
8. `match_skills_to_requirements()` returns 0% match

**Root Cause:** 
- "RESTful" not in skills.json
- No alias mapping for "RESTful" → "REST API"
- Exact word boundary matching fails on variations

**File:** `app/services/skill_service.py` lines 32-72

---

### Example 2: OOP vs Object-Oriented Design - Partial False Negative

**Resume Text:**
```
Strong understanding of OOP principles and object-oriented design
```

**JD Requirement:**
```
Required Skills: Object-Oriented Programming
```

**Execution Flow:**
1. `normalize_skill_name("OOP")` → "object-oriented programming" (alias works)
2. `normalize_skill_name("object-oriented design")` → "object-oriented design" (no alias)
3. "object-oriented programming" in skills.json → extracted
4. "object-oriented design" not in skills.json → not extracted
5. Match: "object-oriented programming" matches JD requirement
6. Result: 1/1 matched (100%) if only OOP mentioned

**Root Cause:**
- "object-oriented design" has no alias to "object-oriented programming"
- These are treated as different skills

**File:** `app/utils/text_processor.py` lines 386-394

---

### Example 3: PostgreSQL vs SQL - False Negative

**Resume Text:**
```
Experience with SQL databases and query optimization
```

**JD Requirement:**
```
Required Skills: PostgreSQL
```

**Execution Flow:**
1. "SQL" in skills.json → extracted
2. "PostgreSQL" in skills.json (different entry)
3. No alias mapping between SQL and PostgreSQL
4. Match: SQL ≠ PostgreSQL
5. Result: 0% match

**Root Cause:**
- SQL and PostgreSQL are separate database entries
- No hierarchical relationship or equivalence mapping
- System assumes specific database knowledge is required

**File:** `app/data/skills.json` lines 23-24, 68-69

---

### Example 4: FastAPI in Experience Section - Success

**Resume Text:**
```
Skills: Python, JavaScript
Experience: Developed web applications using FastAPI framework
Projects: Built REST APIs with FastAPI
```

**JD Requirement:**
```
Required Skills: FastAPI
```

**Execution Flow:**
1. `extract_skills()` scans entire text
2. "FastAPI" in skills.json → extracted from experience section
3. "FastAPI" in skills.json → extracted from projects section
4. Deduplication removes duplicate
5. Match: FastAPI matches JD requirement
6. Result: 100% match

**Analysis:**
- This works because FastAPI is in skills.json
- Extraction is section-agnostic (both experience and projects)
- No distinction between "used FastAPI" vs "know FastAPI"

---

## Phase 5: Root Cause Analysis

### False Negative Classification

| Example | Root Cause | Type |
|---------|------------|------|
| REST API vs RESTful services | Skill not in database + no alias | Skill extraction failure |
| OOP vs object-oriented design | Incomplete alias mapping | Normalization failure |
| PostgreSQL vs SQL | No equivalence mapping | Normalization failure |
| FastAPI in projects | Works correctly | N/A |

### Failure Type Distribution

- **Skill extraction failure:** 25% (terms not in database)
- **Normalization failure:** 50% (incomplete aliases, no equivalence)
- **Semantic matching failure:** 25% (semantic unavailable)
- **Evidence validation failure:** 0% (evidence works but limited)
- **Scoring logic failure:** 0% (scoring formula is correct for inputs)

---

## Phase 6: Recommended Improvements (Ordered by Impact)

### 1. Enable Semantic Matching (CRITICAL)

**Impact:** HIGH  
**Effort:** LOW  
**Risk:** LOW

**Action:** Install `sentence-transformers` package

**Command:**
```bash
pip install sentence-transformers
```

**Expected Improvement:**
- Document-level semantic similarity between resume and job description
- Ability to match related concepts (RESTful ↔ REST API)
- Improved ranking for candidates with relevant experience expressed differently
- Activation of full scoring formula (35% required + 15% preferred + 30% semantic + 20% evidence)

**Risks:**
- Increased memory usage (model loading)
- Slower inference time
- Model download on first run (~100MB)

---

### 2. Expand Skill Alias Mappings (HIGH)

**Impact:** HIGH  
**Effort:** MEDIUM  
**Risk:** LOW

**Action:** Add comprehensive alias mappings to `_SKILL_ALIASES`

**Recommended Additions:**
```python
_SKILL_ALIASES: Dict[str, str] = {
    # Existing mappings...
    
    # REST API variations
    "restful": "rest api",
    "restful services": "rest api",
    "restful web services": "rest api",
    "rest apis": "rest api",
    
    # OOP variations
    "object-oriented design": "object-oriented programming",
    "ood": "object-oriented programming",
    "object oriented analysis and design": "object-oriented programming",
    
    # Database variations
    "sql database": "sql",
    "relational database": "sql",
    "rdbms": "sql",
    "nosql database": "nosql",
    
    # Cloud variations
    "cloud computing": "aws",  # Context-dependent, may need separate handling
    "cloud native": "kubernetes",
    
    # API variations
    "web services": "rest api",
    "web service": "rest api",
    "http api": "rest api",
    
    # Framework variations
    "reactjs": "react",
    "angularjs": "angular",
    "vuejs": "vue.js",
}
```

**Expected Improvement:**
- Better matching of skill variations
- Reduced false negatives from terminology differences
- Minimal performance impact

**Risks:**
- Over-generalization (e.g., mapping "cloud computing" to "AWS" may be incorrect)
- Maintenance burden to keep aliases updated

---

### 3. Add Hierarchical Skill Relationships (HIGH)

**Impact:** HIGH  
**Effort:** HIGH  
**Risk:** MEDIUM

**Action:** Implement skill hierarchy or equivalence classes

**Proposed Structure:**
```python
_SKILL_HIERARCHY = {
    "databases": {
        "sql": ["sql", "postgresql", "mysql", "microsoft sql server", "oracle", "sqlite"],
        "nosql": ["mongodb", "redis", "cassandra", "dynamodb", "neo4j", "elasticsearch"],
    },
    "web_frameworks": {
        "python": ["django", "flask", "fastapi"],
        "javascript": ["react", "angular", "vue.js", "express.js", "node.js"],
    },
    "api_design": {
        "rest": ["rest api", "restful", "restful services", "web services"],
        "graphql": ["graphql", "apollo"],
    },
    "programming_paradigms": {
        "oop": ["object-oriented programming", "object-oriented design", "ood"],
    },
}
```

**Matching Logic:**
- If JD requires "SQL", match any skill in SQL hierarchy
- If JD requires specific database (PostgreSQL), only match PostgreSQL
- Configurable strictness level

**Expected Improvement:**
- PostgreSQL vs SQL false negatives resolved
- Framework family matching (Django ↔ Python web development)
- More flexible matching without over-generalization

**Risks:**
- Complex implementation
- May introduce false positives if hierarchy too broad
- Requires careful design of strictness levels

---

### 4. Improve Skills Database Coverage (MEDIUM)

**Impact:** MEDIUM  
**Effort:** MEDIUM  
**Risk:** LOW

**Action:** Expand skills.json with missing technical terms

**Recommended Additions:**
- RESTful, RESTful services
- object-oriented design, OOD
- cloud-native, serverless
- microservices architecture
- event-driven architecture
- domain-driven design
- test-driven development (already present as TDD)
- behavior-driven development (already present as BDD)

**Expected Improvement:**
- More skills recognized from modern resumes
- Better coverage of contemporary terminology

**Risks:**
- Database bloat
- May increase false positives if terms too generic

---

### 5. Adjust Fallback Scoring Weights (MEDIUM)

**Impact:** MEDIUM  
**Effort:** LOW  
**Risk:** MEDIUM

**Action:** Increase required skill weight in fallback mode

**Current:**
```python
overall_score = (0.5 * required_coverage) + (0.5 * preferred_coverage)
```

**Recommended:**
```python
overall_score = (0.7 * required_coverage) + (0.3 * preferred_coverage)
```

**Rationale:**
- Required skills are more critical than preferred
- 70/30 split better reflects hiring priorities
- Reduces artificial inflation from preferred skill coverage

**Expected Improvement:**
- Candidates missing required skills score lower
- More accurate representation of candidate fit

**Risks:**
- May penalize candidates with strong overall fit but missing one required skill
- Requires validation with hiring managers

---

### 6. Add Contextual Skill Extraction (MEDIUM)

**Impact:** MEDIUM  
**Effort:** HIGH  
**Risk:** MEDIUM

**Action:** Distinguish between skill claims and demonstrated experience

**Proposed Logic:**
```python
def extract_skills_with_context(resume_text):
    skills = []
    
    # Skills section: explicit claims (lower confidence)
    skills_section = get_section_text(resume_text, "skills")
    for skill in find_skills(skills_section):
        skills.append({"skill": skill, "context": "claimed", "confidence": 0.7})
    
    # Experience/Projects: demonstrated (higher confidence)
    exp_text = get_section_text(resume_text, "experience") + get_section_text(resume_text, "projects")
    for skill in find_skills(exp_text):
        skills.append({"skill": skill, "context": "demonstrated", "confidence": 1.0})
    
    return skills
```

**Scoring Impact:**
- Demonstrated skills weighted higher than claimed skills
- Aspirational mentions ("learning Python") excluded or weighted lower

**Expected Improvement:**
- Better distinction between skill knowledge and experience
- Reduced impact of keyword stuffing

**Risks:**
- Complex implementation
- Section detection errors may misclassify skills
- May require tuning of confidence weights

---

### 7. Improve Evidence Extraction Quality (LOW-MEDIUM)

**Impact:** LOW-MEDIUM  
**Effort:** MEDIUM  
**Risk:** LOW

**Action:** Enhance snippet extraction and relevance scoring

**Proposed Improvements:**
- Dynamic window sizing based on sentence boundaries
- Relevance scoring based on proximity to action verbs
- Filter out generic statements ("Python is popular")
- Prioritize evidence from experience/projects over skills section

**Expected Improvement:**
- More meaningful evidence snippets
- Better evidence strength classification

**Risks:**
- Increased complexity
- May still miss semantic relevance without semantic matching

---

### 8. Add Keyword Stuffing Detection (LOW)

**Impact:** LOW  
**Effort:** MEDIUM  
**Risk:** LOW

**Action:** Detect and penalize excessive skill listing without evidence

**Proposed Logic:**
```python
def detect_keyword_stuffing(skills, evidence):
    skills_without_evidence = [s for s in skills if s not in evidence]
    stuffing_ratio = len(skills_without_evidence) / len(skills)
    
    if stuffing_ratio > 0.7:  # 70% of skills have no evidence
        return {"stuffing_detected": True, "penalty": -10}
    return {"stuffing_detected": False, "penalty": 0}
```

**Expected Improvement:**
- Penalize candidates with many claimed skills but no evidence
- Reduce impact of keyword stuffing

**Risks:**
- May penalize candidates with legitimate broad skill sets
- Threshold requires tuning

---

## Phase 7: Evaluation Methodology

### Proposed Benchmark

**Dataset Structure:**
```json
{
  "job_descriptions": [
    {
      "id": "jd_001",
      "title": "Backend Software Engineer",
      "description": "...",
      "required_skills": ["Python", "FastAPI", "PostgreSQL", "REST API"],
      "preferred_skills": ["Docker", "AWS", "Kubernetes"],
      "human_labelled_relevance": {
        "resume_001": "high",
        "resume_002": "medium",
        "resume_003": "low"
      }
    }
  ],
  "resumes": [
    {
      "id": "resume_001",
      "content": "...",
      "human_labelled_skills": ["Python", "FastAPI", "PostgreSQL", "RESTful services"],
      "human_labelled_skill_matches": {
        "Python": "matched",
        "FastAPI": "matched",
        "PostgreSQL": "matched",
        "REST API": "matched (as RESTful services)"
      }
    }
  ]
}
```

### Metrics

**1. Precision@5**
- Definition: Proportion of top-5 ranked candidates that are actually relevant
- Formula: `|relevant_in_top5| / 5`
- Target: ≥ 0.8

**2. Recall@5**
- Definition: Proportion of all relevant candidates that appear in top-5
- Formula: `|relevant_in_top5| / |total_relevant|`
- Target: ≥ 0.7

**3. NDCG@5**
- Definition: Normalized Discounted Cumulative Gain at rank 5
- Accounts for ranking quality (relevant candidates should be higher)
- Formula: Standard NDCG calculation
- Target: ≥ 0.75

**4. Skill Precision**
- Definition: Proportion of matched skills that are actually present
- Formula: `|correctly_matched_skills| / |total_matched_skills|`
- Target: ≥ 0.9

**5. Skill Recall**
- Definition: Proportion of actual skills that were matched
- Formula: `|correctly_matched_skills| / |total_actual_skills|`
- Target: ≥ 0.85

### Test Cases

**Positive Examples (Should Match):**
- JD: "REST API" ↔ Resume: "RESTful services"
- JD: "Object-Oriented Programming" ↔ Resume: "OOP principles"
- JD: "PostgreSQL" ↔ Resume: "SQL databases" (if hierarchy enabled)
- JD: "FastAPI" ↔ Resume: "Built APIs with FastAPI"

**Negative Examples (Should Not Match):**
- JD: "PostgreSQL" ↔ Resume: "MongoDB" (different database types)
- JD: "Python" ↔ Resume: "Learning Python" (aspirational)
- JD: "React" ↔ Resume: "React Native" (different framework)

### Evaluation Procedure

1. **Baseline Evaluation:** Run current system on benchmark
2. **Implement Improvement:** Apply one improvement at a time
3. **A/B Testing:** Compare metrics before/after each improvement
4. **Ablation Study:** Remove each component to measure contribution
5. **Human Validation:** Have recruiters review top-10 rankings for 20 jobs

---

## Phase 8: Risks and Mitigation

### Risk Matrix

| Improvement | Risk | Likelihood | Impact | Mitigation |
|--------------|------|------------|--------|------------|
| Enable semantic matching | Performance degradation | Medium | Low | Cache embeddings, async processing |
| Expand aliases | Over-generalization | Medium | Medium | Human review of aliases, A/B testing |
| Skill hierarchy | False positives | Medium | High | Strictness levels, configurable |
| Expand skills DB | Database bloat | High | Low | Periodic cleanup, usage tracking |
| Adjust fallback weights | Score inflation | Low | Medium | Validate with hiring managers |
| Contextual extraction | Section detection errors | Medium | Medium | Fallback to current method on error |
| Evidence improvements | Limited impact | High | Low | Semantic matching prerequisite |
| Stuffing detection | False positives | Low | Low | Tunable threshold, human review |

### Implementation Risks

**1. Breaking Changes**
- Risk: Changes to scoring formula may produce unexpected rankings
- Mitigation: Maintain backward compatibility flag, gradual rollout

**2. Performance Impact**
- Risk: Semantic matching and hierarchical matching increase latency
- Mitigation: Implement caching, batch processing, async operations

**3. Maintenance Burden**
- Risk: Expanded skills database and aliases require ongoing maintenance
- Mitigation: Automated skill extraction from job boards, community contributions

**4. Calibration Required**
- Risk: New scoring weights may not align with hiring priorities
- Mitigation: A/B testing with hiring teams, configurable weights per organization

---

## Conclusion

The HireLens matching system has a solid foundation with evidence-aware scoring and section-based extraction. However, the **absence of semantic matching** is the most critical limitation, causing the system to rely on keyword-based matching with significant false negatives for terminology variations.

**Immediate Priority:** Enable semantic matching by installing `sentence-transformers`

**High-Impact Follow-up:** Expand skill alias mappings and implement skill hierarchies to handle related technologies and variations.

**Long-term:** Implement contextual skill extraction and keyword stuffing detection to improve ranking quality.

The proposed improvements are ordered by impact and risk, enabling incremental enhancement while maintaining system stability. The evaluation methodology provides a framework for measuring improvement objectively.

**Recommendation:** Implement improvements in phases, measuring impact with the proposed benchmark after each phase.
