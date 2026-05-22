"""Vendor Risk Copilot service.

Automates vendor risk assessment using AI:
1. Extract structured data from unstructured vendor documents
2. Classify risk level with reasoning
3. Suggest next steps
4. Draft follow-up emails
"""

import json
import re
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from app.config import settings


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a Third-Party Risk Management (TPRM) analyst. Extract structured vendor information from the document below.

Return ONLY a valid JSON object (no markdown, no extra text). Use these exact keys:
- company_name: string or null
- risk_type: "Financial", "Security", "Compliance", "Operational", "Data Privacy", or null
- country: string or null
- business_unit: string or null
- compliance_notes: string or null
- missing_fields: array of strings

Example: {{"company_name": "Example Corp", "risk_type": "Security", "country": "USA", "business_unit": "IT", "compliance_notes": null, "missing_fields": ["SOC 2 report"]}}

Be thorough. Infer from context when obvious. Mark as null when uncertain."""),
    ("human", "DOCUMENT:\n{document_text}")
])

RISK_CLASSIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a TPRM risk analyst. Based on the extracted vendor information, classify the risk level.

Consider:
- Risk type (Security/Compliance risks are typically higher)
- Country (high-risk jurisdictions)
- Missing fields (gaps in information increase risk)
- Compliance notes (red flags)

Return ONLY valid JSON:
{{"risk_level": "Critical or High or Medium or Low", "reasoning": "brief explanation"}}"""),
    ("human", "EXTRACTED INFO:\n{extracted_json}")
])

NEXT_STEPS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a TPRM analyst. Based on the risk assessment, suggest specific next steps.

Return a JSON array of 3-5 actionable steps. Each step should be specific and actionable.
Example: "Request SOC 2 Type II report within 30 days"

Return format: ["step 1", "step 2", ...]"""),
    ("human", "COMPANY: {company_name}\nRISK LEVEL: {risk_level}\nRISK TYPE: {risk_type}\nCOMPLIANCE NOTES: {compliance_notes}\nMISSING FIELDS: {missing_fields}")
])

EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a TPRM analyst drafting a professional follow-up email to a vendor.

The email should:
1. Be professional and courteous
2. Reference the risk assessment findings
3. Request additional information if needed
4. Suggest next steps for the vendor relationship

Do NOT include a subject line or salutation placeholder. Write the body only."""),
    ("human", "COMPANY: {company_name}\nRISK LEVEL: {risk_level}\nRISK TYPE: {risk_type}\nNEXT STEPS: {next_steps}")
])


