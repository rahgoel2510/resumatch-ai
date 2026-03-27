"""
Advanced ATS (Applicant Tracking System) scorer — 2026 edition.

Mirrors how modern ATS platforms (Greenhouse, Workday, Lever, Taleo) evaluate
resumes using AI-driven semantic analysis:

1. Role-Specific Skill Clustering — groups related skills (PyTorch + TensorFlow
   → "Deep Learning" cluster) so partial coverage still scores
2. Contextual Placement Weighting — keywords in Summary/Title get 3x weight,
   Skills section 2x, recent experience 1.5x, older roles 1x
3. Quantification Detection — $, %, large numbers, timeframes, multipliers
   scored as "impact signals" (like Greenhouse/Lever AI scoring)
4. Synonym & Acronym Expansion — bidirectional (GenAI ↔ Generative AI)
5. Skill Category Coverage — hard skills, certs, management, soft skills
6. Recency Weighting — recent roles contribute more than older ones
"""

import re
from dataclasses import dataclass, field


# ======================================================================
# SKILL CLUSTERS — related skills grouped so partial coverage counts
# Modern ATS groups these; having 2/4 in a cluster ≠ 0, it's ~50%
# ======================================================================
SKILL_CLUSTERS: dict[str, list[str]] = {
    "Deep Learning": [
        "pytorch", "tensorflow", "keras", "deep learning", "neural network",
        "neural networks", "cnn", "rnn", "lstm", "transformer",
    ],
    "Generative AI": [
        "genai", "generative ai", "llm", "large language model", "gpt",
        "chatgpt", "claude", "gemini", "langchain", "llamaindex",
        "prompt engineering", "fine-tuning", "rlhf", "llmops",
    ],
    "RAG & Vector Search": [
        "rag", "retrieval augmented generation", "vector database",
        "vector store", "embeddings", "faiss", "pinecone", "chromadb",
        "weaviate", "mcp", "model context protocol",
    ],
    "NLP": [
        "nlp", "natural language processing", "text mining", "sentiment analysis",
        "named entity recognition", "ner", "tokenization", "bert",
        "text classification", "spacy",
    ],
    "Cloud - AWS": [
        "aws", "amazon web services", "ec2", "s3", "lambda", "eks", "ecs",
        "sagemaker", "cloudformation", "dynamodb", "rds", "sns", "sqs",
        "cloudwatch", "iam", "vpc",
    ],
    "Cloud - GCP": [
        "gcp", "google cloud", "bigquery", "cloud run", "gke",
        "vertex ai", "cloud functions", "pub/sub",
    ],
    "Cloud - Azure": [
        "azure", "microsoft azure", "azure devops", "azure functions",
        "cosmos db", "azure ml", "azure cognitive",
    ],
    "Containers & Orchestration": [
        "docker", "kubernetes", "k8s", "container", "containerization",
        "helm", "istio", "service mesh", "ecs", "eks", "gke",
    ],
    "CI/CD & DevOps": [
        "ci/cd", "cicd", "jenkins", "github actions", "gitlab ci",
        "circleci", "argocd", "terraform", "ansible", "infrastructure as code",
        "iac", "devops", "sre", "site reliability",
    ],
    "Data Engineering": [
        "etl", "data pipeline", "airflow", "spark", "kafka", "hadoop",
        "data lake", "data warehouse", "snowflake", "databricks",
        "dbt", "data modeling", "batch processing", "stream processing",
    ],
    "Backend Development": [
        "python", "java", "golang", "node", "nodejs", "fastapi", "django",
        "flask", "spring", "spring boot", "express", "rest", "api",
        "graphql", "grpc", "microservices",
    ],
    "Frontend Development": [
        "react", "angular", "vue", "javascript", "typescript", "html",
        "css", "tailwind", "next.js", "nextjs", "webpack", "vite",
    ],
    "Databases": [
        "sql", "postgresql", "postgres", "mysql", "mongodb", "redis",
        "elasticsearch", "cassandra", "dynamodb", "nosql", "oracle db",
    ],
    "Agile & Project Management": [
        "agile", "scrum", "kanban", "safe", "jira", "confluence",
        "sprint planning", "retrospective", "backlog", "user stories",
        "story points",
    ],
    "Program & Portfolio Management": [
        "program management", "portfolio management", "roadmap",
        "okr", "kpi", "governance", "stakeholder management",
        "change management", "risk management", "budget management",
        "vendor management", "strategic planning", "p&l",
    ],
    "Leadership & People": [
        "leadership", "people management", "mentoring", "coaching",
        "team building", "cross-functional", "matrixed", "hiring",
        "performance review", "talent development",
    ],
}


