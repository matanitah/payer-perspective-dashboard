"""
Tri-state (NY / CT / NJ) knowledge base.

Contains:
  - Major providers by state
  - Major payers operating in the region
  - State-specific regulatory context
  - Payer-perspective inference prompts for Cigna, United, Anthem
  - RSS/scrape sources including tri-state–specific outlets
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────
# PROVIDERS BY STATE
# ─────────────────────────────────────────────────────────────────────

PROVIDERS: dict[str, list[dict]] = {
    "NY": [
        {"name": "NewYork-Presbyterian", "aliases": ["nyp", "newyork-presbyterian", "ny presbyterian"], "type": "Academic", "beds": 2600, "notes": "Columbia & Weill Cornell affiliate. Largest not-for-profit hospital in the US."},
        {"name": "Mount Sinai Health System", "aliases": ["mount sinai", "sinai"], "type": "Academic", "beds": 3800, "notes": "8 hospitals, 9000+ physicians. Active Anthem dispute resolved Apr 2026."},
        {"name": "NYU Langone Health", "aliases": ["nyu langone", "nyu"], "type": "Academic", "beds": 1900, "notes": "Rapid expansion into Long Island and Brooklyn."},
        {"name": "Northwell Health", "aliases": ["northwell"], "type": "System", "beds": 4500, "notes": "Largest private employer in NY. 21 hospitals spanning NYC, LI, Westchester."},
        {"name": "Montefiore Health System", "aliases": ["montefiore"], "type": "Academic", "beds": 2800, "notes": "Albert Einstein affiliate. Dominant in the Bronx and lower Hudson Valley."},
        {"name": "Memorial Sloan Kettering", "aliases": ["msk", "memorial sloan", "sloan kettering"], "type": "Specialty", "beds": 514, "notes": "Top cancer center. UHC MA contract dispute mid-2025, resolved."},
        {"name": "NYC Health + Hospitals", "aliases": ["h+h", "health + hospitals", "nyc hhc"], "type": "Public", "beds": 4400, "notes": "Largest public health system in the US. Operates MetroPlusHealth MCO."},
        {"name": "Maimonides Medical Center", "aliases": ["maimonides"], "type": "Community", "beds": 711, "notes": "Largest hospital in Brooklyn."},
        {"name": "Catholic Health (LI)", "aliases": ["catholic health long island"], "type": "System", "beds": 1500, "notes": "6 hospitals on Long Island."},
    ],
    "CT": [
        {"name": "Yale New Haven Health System", "aliases": ["ynhhs", "yale new haven", "ynhh"], "type": "Academic", "beds": 2600, "notes": "11 hospitals. Largest CT system. Acquired Prospect hospitals 2024-25."},
        {"name": "Hartford HealthCare", "aliases": ["hartford healthcare", "hhc ct"], "type": "System", "beds": 2400, "notes": "10 hospitals. Antitrust lawsuit by St. Francis (settled Jan 2025)."},
        {"name": "Nuvance Health", "aliases": ["nuvance"], "type": "System", "beds": 1200, "notes": "7 hospitals spanning western CT and NY Hudson Valley. Cross-state network."},
        {"name": "Trinity Health of New England", "aliases": ["trinity health ne", "saint francis ct"], "type": "System", "beds": 900, "notes": "Includes Saint Francis Hospital, largest Catholic hospital in New England."},
        {"name": "Stamford Health", "aliases": ["stamford health", "stamford hospital"], "type": "Community", "beds": 305, "notes": "Columbia University affiliate. Serves lower Fairfield County."},
        {"name": "Middlesex Health", "aliases": ["middlesex health"], "type": "Community", "beds": 250, "notes": "Part of Mayo Clinic Care Network."},
    ],
    "NJ": [
        {"name": "RWJBarnabas Health", "aliases": ["rwjbarnabas", "rwjbh", "barnabas"], "type": "System", "beds": 5066, "notes": "16 hospitals. Highest NPR in NJ (~$6.5B). Rutgers affiliation."},
        {"name": "Hackensack Meridian Health", "aliases": ["hackensack meridian", "hmh"], "type": "Academic", "beds": 4520, "notes": "16 hospitals. Hackensack Meridian School of Medicine. Largest NJ system by facilities."},
        {"name": "Atlantic Health System", "aliases": ["atlantic health"], "type": "System", "beds": 1800, "notes": "8 hospitals. Morristown #2 and Overlook #3 in NJ rankings."},
        {"name": "Virtua Health", "aliases": ["virtua"], "type": "System", "beds": 1600, "notes": "5 hospitals in South Jersey. Strong community presence."},
        {"name": "Valley Health System", "aliases": ["valley health nj", "valley hospital"], "type": "Community", "beds": 451, "notes": "New facility opened 2024. Consistently top-100 nationally."},
        {"name": "Cooper University Health Care", "aliases": ["cooper health", "cooper university"], "type": "Academic", "beds": 635, "notes": "MD Anderson affiliate. Level I trauma in South Jersey."},
        {"name": "St. Joseph's Health", "aliases": ["st josephs health nj"], "type": "System", "beds": 700, "notes": "2 hospitals in Paterson area. Serves vulnerable populations."},
        {"name": "Englewood Health", "aliases": ["englewood health", "englewood hospital"], "type": "Community", "beds": 531, "notes": "FTC blocked HMH merger in 2022. Independent."},
    ],
}


# ─────────────────────────────────────────────────────────────────────
# PAYERS OPERATING IN TRI-STATE
# ─────────────────────────────────────────────────────────────────────

PAYERS: dict[str, dict] = {
    "UnitedHealthcare": {
        "aliases": ["uhc", "unitedhealthcare", "united", "uhg", "optum", "oxford health"],
        "segments": ["Commercial", "Medicare Advantage", "Medicaid (Community Plan)", "Essential Plan (NY)"],
        "notes": "Largest national insurer. Oxford subsidiary dominant in NYC small group. Projecting 1.3M MA member loss in 2026. Active NYP MA dispute.",
        "states": ["NY", "CT", "NJ"],
    },
    "Anthem / Elevance (Empire BCBS)": {
        "aliases": ["anthem", "empire bcbs", "empire blue cross", "elevance", "anthem bcbs"],
        "segments": ["Commercial", "Medicare Advantage", "Medicaid"],
        "notes": "Empire BCBS brand in NY. Mount Sinai dispute (Jan–Apr 2026) most visible. Blue Cross cross-licensing adds payment processing complexity.",
        "states": ["NY", "CT", "NJ"],
    },
    "Cigna / Evernorth": {
        "aliases": ["cigna", "evernorth"],
        "segments": ["Commercial", "Medicare Advantage"],
        "notes": "Strong in employer-sponsored market. Evernorth PBM/services arm. Less Medicaid presence in tri-state. Merged with Health Care Service Corp products.",
        "states": ["NY", "CT", "NJ"],
    },
    "Aetna (CVS Health)": {
        "aliases": ["aetna", "cvs health"],
        "segments": ["Commercial", "Medicare Advantage", "Medicaid"],
        "notes": "CVS ownership creates vertical integration (MinuteClinic, Caremark PBM). Active in CT market (HQ in Hartford area historically).",
        "states": ["NY", "CT", "NJ"],
    },
    "Humana": {
        "aliases": ["humana"],
        "segments": ["Medicare Advantage"],
        "notes": "Primarily MA-focused. Multiple system terminations nationally in 2025-26.",
        "states": ["NY", "NJ"],
    },
    "Healthfirst": {
        "aliases": ["healthfirst"],
        "segments": ["Medicaid", "Essential Plan", "Medicare Advantage", "Commercial (QHP)"],
        "notes": "NYC-area nonprofit. Top MA HMO enrollment in Manhattan. Strong Medicaid managed care presence.",
        "states": ["NY"],
    },
    "EmblemHealth": {
        "aliases": ["emblemhealth", "ghi", "hip"],
        "segments": ["Commercial", "Medicaid", "Medicare Advantage", "Essential Plan"],
        "notes": "GHI + HIP merger. Administers NYCE PPO for NYC municipal employees (with UHC). Requested 12.7% premium increase for FY2026.",
        "states": ["NY"],
    },
    "Fidelis Care (Centene)": {
        "aliases": ["fidelis", "fidelis care", "centene"],
        "segments": ["Medicaid", "Essential Plan", "Child Health Plus", "Medicare Advantage (via WellCare)"],
        "notes": "Centene subsidiary. Major Medicaid MCO in NY. Acquired WellCare.",
        "states": ["NY"],
    },
    "MetroPlusHealth": {
        "aliases": ["metroplus", "metroplushealth"],
        "segments": ["Medicaid", "Essential Plan", "Medicare Advantage"],
        "notes": "NYC H+H subsidiary. Network includes Mount Sinai, NYU Langone, H+H hospitals. Unique provider-owned MCO.",
        "states": ["NY"],
    },
    "Horizon BCBS NJ": {
        "aliases": ["horizon", "horizon bcbs"],
        "segments": ["Commercial", "Medicare Advantage", "Medicaid"],
        "notes": "Dominant NJ insurer. Only NJ BCBS plan. Strong negotiating position due to market share.",
        "states": ["NJ"],
    },
    "AmeriHealth NJ": {
        "aliases": ["amerihealth"],
        "segments": ["Commercial", "Medicaid"],
        "notes": "IBC subsidiary. Active in NJ Medicaid managed care.",
        "states": ["NJ"],
    },
    "ConnectiCare": {
        "aliases": ["connecticare"],
        "segments": ["Commercial", "Medicare Advantage"],
        "notes": "EmblemHealth subsidiary operating in CT. ACA marketplace presence.",
        "states": ["CT"],
    },
}


# ─────────────────────────────────────────────────────────────────────
# STATE REGULATORY CONTEXT
# ─────────────────────────────────────────────────────────────────────

STATE_REGULATIONS: dict[str, dict] = {
    "NY": {
        "summary": "New York has among the most regulated insurance markets in the US.",
        "key_rules": [
            "Community rating: Premiums cannot vary by health status in individual/small group.",
            "Network adequacy: DFS requires plans to maintain adequate networks; losing a major provider may violate standards.",
            "Any Willing Provider: For certain plan types, plans must accept providers who agree to terms.",
            "Managed Care Model Contract: Medicaid MCOs must follow state-mandated rate floors and pass-through requirements.",
            "Essential Plan (BHP): State-set rates for 138-250% FPL population. Providers have minimal negotiation room.",
            "Hospital Price Transparency: Machine-readable files required since 2021. NY AG actively enforces.",
            "Certificate of Need: Required for new facilities, service expansions, and major capital projects.",
            "Surprise Billing: NY had state surprise billing law before federal NSA. State process applies to fully-insured plans.",
            "Medicaid rates: Historically 30-40% below Medicare. $50M physician rate investment in 2026 narrows gap slightly.",
            "MCO Provider Tax: New tax generating ~$1.4B annually funds provider rate increases.",
        ],
        "regulators": [
            "NY Department of Financial Services (DFS) — insurance regulation, rate review",
            "NY Department of Health (DOH) — Medicaid, hospital licensing, CON",
            "NY State of Health — ACA marketplace, Essential Plan administration",
            "Office of the Medicaid Inspector General (OMIG) — fraud/abuse",
        ],
    },
    "CT": {
        "summary": "Connecticut has been actively addressing hospital consolidation through regulatory tools.",
        "key_rules": [
            "Office of Health Strategy (OHS): Oversees Certificate of Need, cost growth benchmarks, hospital reporting.",
            "Cost Growth Benchmark: CT sets targets for healthcare cost growth; providers and insurers face scrutiny if exceeded.",
            "Certificate of Need: Required for hospital mergers, service changes, major capital. OHS reviews.",
            "Statewide Health Care Facility and Services Plan: Updated March 2025. Blueprint for service planning.",
            "Antitrust enforcement: AG active. Hartford HealthCare antitrust lawsuit (settled Jan 2025) signals scrutiny.",
            "Community benefit: Strong nonprofit hospital requirements. Reports filed with OHS.",
            "All-Payer Claims Database: CT operates APCD for cost and utilization analysis.",
            "Network adequacy: CT Insurance Department reviews network adequacy for QHP and commercial plans.",
            "Medicaid: Administered by Department of Social Services (DSS). Managed care via HUSKY Health program.",
        ],
        "regulators": [
            "CT Office of Health Strategy (OHS) — CON, cost benchmarks, planning",
            "CT Insurance Department — rate review, network adequacy",
            "CT Department of Social Services (DSS) — Medicaid (HUSKY Health)",
            "CT Attorney General — antitrust, consumer protection",
        ],
    },
    "NJ": {
        "summary": "New Jersey's market is dominated by two mega-systems (HMH, RWJBH) and one dominant insurer (Horizon BCBS).",
        "key_rules": [
            "Out-of-Network Consumer Protection Act: NJ's surprise billing law (predates federal NSA). Arbitration for OON disputes.",
            "Certificate of Need: NJ DOH reviews hospital expansions and new services.",
            "Network adequacy: DOBI sets minimum network standards. Narrow networks face scrutiny.",
            "Rate review: DOBI reviews individual and small group rate filings.",
            "Charity care: NJ requires hospitals to provide charity care; state partially subsidizes through Charity Care Fund.",
            "Graduate Medical Education: State funding for teaching hospitals; affects negotiating position of academic centers.",
            "Health Care Quality Institute: Independent watchdog monitoring quality and cost.",
            "Medicaid Managed Care: Managed by Division of Medical Assistance and Health Services (DMAHS).",
            "Provider tax: NJ hospital fee funds Medicaid supplemental payments.",
            "Consolidation: FTC blocked HMH-Englewood merger (2022). Signals limits on further horizontal consolidation.",
        ],
        "regulators": [
            "NJ Department of Banking and Insurance (DOBI) — insurance regulation, rate review",
            "NJ Department of Health (DOH) — hospital licensing, CON, charity care",
            "NJ Division of Medical Assistance and Health Services (DMAHS) — Medicaid",
            "Federal Trade Commission — antitrust (active in NJ market)",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────
# PAYER-PERSPECTIVE INFERENCE PROMPTS
# ─────────────────────────────────────────────────────────────────────
# These are used by the analyzer to generate inferred payer strategies
# from the news, rather than relying on payer press releases.

PAYER_INFERENCE_PROMPTS: dict[str, str] = {
    "UnitedHealthcare": """\