class VendorRiskService:
    """AI-powered vendor risk assessment service."""

    def __init__(self):
        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )
        self.extraction_chain = EXTRACTION_PROMPT | self.llm | StrOutputParser()
        self.classification_chain = RISK_CLASSIFICATION_PROMPT | self.llm | StrOutputParser()
        self.next_steps_chain = NEXT_STEPS_PROMPT | self.llm | StrOutputParser()
        self.email_chain = EMAIL_PROMPT | self.llm | StrOutputParser()

    async def run_full_assessment(self, document_text: str, filename: str) -> dict:
        """
        Run the full vendor assessment pipeline:
        1. Extract structured data
        2. Classify risk
        3. Suggest next steps
        4. Draft follow-up email
        """
        # Step 1: Extract
        extracted = await self._extract(document_text)

        # Step 2: Classify risk
        classification = await self._classify_risk(extracted)

        # Step 3: Suggest next steps
        next_steps = await self._suggest_next_steps(
            extracted.get("company_name") or filename,
            classification.get("risk_level", "Medium"),
            extracted.get("risk_type"),
            extracted.get("compliance_notes"),
            extracted.get("missing_fields", []),
        )

        # Step 4: Draft email
        email = await self._draft_email(
            extracted.get("company_name") or filename,
            classification.get("risk_level", "Medium"),
            extracted.get("risk_type"),
            next_steps,
        )

        return {
            "company_name": extracted.get("company_name"),
            "risk_type": extracted.get("risk_type"),
            "risk_level": classification.get("risk_level", "Medium"),
            "country": extracted.get("country"),
            "business_unit": extracted.get("business_unit"),
            "compliance_notes": extracted.get("compliance_notes"),
            "missing_fields": extracted.get("missing_fields", []),
            "extracted_raw": extracted,
            "classification_reasoning": classification.get("reasoning", ""),
            "next_steps": next_steps,
            "follow_up_email": email,
        }

    async def _extract(self, text: str) -> dict:
        """Extract structured vendor info from document text."""
        # Truncate to avoid context window issues
        truncated = text[:8000] if len(text) > 8000 else text
        try:
            raw = await self.extraction_chain.ainvoke({"document_text": truncated})
            parsed = self._parse_json(raw, None)
            if parsed is None:
                return {
                    "company_name": None,
                    "risk_type": None,
                    "country": None,
                    "business_unit": None,
                    "compliance_notes": None,
                    "missing_fields": [],
                    "_extracted_raw": raw,
                    "_parse_failed": True,
                }
            return parsed
        except Exception as e:
            return {
                "company_name": None,
                "risk_type": None,
                "country": None,
                "business_unit": None,
                "compliance_notes": None,
                "missing_fields": [],
                "_error": str(e),
            }

    async def _classify_risk(self, extracted: dict) -> dict:
        """Classify vendor risk level."""
        try:
            raw = await self.classification_chain.ainvoke({
                "extracted_json": json.dumps(extracted, indent=2)
            })
            return self._parse_json(raw, {"risk_level": "Medium", "reasoning": "Fallback classification"})
        except:
            return {"risk_level": "Medium", "reasoning": "Fallback classification"}

    async def _suggest_next_steps(
        self, company: str, risk_level: str, risk_type, compliance_notes, missing_fields
    ) -> list[str]:
        """Suggest next steps based on risk assessment."""
        try:
            raw = await self.next_steps_chain.ainvoke({
                "company_name": company,
                "risk_level": risk_level,
                "risk_type": risk_type or "Unknown",
                "compliance_notes": compliance_notes or "None provided",
                "missing_fields": json.dumps(missing_fields),
            })
            parsed = self._parse_json(raw, [])
            if isinstance(parsed, list):
                return parsed[:5]
            return self._default_next_steps(risk_level)
        except:
            return self._default_next_steps(risk_level)

    async def _draft_email(
        self, company: str, risk_level: str, risk_type, next_steps: list
    ) -> str:
        """Draft a follow-up email to the vendor."""
        try:
            email = await self.email_chain.ainvoke({
                "company_name": company,
                "risk_level": risk_level,
                "risk_type": risk_type or "General",
                "next_steps": json.dumps(next_steps),
            })
            return email.strip()
        except:
            return (
                f"Dear {company} Team,\n\n"
                f"Following our recent assessment, we have identified some areas "
                f"that require attention regarding our vendor relationship. "
                f"The risk level has been classified as {risk_level}.\n\n"
                f"Please review the recommended next steps and reach out to "
                f"schedule a follow-up discussion.\n\nBest regards,\nTPRM Team"
            )

    def _parse_json(self, raw: str, default):
        """Parse JSON from LLM output, with fallback to regex extraction."""
        # Strip markdown code fences
        cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip()

        json_match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        return default

    def _default_next_steps(self, risk_level: str) -> list[str]:
        steps = {
            "Critical": [
                "Schedule immediate risk mitigation call with vendor",
                "Request full security audit report within 14 days",
                "Escalate to leadership for review",
                "Define remediation plan with clear deadlines",
                "Evaluate alternative vendors as contingency",
            ],
            "High": [
                "Request SOC 2 or equivalent security report",
                "Schedule vendor risk review meeting within 30 days",
                "Request evidence of compliance controls",
                "Define action plan for identified gaps",
            ],
            "Medium": [
                "Request updated compliance documentation",
                "Schedule quarterly review cadence",
                "Monitor for any changes in risk posture",
            ],
            "Low": [
                "Document assessment and file for records",
                "Schedule annual review cycle",
                "No immediate action required",
            ],
        }
        return steps.get(risk_level, steps["Medium"])