# ======================================================================
# Synonym / acronym map — bidirectional expansion
# ======================================================================
SYNONYM_MAP: dict[str, list[str]] = {
    # AI / ML
    "genai": ["generative ai", "gen ai", "generative artificial intelligence"],
    "llm": ["large language model", "large language models"],
    "llmops": ["llm ops", "llm operations"],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
    "mcp": ["model context protocol"],
    "nlp": ["natural language processing"],
    "ml": ["machine learning"],
    "ai": ["artificial intelligence"],
    "dl": ["deep learning"],
    "transformer": ["transformer models", "transformers", "attention model"],
    "gpt": ["generative pre-trained transformer"],
    "bert": ["bidirectional encoder representations"],
    "langchain": ["lang chain"],
    "vector database": ["vector db", "vectordb", "vector store", "vectorstore"],
    # Cloud
    "aws": ["amazon web services"],
    "gcp": ["google cloud platform", "google cloud"],
    "azure": ["microsoft azure"],
    "ec2": ["elastic compute cloud"],
    "s3": ["simple storage service"],
    "lambda": ["aws lambda", "serverless functions"],
    "eks": ["elastic kubernetes service"],
    "ecs": ["elastic container service"],
    # DevOps
    "ci/cd": ["cicd", "continuous integration", "continuous deployment", "continuous delivery"],
    "k8s": ["kubernetes"],
    "docker": ["containerization", "containers"],
    "terraform": ["infrastructure as code", "iac"],
    "iac": ["infrastructure as code"],
    # Agile
    "agile": ["agile methodology", "agile development"],
    "scrum": ["scrum methodology", "scrum framework"],
    "kanban": ["kanban board"],
    "jira": ["atlassian jira"],
    # Programming
    "python": ["python3", "python 3"],
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "react": ["reactjs", "react.js"],
    "node": ["nodejs", "node.js"],
    "fastapi": ["fast api"],
    "django": ["django framework"],
    # Data
    "sql": ["structured query language"],
    "nosql": ["no-sql", "non-relational"],
    "postgresql": ["postgres"],
    "mongodb": ["mongo"],
    "redis": ["redis cache"],
    "etl": ["extract transform load"],
    # Management
    "pmp": ["project management professional"],
    "pgmp": ["program management professional"],
    "csm": ["certified scrum master"],
    "safe": ["scaled agile framework"],
    "okr": ["objectives and key results", "okrs"],
    "kpi": ["key performance indicator", "key performance indicators", "kpis"],
    "roi": ["return on investment"],
    "p&l": ["profit and loss", "profit & loss"],
    "stakeholder management": ["stakeholder engagement"],
    "cross-functional": ["cross functional", "matrixed"],
    "program management": ["programme management"],
    "change management": ["organizational change"],
}


# ======================================================================
# Skill categories
# ======================================================================
HARD_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "node", "sql",
    "nosql", "aws", "gcp", "azure", "docker", "kubernetes", "k8s",
    "terraform", "ci/cd", "git", "linux", "api", "rest", "graphql",
    "microservices", "kafka", "redis", "postgresql", "mongodb", "etl",
    "spark", "hadoop", "airflow", "jenkins", "github", "gitlab",
    "fastapi", "django", "flask", "spring", "angular", "vue",
    "ml", "ai", "nlp", "genai", "llm", "rag", "mcp", "langchain",
    "pytorch", "tensorflow", "transformer", "bert", "gpt", "llmops",
    "vector database", "embeddings", "fine-tuning",
    "tableau", "power bi", "looker", "snowflake", "databricks",
    "bigquery", "redshift",
}