You are simulating the strategic perspective of UnitedHealthcare's managed care \
contracting team for the NY/CT/NJ tri-state region. UHC is the largest national \
insurer. Key context:
- UHC projects losing 1.3-1.4M MA members nationally in 2026 due to competition.
- Oxford (UHC subsidiary) is the largest small-group insurer in NYC/Long Island.
- Active MA contract dispute with NewYork-Presbyterian (May 1, 2026 deadline).
- UHC Community Plan operates Medicaid and Essential Plan products in NY.
- Optum (UHG subsidiary) owns physician practices, creating vertical integration.
- CMS proposed only 0.9% MA rate increase for 2027, compressing margins further.

Given the news article below, infer what UHC's contracting team is likely thinking, \
what leverage they have or lack, and what moves they would make. Be specific about \
which product lines (commercial, MA, Medicaid) and which provider relationships \
are most affected. Consider how Optum's provider ownership creates conflicts.
""",
    "Anthem / Elevance (Empire BCBS)": """\
You are simulating the strategic perspective of Anthem Blue Cross Blue Shield \
(Empire BCBS in New York) contracting leadership for the tri-state region. Key context:
- Mount Sinai dispute (Jan-Apr 2026): 9,000 physicians and hospitals went OON \
  for ~200,000 Anthem members. Resolved with 3-year deal including VBC models.
