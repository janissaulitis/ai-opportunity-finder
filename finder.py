"""Finds where AI pays off first in a company, from a few answers about how the team spends its time.

Each use case knows what it saves per unit of work (minutes per email, per invoice, per report…), how much effort it
takes to set up, and what makes it risky. The ranking is plain arithmetic, shown in the details, so every number can be
questioned: hours saved × hourly cost × a realistic adoption rate, against a setup cost and an ongoing cost.
"""
from __future__ import annotations

from dataclasses import dataclass

PROOF = {
    "triage": ("Inbox Router", "https://ai-inbox-triage.streamlit.app/"),
    "statements": ("Statement Check", "https://loan-doc-checker.streamlit.app/"),
    "risk": ("Early Call", "https://loan-risk-model.streamlit.app/"),
    "quote": ("Quote calculator", "https://live-production-quote-calculator.vercel.app/"),
    "schedule": ("Crew scheduler", "https://court-crew-control.lovable.app/"),
    "report": ("Client report from messy logs", "https://tournament-report.streamlit.app/"),
}

# What eats the team's time. Each pain asks for one volume and maps to the use cases that address it.
PAINS = {
    "emails": ("Answering customer emails and messages", "Customer emails a month", 400),
    "documents": ("Checking documents (IDs, statements, contracts)", "Documents checked a month", 150),
    "invoices": ("Typing in invoices and receipts", "Invoices and receipts a month", 300),
    "bookkeeping": ("Sorting bank transactions for the books", "Bank transactions a month", 800),
    "leads": ("Following up on sales leads", "New leads a month", 120),
    "meetings": ("Writing up meetings and action points", "Meetings a week", 10),
    "reports": ("Building weekly or monthly reports", "Reports a month", 12),
    "questions": ("Staff searching for answers in documents and policies", "Staff who look things up", 15),
    "content": ("Writing posts, product texts, newsletters", "Pieces of content a month", 40),
    "translation": ("Translating texts between languages", "Pages translated a month", 30),
    "scheduling": ("Planning shifts or crews", "People scheduled", 20),
    "quotes": ("Preparing price quotes", "Quotes a month", 60),
    "hiring": ("Screening job applications", "Applications a month", 80),
    "late_payments": ("Customers paying late", "Active customers or loans", 2000),
}


@dataclass
class UseCase:
    key: str
    name: str
    pain: str
    does: str
    minutes_per_unit: float        # time saved per unit of work, before adoption
    effort_weeks: float            # to a working first version
    monthly_tool_cost: float       # AI / software running cost, € per month at typical volume
    risk: str                      # "low" | "medium" | "high"
    risk_note: str
    first_steps: tuple[str, str, str]
    proof: str | None = None
    unit_scale: float = 1.0        # converts the asked volume into units per month
    value_per_unit_eur: float = 0.0  # direct money value per unit (instead of time), e.g. prevented losses
    industries: tuple[str, ...] = ()  # where it matters more than usual


