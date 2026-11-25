"""Settings loaded from environment variables. Secrets are never stored in code."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.split(" #", 1)[0].strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class Settings:
    firecrawl_api_key: str = ""
    mailchimp_api_key: str = ""
    mailchimp_audience_id: str = ""
    mailchimp_server_prefix: str = ""
    from_name: str = "Ana | James Insurance Advisory"
    reply_to: str = ""
    dnc_csv_path: str = ""
    scrub_cleared_csv_path: str = ""
    litigator_csv_path: str = ""
    suppression_csv_path: str = ""
    scrub_api_url: str = ""
    scrub_api_key: str = ""
    require_phone_for_dnc_check: bool = True
    dnc_scrub: str = "internal"  # "internal" or "external" (done by your team after export)
    agency_name: str = "James Insurance Advisory"
    carrier_disclaimer: str = ""
    agency_address: str = "[PHYSICAL MAILING ADDRESS]"
    agent_license_line: str = ""
    licensed_states: list[str] = field(default_factory=list)
    brochure_url: str = "[BROCHURE PDF LINK]"
    booking_url: str = "https://calendly.com/aidenjameshealth/free-health-coverage-consultation-clone-1"
    include_premiums: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        d = cls()
        return cls(
            firecrawl_api_key=_env("FIRECRAWL_API_KEY"),
            mailchimp_api_key=_env("MAILCHIMP_API_KEY"),
            mailchimp_audience_id=_env("MAILCHIMP_AUDIENCE_ID"),
            mailchimp_server_prefix=_env("MAILCHIMP_SERVER_PREFIX"),
            from_name=_env("MAILCHIMP_FROM_NAME", d.from_name),
            reply_to=_env("MAILCHIMP_REPLY_TO", d.reply_to),
            dnc_csv_path=_env("DNC_CSV_PATH"),
            scrub_cleared_csv_path=_env("SCRUB_CLEARED_CSV_PATH"),
            litigator_csv_path=_env("LITIGATOR_CSV_PATH"),
            suppression_csv_path=_env("SUPPRESSION_CSV_PATH"),
            scrub_api_url=_env("SCRUB_API_URL"),
            scrub_api_key=_env("SCRUB_API_KEY"),
            dnc_scrub="external" if _env("DNC_SCRUB", "internal").lower() == "external" else "internal",
            require_phone_for_dnc_check=_env("REQUIRE_PHONE_FOR_DNC_CHECK", "true").lower() != "false",
            agency_name=_env("AGENCY_NAME", d.agency_name),
            agency_address=_env("AGENCY_ADDRESS", d.agency_address),
            carrier_disclaimer=_env("CARRIER_DISCLAIMER"),
            agent_license_line=_env("AGENT_LICENSE_LINE", d.agent_license_line),
            licensed_states=[s.strip().upper() for s in _env("LICENSED_STATES").split(",") if s.strip()],
            brochure_url=_env("BROCHURE_URL", d.brochure_url),
            booking_url=_env("BOOKING_URL", d.booking_url),
            include_premiums=_env("INCLUDE_PREMIUMS", "false").lower() == "true",
        )

    def unfilled_placeholders(self) -> list[str]:
        names = ["from_name", "agency_name", "agency_address", "brochure_url", "booking_url"]
        return [n for n in names if "[" in getattr(self, n)]