- Anthem claimed Mount Sinai demanded a 50% rate increase; Sinai claimed $450M \
  in unpaid claims. The 7 negotiation points included rates, claims review, \
  termination rights, interim payments, and VBC structures.
- Blue Cross cross-licensing structure adds payment processing complexity.
- Anthem/Elevance is pushing value-based care models to tie payment to outcomes.
- Horizon BCBS NJ is a separate entity but Blue Cross cross-licensing means \
  OON status in NY can ripple to out-of-state Blues members.

Given the news article below, infer what Anthem's tri-state contracting strategy \
looks like, what they learned from the Mount Sinai dispute, and how they will \
approach future renewals. Focus on how claims review and VBC models are being \
used as negotiation levers.
""",
    "Cigna / Evernorth": """\
You are simulating the strategic perspective of Cigna's provider contracting \
team for the NY/CT/NJ tri-state region. Key context:
- Cigna is strongest in the employer-sponsored commercial market.
- Evernorth (PBM, specialty pharmacy, care delivery) creates vertical integration.
- Less Medicaid presence in tri-state than UHC or Anthem.
- Health Care Service Corp (HCSC) merged some Cigna products; watch for brand confusion.
- Cigna historically positions on narrow/tiered networks to control costs.
- MA is a secondary focus for Cigna vs. UHC/Anthem, but growing.
- In NJ, Cigna competes against dominant Horizon BCBS.