CERTIFICATIONS = {
    "pmp", "pgmp", "csm", "safe", "aws solutions architect",
    "aws certified", "azure certified", "gcp certified",
    "itil", "togaf", "six sigma", "cissp", "cka",
}

MANAGEMENT_SKILLS = {
    "program management", "project management", "people management",
    "stakeholder management", "change management", "risk management",
    "budget management", "vendor management", "portfolio management",
    "agile", "scrum", "kanban", "okr", "kpi", "roadmap",
    "cross-functional", "leadership", "mentoring", "coaching",
    "governance", "strategic planning",
}

SOFT_SKILLS = {
    "communication", "collaboration", "problem solving", "critical thinking",
    "adaptability", "teamwork", "negotiation", "presentation",
    "decision making", "conflict resolution", "time management",
    "analytical", "creative", "innovative", "detail oriented",
}


# ======================================================================
# Resume section detection — enhanced with recency awareness
# ======================================================================
_SUMMARY_PATTERNS = [
    r"(?i)(summary|profile|objective|about me|professional summary|overview)",
]
_TITLE_PATTERNS = [
    r"(?i)(title|designation|current role|headline)",
]
_EXPERIENCE_PATTERNS = [
    r"(?i)(experience|employment|work history|professional experience|career)",
]
_SKILLS_PATTERNS = [
    r"(?i)(skills|technical skills|core competencies|technologies|tools|expertise)",
]
_EDUCATION_PATTERNS = [
    r"(?i)(education|academic|degree|university|certification|certifications)",
]

ALL_SECTION_PATTERNS = (
    _SUMMARY_PATTERNS + _TITLE_PATTERNS + _EXPERIENCE_PATTERNS
    + _SKILLS_PATTERNS + _EDUCATION_PATTERNS
)


def _extract_section(text: str, patterns: list[str]) -> str:
    """Extract text between a section header and the next section."""
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            start = match.end()
            remaining = text[start:]
            end = len(remaining)
            for hdr_pat in ALL_SECTION_PATTERNS:
                if hdr_pat in patterns:
                    continue
                next_match = re.search(hdr_pat, remaining)
                if next_match and next_match.start() < end:
                    end = next_match.start()
            return remaining[:end].strip()
    return ""


def _extract_recent_experience(text: str) -> str:
    """Extract the first ~40% of the experience section (most recent roles)."""
    exp = _extract_section(text, _EXPERIENCE_PATTERNS)
    if not exp:
        return ""
    cutoff = int(len(exp) * 0.4)
    return exp[:cutoff]