CASES = [
    UseCase("triage", "Sort and draft replies to customer emails", "emails",
            "Reads each email, sorts it by topic and urgency, sends it to the right person and drafts a reply in the "
            "customer's language. A person reviews before sending.", 3.0, 3, 40, "medium",
            "Customer data goes to an AI service: needs a data agreement and a person checking sensitive replies.",
            ("Export 200 recent emails and label the topics", "Test sorting accuracy on them before going live",
             "Start with drafts only; send automatically only the simplest topics later"), "triage",
            industries=("finance", "ecommerce", "software", "hospitality")),
    UseCase("statements", "Check documents against applications", "documents",
            "Reads statements, IDs or contracts in any language and flags what doesn't match: names, dates, income, "
            "missing pages. A person decides.", 9.0, 4, 30, "high",
            "Personal and financial data, often regulated: keep a person in every decision and log what the AI read.",
            ("Collect 30 past documents with the decisions made on them", "Agree the 5–8 checks that matter most",
             "Run side by side with the team for a month and compare"), "statements",
            industries=("finance", "professional", "public")),
    UseCase("invoices", "Read invoices and receipts automatically", "invoices",
            "Pulls supplier, date, amounts and VAT from invoices and receipts into the accounting system.", 4.0, 2, 25,
            "low", "Low risk: totals are checked against the bank payment.",
            ("Pick the 10 suppliers with the most invoices", "Connect the inbox where invoices arrive",
             "Check every extracted total against the payment for the first month"),
            industries=("logistics", "manufacturing", "hospitality", "ecommerce")),
    UseCase("bookkeeping", "Sort bank transactions for the books", "bookkeeping",
            "Puts each bank transaction in the right accounting category and learns from every correction.", 0.6, 2,
            10, "low", "Low risk: an accountant still reviews the month.",
            ("Export 6 months of categorised transactions", "Train on them and measure the hit rate",
             "Let the accountant correct the rest; the model learns from each fix"),
            industries=("professional", "hospitality", "ecommerce")),
    UseCase("leads", "Qualify leads and draft follow-ups", "leads",
            "Scores new leads from the form and website data and drafts a personal first follow-up for the salesperson.",
            6.0, 2, 30, "low", "Low risk: a salesperson sends every message.",
            ("List what made your last 20 good customers good", "Turn that into a simple score",
             "Draft follow-ups for one week and compare reply rates"), industries=("software", "professional")),
    UseCase("meetings", "Meeting notes and action points", "meetings",
            "Turns a meeting recording into a summary, decisions and who-does-what, posted to the team's tool.", 15.0,
            1, 20, "medium", "Recordings may include personal data: get consent and set a retention period.",
            ("Choose one recurring meeting to start with", "Agree the summary format",
             "Send the summary to attendees to confirm for two weeks"), unit_scale=4.3),
    UseCase("reports", "Build recurring reports automatically", "reports",
            "Pulls the numbers from the systems, checks them, and writes the report with the main changes explained.",
            60.0, 3, 20, "low", "Low risk if numbers are checked against the source.",
            ("Pick the report that takes longest", "List where each number comes from",
             "Generate it alongside the manual one for two cycles"), "report",
            industries=("logistics", "manufacturing", "finance", "professional")),
    UseCase("questions", "An assistant that answers from your own documents", "questions",
            "Staff ask in plain language and get an answer with a link to the policy, manual or contract it came from.",
            90.0, 4, 60, "medium", "Answers must cite the source; outdated documents give outdated answers.",
            ("Collect the 30 questions people ask most", "Gather the documents that answer them",
             "Test the answers with two teams before rolling out")),
    UseCase("content", "Draft posts, product texts and newsletters", "content",
            "Writes first drafts in your tone from short briefs or product data; a person edits and publishes.", 20.0,
            1, 20, "low", "Low risk with a human editor; check facts and claims.",
            ("Collect 20 texts you liked", "Write a one-page tone guide from them", "Draft one week of content and compare time spent"),
            industries=("ecommerce", "hospitality")),
    UseCase("translation", "Translate texts and replies", "translation",
            "Translates pages, replies and product texts between languages, keeping your terms consistent.", 15.0, 1,
            15, "low", "Have a native speaker check legal and customer-facing texts.",
            ("Build a glossary of 50 company terms", "Translate one batch and have it checked", "Track how much editing each page needs")),
    UseCase("schedule", "Plan shifts and crews", "scheduling",
            "Builds the plan from availability and rules, flags clashes, rest-time breaches and overtime before they happen.",
            30.0, 4, 15, "low", "Low risk: the planner approves the plan.",
            ("Write down the rules the planner follows", "Load one month of real availability",
             "Compare clashes and overtime against the manual plan"), "schedule",
            industries=("logistics", "hospitality", "manufacturing", "public"), unit_scale=1 / 4),
    UseCase("quotes", "Instant quotes customers build themselves", "quotes",
            "A price calculator on the website or in sales, with the quote ready to send or print.", 10.0, 2, 5, "low",
            "Low risk once the price rules are confirmed.",
            ("Write down the price rules and discounts", "Rebuild 20 past quotes with the calculator", "Put it live for one product line"),
            "quote", industries=("professional", "manufacturing", "logistics")),
    UseCase("hiring", "Screen job applications", "hiring",
            "Matches applications to the role's must-haves and summarises each one; a recruiter decides.", 5.0, 2, 15,
            "high", "Hiring with AI is high-risk under the EU AI Act: a person must decide, and the criteria must be fair and documented.",
            ("Agree the 5 must-haves for one role", "Compare AI summaries with the recruiter's notes on 30 CVs",
             "Document the criteria before using it on a live role")),
    UseCase("risk", "Predict which customers will pay late", "late_payments",
            "Scores customers for the risk of paying late, so the team calls the right ones early, with the reasons shown.",
            0.0, 5, 20, "medium", "Uses personal financial data; explain every score and don't use it to refuse credit without a person.",
            ("Export 18 months of payment history", "Train and test on the most recent months",
             "Call the top 10% for two months and measure the late rate"), "risk", value_per_unit_eur=0.35,
            industries=("finance", "software", "public")),
]
BY_KEY = {c.key: c for c in CASES}
INDUSTRIES = {"finance": "Finance and lending", "ecommerce": "Online shop or e-commerce",
              "professional": "Professional services (accounting, legal, agencies)", "logistics": "Logistics and transport",
              "manufacturing": "Manufacturing", "hospitality": "Hotels, restaurants and events",
              "software": "Software and tech", "public": "Public sector or non-profit", "other": "Something else"}


def assess(industry: str, pains: dict[str, float], hourly_cost: float, build_cost_per_week: float,
           adoption: float = 0.6, sensitive_data: bool = False) -> list[dict]:
    """pains: {pain_key: volume}. Returns every applicable use case, best first."""
    out = []
    for c in CASES:
        if c.pain not in pains:
            continue
        units = pains[c.pain] * c.unit_scale
        hours = units * c.minutes_per_unit / 60 * adoption
        time_value = hours * hourly_cost
        direct = units * c.value_per_unit_eur * adoption
        monthly_value = time_value + direct
        net = monthly_value - c.monthly_tool_cost
        setup = c.effort_weeks * build_cost_per_week
        payback = setup / net if net > 0 else float("inf")
        risk = c.risk
        if sensitive_data and risk == "medium":
            risk = "high" if c.key in ("triage", "questions") else risk
        fit = 1.15 if industry in c.industries else 1.0
        penalty = {"low": 1.0, "medium": 0.85, "high": 0.7}[risk]
        score = (net * 12 / max(setup, 1)) * fit * penalty
        out.append({"key": c.key, "name": c.name, "does": c.does, "hours": hours, "monthly_value": monthly_value,
                    "tool_cost": c.monthly_tool_cost, "net": net, "setup": setup, "weeks": c.effort_weeks,
                    "payback_months": payback, "risk": risk, "risk_note": c.risk_note, "steps": c.first_steps,
                    "proof": PROOF.get(c.proof) if c.proof else None, "score": score, "industry_fit": fit > 1,
                    "units": units, "minutes": c.minutes_per_unit})
    return sorted(out, key=lambda r: -r["score"])