Given the news article below, infer Cigna's likely response and strategy. \
Focus on how they differentiate from UHC and Anthem in provider negotiations, \
their employer-market positioning, and how Evernorth's vertical integration \
affects their negotiating stance with hospitals.
""",
}


# ─────────────────────────────────────────────────────────────────────
# NEWS SOURCES — expanded for tri-state coverage
# ─────────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    # National healthcare (URLs verified periodically; prefer feeds that allow standard HTTP clients)
    {"name": "MobiHealthNews", "url": "https://www.mobihealthnews.com/feed"},
    {"name": "Health Leaders Media", "url": "https://www.healthleadersmedia.com/rss.xml"},
    {"name": "MedCity News", "url": "https://medcitynews.com/feed/"},
    {"name": "Fierce Healthcare", "url": "https://www.fiercehealthcare.com/rss/xml"},
    {"name": "Healthcare Dive", "url": "https://www.healthcaredive.com/feeds/news/"},
    {"name": "BioPharma Dive", "url": "https://www.biopharmadive.com/feeds/news/"},
    {"name": "Healthcare IT News", "url": "https://www.healthcareitnews.com/feed"},
    {"name": "KFF Health News", "url": "https://kffhealthnews.org/feed/"},
    {"name": "HFMA", "url": "https://www.hfma.org/feed/"},
    {"name": "CMS Newsroom", "url": "https://www.cms.gov/newsroom/rss-feeds"},
    {"name": "NPR Health", "url": "https://www.npr.org/rss/rss.php?id=1128"},
    {"name": "STAT News", "url": "https://www.statnews.com/feed/"},
    # NY-specific
    {"name": "The City (NYC)", "url": "https://www.thecity.nyc/rss"},
    {"name": "Gothamist", "url": "https://gothamist.com/feed"},
    # CT-specific
    {"name": "CT Mirror Health", "url": "https://ctmirror.org/category/health/feed/"},
    {"name": "CT OHS News", "url": "https://portal.ct.gov/ohs/press-room/press-releases/rss"},
    {"name": "CT News Junkie", "url": "https://www.ctnewsjunkie.com/feed/"},
    {"name": "CT Examiner", "url": "https://ctexaminer.com/feed/"},
    # NJ-specific
    {"name": "NJ Spotlight News", "url": "https://www.njspotlightnews.org/feed/"},
    {"name": "New Jersey Monitor", "url": "https://newjerseymonitor.com/feed/"},
    {"name": "ROI-NJ Healthcare", "url": "https://www.roi-nj.com/category/healthcare/feed/"},
    # Policy / regulatory & payer/commercial
    {"name": "Health Affairs Journal", "url": "https://www.healthaffairs.org/action/showFeed?type=etoc&feed=rss&jc=hlthaff"},
    {"name": "PYMNTS Healthcare", "url": "https://www.pymnts.com/tag/healthcare/feed/"},
]

SCRAPE_SOURCES = [
    {"name": "AHA News Insurance", "url": "https://www.aha.org/news?topic=340", "selector": "h3 a, .node-title a", "base_url": "https://www.aha.org"},
]


# ─────────────────────────────────────────────────────────────────────
# KEYWORDS — topic and geographic
# ─────────────────────────────────────────────────────────────────────

TOPIC_KEYWORDS = [
    "contract negotiation", "contract dispute", "out of network", "out-of-network",
    "network termination", "in-network", "network exit", "reimbursement rate",
    "rate increase", "rate cut", "fee schedule", "payer contract", "provider contract",
    "contract renewal", "contract expir", "going out of network",
    "open enrollment", "annual enrollment", "medicare advantage", "medicaid managed care",
    "essential plan", "plan exit", "dropping plan", "leaving network", "network change",
    "benefit cut", "premium increase", "plan termination",
    "value-based", "capitation", "bundled payment", "shared savings", "risk-based",
    "fee-for-service", "alternative payment",
    "no surprises act", "independent dispute resolution", "idr",
    "prior authorization", "network adequacy", "cms final rule",
    "price transparency", "qualified payment amount", "qpa",
    "hospital merger", "provider consolidation", "insurer consolidation",
    "market power", "antitrust", "private equity", "certificate of need",
    "denial rate", "claim denial", "underpayment",
    "unitedhealthcare", "uhc", "anthem", "aetna", "cigna", "humana",
    "blue cross", "bcbs", "molina", "centene", "wellcare", "oscar health",
    "horizon bcbs", "emblemhealth", "healthfirst", "fidelis", "metroplus",
    "connecticare", "amerihealth",
    "mount sinai", "nyu langone", "newyork-presbyterian", "montefiore",
    "memorial sloan kettering", "northwell", "maimonides",
    "yale new haven", "hartford healthcare", "nuvance",
    "rwjbarnabas", "hackensack meridian", "atlantic health", "virtua",
    "valley health", "cooper university", "englewood health",
]

GEO_KEYWORDS: dict[str, list[str]] = {
    "NY": [
        "new york", "nyc", "manhattan", "brooklyn", "bronx", "queens", "staten island",
        "long island", "westchester", "hudson valley",
        "mount sinai", "nyu langone", "newyork-presbyterian", "nyp", "montefiore",
        "memorial sloan", "msk", "northwell", "maimonides", "nyc health + hospitals",
        "emblemhealth", "healthfirst", "metroplus", "fidelis", "empire bcbs",
        "oxford health", "ny state of health",
    ],
    "CT": [
        "connecticut", " ct ", "hartford", "new haven", "bridgeport", "stamford",
        "fairfield county", "yale new haven", "hartford healthcare", "nuvance",
        "trinity health new england", "saint francis ct", "stamford health",
        "middlesex health", "connecticare", "ct ohs", "husky health",
    ],
    "NJ": [
        "new jersey", " nj ", "newark", "hackensack", "morristown", "paterson",
        "trenton", "camden", "jersey city",
        "rwjbarnabas", "hackensack meridian", "hmh", "atlantic health", "virtua",
        "valley health nj", "cooper university", "englewood health",
        "horizon bcbs", "amerihealth", "nj dobi",
    ],
}


# ─────────────────────────────────────────────────────────────────────
# OLLAMA
# ─────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma4"
OLLAMA_TIMEOUT = 120

# ─────────────────────────────────────────────────────────────────────
# THRESHOLDS & SETTINGS
# ─────────────────────────────────────────────────────────────────────
MAX_ARTICLES_PER_SOURCE = 10
MIN_RELEVANCE_SCORE = 5
SEEN_DB_PATH = "data/seen_articles.json"
ANALYSIS_RUNS_PATH = "data/analysis_runs.json"
LOG_PATH = "data/monitor.log"
REPORTS_DIR = "data/reports"
LLM_CACHE_DIR = "data/llm_cache"