# ======================================================================
# Keyword extraction
# ======================================================================
_SHORT_TECH_TERMS = {
    "ai", "ml", "dl", "ci", "cd", "js", "ts", "go", "r", "c#",
    "c++", "aws", "gcp", "sql", "api", "etl", "rag", "mcp",
    "llm", "nlp", "k8s", "git", "okr", "kpi", "roi", "pmp",
    "ecs", "eks", "ec2", "s3", "iac", "sre", "vpc", "iam",
    "sns", "sqs", "rds", "cnn", "rnn", "ner", "dbt",
}


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords including multi-word terms."""
    text_lower = text.lower()
    keywords = set()

    # Single words (4+ chars)
    keywords.update(re.findall(r"\b[a-zA-Z+#/.]{4,}\b", text_lower))

    # Known multi-word terms from all sources
    all_terms = set(SYNONYM_MAP.keys())
    for synonyms in SYNONYM_MAP.values():
        all_terms.update(synonyms)
    all_terms.update(HARD_SKILLS)
    all_terms.update(CERTIFICATIONS)
    all_terms.update(MANAGEMENT_SKILLS)
    all_terms.update(SOFT_SKILLS)
    # Cluster terms
    for terms in SKILL_CLUSTERS.values():
        all_terms.update(terms)

    for term in all_terms:
        if term.lower() in text_lower:
            keywords.add(term.lower())

    # Short tech terms
    for term in _SHORT_TECH_TERMS:
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            keywords.add(term)

    return keywords


def _expand_with_synonyms(keywords: set[str]) -> set[str]:
    """Expand a keyword set with known synonyms/acronyms."""
    expanded = set(keywords)
    for key, synonyms in SYNONYM_MAP.items():
        key_l = key.lower()
        syns_l = [s.lower() for s in synonyms]
        if key_l in keywords or any(s in keywords for s in syns_l):
            expanded.add(key_l)
            expanded.update(syns_l)
    return expanded


# ======================================================================
# Quantification detection — enhanced
# ======================================================================
def _score_quantification(text: str) -> dict:
    """
    Detect quantified achievements: $, %, large numbers, timeframes,
    multipliers, and result-oriented phrases.
    """
    money = re.findall(r"\$[\d,.]+\s*[MBKmk]?\b", text)
    percents = re.findall(r"\d+\.?\d*\s*%", text)
    big_numbers = re.findall(r"\b\d{1,3}(?:,\d{3})+\+?\b", text)
    multipliers = re.findall(r"\b\d+\.?\d*[xX]\b", text)
    timeframes = re.findall(r"\b\d+\+?\s*(?:years?|months?|weeks?|days?|quarters?)\b", text, re.I)
    # Result phrases like "reduced by", "increased to", "saved", "delivered"
    result_verbs = re.findall(
        r"\b(?:reduced|increased|improved|saved|delivered|generated|achieved|"
        r"grew|accelerated|optimized|eliminated|resolved|automated|scaled|"
        r"launched|migrated|consolidated)\b",
        text, re.I,
    )

    all_examples = money + percents + big_numbers + multipliers + timeframes
    unique_examples = list(dict.fromkeys(all_examples))  # dedupe preserving order

    # Scoring: each type contributes, capped at 15
    raw = (
        len(money) * 4
        + len(percents) * 3
        + len(big_numbers) * 2
        + len(multipliers) * 3
        + len(timeframes) * 1
        + min(len(result_verbs), 5) * 1  # cap verb contribution
    )
    score = min(raw, 15)

    return {
        "count": len(all_examples),
        "score": score,
        "examples": unique_examples[:8],
        "result_verbs_count": len(result_verbs),
    }


# ======================================================================
# Skill cluster scoring
# ======================================================================
def _score_skill_clusters(resume_text: str, jd_text: str) -> dict:
    """
    For each skill cluster relevant to the JD, compute coverage %.
    Returns per-cluster breakdown and an average score.
    """
    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()

    cluster_results = {}
    relevant_clusters = 0
    total_coverage = 0

    for cluster_name, terms in SKILL_CLUSTERS.items():
        # Which terms from this cluster appear in the JD?
        jd_terms = [t for t in terms if t in jd_lower]
        if not jd_terms:
            continue  # cluster not relevant to this JD

        relevant_clusters += 1
        # Check resume coverage (with synonym expansion)
        resume_hits = []
        resume_misses = []
        for t in jd_terms:
            found = t in resume_lower
            if not found:
                # Check synonyms
                expanded = {t}
                if t in SYNONYM_MAP:
                    expanded.update(s.lower() for s in SYNONYM_MAP[t])
                found = any(e in resume_lower for e in expanded)
            if found:
                resume_hits.append(t)
            else:
                resume_misses.append(t)

        coverage = round(len(resume_hits) / len(jd_terms) * 100) if jd_terms else 0
        total_coverage += coverage

        cluster_results[cluster_name] = {
            "required": len(jd_terms),
            "matched": len(resume_hits),
            "coverage": min(coverage, 100),
            "matched_terms": resume_hits[:5],
            "missing_terms": resume_misses[:5],
        }

    avg_coverage = round(total_coverage / relevant_clusters) if relevant_clusters > 0 else 0

    return {
        "clusters": cluster_results,
        "relevant_cluster_count": relevant_clusters,
        "average_coverage": avg_coverage,
    }


# ======================================================================
# Stop words
# ======================================================================
_STOP_WORDS = {
    "the", "and", "for", "are", "with", "you", "your", "our", "will",
    "this", "that", "from", "have", "has", "been", "being", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "such", "each", "which", "their", "there", "these",
    "those", "other", "than", "then", "also", "just", "more", "some",
    "can", "could", "would", "should", "may", "might", "must", "shall",
    "not", "but", "what", "when", "where", "who", "how", "all", "any",
    "able", "accepted", "access", "account", "accounts", "activities",
    "additional", "ago", "apply", "based", "behalf", "both", "click",
    "come", "company", "complete", "comprehensive", "creating", "day",
    "does", "don", "eligible", "employees", "employment", "ensure",
    "every", "federal", "full", "global", "here", "including",
    "information", "join", "know", "law", "learn", "live", "local",
    "making", "markets", "new", "now", "offer", "one", "only", "open",
    "opportunity", "part", "pay", "percent", "person", "please",
    "provide", "provides", "providing", "regardless", "report",
    "request", "required", "role", "services", "share", "simple",
    "state", "status", "submit", "support", "take", "team", "time",
    "travel", "type", "use", "using", "value", "visit", "way", "well",
    "work", "working", "years", "yet",
}


# ======================================================================
# Result dataclass
# ======================================================================
@dataclass
class ATSResult:
    """Comprehensive ATS scoring result."""
    overall_score: int = 0

    # Sub-scores
    keyword_score: int = 0
    contextual_placement_score: int = 0
    quantification_score: int = 0
    cluster_score: int = 0
    category_score: int = 0

    # Detailed breakdowns
    skill_category_breakdown: dict = field(default_factory=dict)
    skill_cluster_breakdown: dict = field(default_factory=dict)

    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    quantification_examples: list[str] = field(default_factory=list)
    result_verbs_count: int = 0

    # Reasoning for APPLY/SKIP
    strengths: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    verdict: str = ""
    verdict_reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "keyword_score": self.keyword_score,
            "contextual_placement_score": self.contextual_placement_score,
            "quantification_score": self.quantification_score,
            "cluster_score": self.cluster_score,
            "category_score": self.category_score,
            "skill_categories": self.skill_category_breakdown,
            "skill_clusters": self.skill_cluster_breakdown,
            "matched_keywords": self.matched_keywords[:25],
            "missing_keywords": self.missing_keywords[:15],
            "quantification_examples": self.quantification_examples,
            "result_verbs_count": self.result_verbs_count,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "verdict": self.verdict,
            "verdict_reasoning": self.verdict_reasoning,
        }


# ======================================================================
# Main scoring function
# ======================================================================
def compute_ats_score(resume_text: str, jd_text: str) -> ATSResult:
    """
    Compute a comprehensive ATS score (0-100) using 2026 scoring signals.

    Weights:
      - Keyword match (synonym-expanded):       25%
      - Contextual placement (section weights):  20%
      - Skill cluster coverage:                  20%
      - Skill category coverage:                 15%
      - Quantified achievements:                 10%
      - Recency bonus:                           10%
    """
    result = ATSResult()

    # --- 1. Keyword match with synonym expansion (25%) ---
    jd_keywords = _extract_keywords(jd_text) - _STOP_WORDS
    resume_keywords = _extract_keywords(resume_text) - _STOP_WORDS

    jd_expanded = _expand_with_synonyms(jd_keywords)
    resume_expanded = _expand_with_synonyms(resume_keywords)

    if not jd_expanded:
        return result

    matched = sorted(jd_expanded & resume_expanded)
    missing = sorted(jd_expanded - resume_expanded)

    result.keyword_score = round(min(len(matched) / len(jd_expanded) * 100, 100))
    result.matched_keywords = matched
    result.missing_keywords = missing

    # --- 2. Contextual placement scoring (20%) ---
    # Summary/Title: 3x, Skills: 2x, Recent experience: 1.5x, Rest: 1x
    summary = _extract_section(resume_text, _SUMMARY_PATTERNS)
    title_text = _extract_section(resume_text, _TITLE_PATTERNS)
    skills_section = _extract_section(resume_text, _SKILLS_PATTERNS)
    recent_exp = _extract_recent_experience(resume_text)
    full_exp = _extract_section(resume_text, _EXPERIENCE_PATTERNS)

    summary_kw = _expand_with_synonyms(_extract_keywords(summary + " " + title_text) - _STOP_WORDS)
    skills_kw = _expand_with_synonyms(_extract_keywords(skills_section) - _STOP_WORDS)
    recent_kw = _expand_with_synonyms(_extract_keywords(recent_exp) - _STOP_WORDS)
    full_kw = _expand_with_synonyms(_extract_keywords(full_exp) - _STOP_WORDS)

    weighted_hits = 0.0
    weighted_total = 0.0
    for kw in jd_expanded:
        if kw in summary_kw:
            weighted_hits += 3.0
        elif kw in skills_kw:
            weighted_hits += 2.0
        elif kw in recent_kw:
            weighted_hits += 1.5
        elif kw in full_kw:
            weighted_hits += 1.0
        elif kw in resume_expanded:
            weighted_hits += 0.5
        weighted_total += 3.0  # max possible per keyword

    result.contextual_placement_score = round(
        min(weighted_hits / weighted_total * 100, 100)
    ) if weighted_total > 0 else 0

    # --- 3. Skill cluster coverage (20%) ---
    clusters = _score_skill_clusters(resume_text, jd_text)
    result.cluster_score = clusters["average_coverage"]
    result.skill_cluster_breakdown = clusters["clusters"]

    # --- 4. Skill category coverage (15%) ---
    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()

    categories = {
        "hard_skills": HARD_SKILLS,
        "certifications": CERTIFICATIONS,
        "management": MANAGEMENT_SKILLS,
        "soft_skills": SOFT_SKILLS,
    }
    cat_breakdown = {}
    cat_score_total = 0

    for cat_name, cat_terms in categories.items():
        jd_has = {t for t in cat_terms if t in jd_lower}
        if not jd_has:
            cat_breakdown[cat_name] = {"required": 0, "matched": 0, "pct": 100}
            cat_score_total += 100
            continue
        resume_has = set()
        for t in jd_has:
            expanded = {t}
            if t in SYNONYM_MAP:
                expanded.update(s.lower() for s in SYNONYM_MAP[t])
            if any(e in resume_lower for e in expanded):
                resume_has.add(t)

        pct = round(len(resume_has) / len(jd_has) * 100)
        cat_breakdown[cat_name] = {
            "required": len(jd_has),
            "matched": len(resume_has),
            "pct": min(pct, 100),
            "missing": sorted(jd_has - resume_has)[:5],
        }
        cat_score_total += pct

    avg_cat = cat_score_total / len(categories) if categories else 0
    result.category_score = round(avg_cat)
    result.skill_category_breakdown = cat_breakdown

    # --- 5. Quantification (10%) ---
    quant = _score_quantification(resume_text)
    result.quantification_score = quant["score"]
    result.quantification_examples = quant["examples"]
    result.result_verbs_count = quant["result_verbs_count"]

    # --- 6. Recency bonus (10%) ---
    # If recent experience has good keyword coverage, bonus up to 10
    recent_match = len(recent_kw & jd_expanded)
    recency_pct = min(recent_match / max(len(jd_expanded), 1) * 100, 100)

    # --- Final weighted score ---
    result.overall_score = round(
        result.keyword_score * 0.25
        + result.contextual_placement_score * 0.20
        + result.cluster_score * 0.20
        + result.category_score * 0.15
        + result.quantification_score * (100 / 15) * 0.10
        + recency_pct * 0.10
    )
    result.overall_score = min(result.overall_score, 100)

    # --- Build strengths / gaps / verdict ---
    result.strengths, result.gaps = _build_reasoning(result, clusters)
    result.verdict, result.verdict_reasoning = _determine_verdict(result)

    return result


# ======================================================================
# Reasoning builder
# ======================================================================
def _build_reasoning(result: ATSResult, clusters: dict) -> tuple[list[str], list[str]]:
    """Build human-readable strengths and gaps lists."""
    strengths = []
    gaps = []

    # Keyword coverage
    if result.keyword_score >= 70:
        strengths.append(f"Strong keyword match ({result.keyword_score}%) — resume covers most JD requirements")
    elif result.keyword_score >= 45:
        strengths.append(f"Moderate keyword match ({result.keyword_score}%)")
    else:
        gaps.append(f"Low keyword overlap ({result.keyword_score}%) — many JD terms missing from resume")

    # Contextual placement
    if result.contextual_placement_score >= 60:
        strengths.append("Key skills appear in Summary/Skills sections (high ATS visibility)")
    else:
        gaps.append("Important keywords are buried in older roles — move them to Summary or Skills section")

    # Clusters
    for cname, cdata in clusters.get("clusters", {}).items():
        cov = cdata.get("coverage", 0)
        if cov >= 70:
            strengths.append(f"{cname}: strong coverage ({cov}%)")
        elif cov >= 40:
            pass  # neutral
        elif cov > 0:
            missing = ", ".join(cdata.get("missing_terms", [])[:3])
            gaps.append(f"{cname}: weak coverage ({cov}%) — missing: {missing}")

    # Quantification
    if result.quantification_score >= 10:
        strengths.append(f"Well-quantified achievements ({len(result.quantification_examples)} metrics found)")
    elif result.quantification_score >= 5:
        strengths.append("Some quantified results present")
    else:
        gaps.append("Few quantified achievements — add $, %, numbers to bullet points")

    # Categories
    for cat_name, cat_data in result.skill_category_breakdown.items():
        if cat_data.get("required", 0) > 0 and cat_data.get("pct", 0) < 40:
            missing = ", ".join(cat_data.get("missing", [])[:3])
            label = cat_name.replace("_", " ").title()
            gaps.append(f"{label}: low match — missing: {missing}")

    return strengths, gaps


def _determine_verdict(result: ATSResult) -> tuple[str, str]:
    """Determine APPLY / MAYBE / SKIP with reasoning."""
    score = result.overall_score

    if score >= 65:
        verdict = "STRONG APPLY"
        reasoning = (
            f"Overall ATS score of {score}% indicates a strong match. "
            f"Your resume aligns well with the job requirements. "
            f"Focus on addressing any minor gaps in your cover letter."
        )
    elif score >= 50:
        verdict = "APPLY"
        reasoning = (
            f"ATS score of {score}% shows a reasonable match. "
            f"You meet core requirements but have some gaps. "
            f"Consider tailoring your resume to add missing keywords before applying."
        )
    elif score >= 35:
        verdict = "MAYBE — TAILOR FIRST"
        reasoning = (
            f"ATS score of {score}% is below typical screening thresholds. "
            f"You have relevant experience but the resume needs keyword optimization. "
            f"Add missing skills to your Summary and Skills sections before applying."
        )
    else:
        verdict = "SKIP"
        reasoning = (
            f"ATS score of {score}% suggests a significant mismatch. "
            f"The role requires skills/experience not well represented in your resume. "
            f"Consider roles more aligned with your current profile."
        )

    return verdict, reasoning
