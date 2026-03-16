from typing import Any

import aiohttp

from ..settings import settings

BASE_URL = "https://www.googleapis.com"


async def run_page_speed(url: str):
    async with (
        aiohttp.ClientSession(base_url=settings.google.base_url) as session,
        session.get(
            url="/pagespeedonline/v5/runPagespeed",
            params={
                "url": url,
                "strategy": "mobile",
                "category": ["seo", "performance", "best-practices"],
                "key": settings.google.psi_api_key,
            },
        ) as response,
    ):
        data = await response.json()

    return _parse_response(data)


def _parse_response(response: dict[str, Any]) -> dict[str, Any]:  # noqa: C901
    filtered = {}
    if "loadingExperience" in response:
        filtered["loadingExperience"] = response["loadingExperience"]
    if "originLoadingExperience" in response:
        filtered["originLoadingExperience"] = response["originLoadingExperience"]
    if "lighthouseResult" in response:
        lh = response["lighthouseResult"]
        filtered_lh = {}
        if "requestedUrl" in lh:
            filtered_lh["requestedUrl"] = lh["requestedUrl"]
        if "finalUrl" in lh:
            filtered_lh["finalUrl"] = lh["finalUrl"]
        if "lighthouseVersion" in lh:
            filtered_lh["lighthouseVersion"] = lh["lighthouseVersion"]
        if "configSettings" in lh:
            filtered_lh["configSettings"] = lh["configSettings"]
        if "categories" in lh:
            categories = {}
            if "performance" in lh["categories"]:
                categories["performance"] = lh["categories"]["performance"]
            if "seo" in lh["categories"]:
                categories["seo"] = lh["categories"]["seo"]
            if categories:
                filtered_lh["categories"] = categories
        if "audits" in lh:
            audits = {}
            cwv_audit_ids = [
                "largest-contentful-paint",
                "cumulative-layout-shift",
                "first-contentful-paint",
                "first-input-delay",
                "interaction-to-next-paint",
                "total-blocking-time",
                "time-to-first-byte",
            ]
            seo_audit_ids = []
            if "categories" in filtered_lh and "seo" in filtered_lh["categories"]:
                seo_audit_ids = [
                    ref["id"] for ref in filtered_lh["categories"]["seo"].get("auditRefs", [])
                ]
            relevant_ids = set(cwv_audit_ids + seo_audit_ids)
            for audit_id in relevant_ids:
                if audit_id in lh["audits"]:
                    audits[audit_id] = lh["audits"][audit_id]
            if audits:
                filtered_lh["audits"] = audits
        if filtered_lh:
            filtered["lighthouseResult"] = filtered_lh
    return filtered
