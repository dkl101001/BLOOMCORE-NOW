# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Deterministic citation-surface inspection for BLOOMCORE RECEIPT."""

from __future__ import annotations

import datetime as dt
import html
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from html.parser import HTMLParser
from typing import Any

URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'-]{1,}", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?)]}'\""
MAX_RESPONSE_BYTES = 1_500_000
DEFAULT_TIMEOUT = 8.0
MAX_REFERENCES = 25
MAX_CLAIMS = 200

STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been",
    "before", "being", "between", "both", "but", "can", "could", "did",
    "does", "each", "for", "from", "had", "has", "have", "into", "its",
    "may", "more", "most", "not", "of", "on", "only", "or", "other", "our",
    "over", "same", "should", "such", "than", "that", "the", "their", "then",
    "there", "these", "they", "this", "through", "to", "under", "using",
    "was", "were", "which", "while", "will", "with", "would",
}


class PageTextParser(HTMLParser):
    """Extract title, metadata descriptions and visible text without execution."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.description = ""
        self._in_title = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
        if lowered == "title":
            self._in_title = True
        if lowered == "meta":
            values = {key.lower(): (value or "") for key, value in attrs}
            name = values.get("name", "").lower()
            prop = values.get("property", "").lower()
            if name == "description" or prop in {"og:description", "twitter:description"}:
                self.description = values.get("content", self.description)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self._in_title = False
        if lowered in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value or self._ignored_depth:
            return
        if self._in_title:
            self.title_parts.append(value)
        else:
            self.text_parts.append(value)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def text(self) -> str:
        return " ".join(self.text_parts).strip()


def normalize_reference(value: str) -> str:
    value = html.unescape(value.strip()).rstrip(TRAILING_PUNCTUATION)
    if DOI_RE.fullmatch(value):
        return f"https://doi.org/{value}"
    return value


def extract_references(text: str) -> list[str]:
    references = [normalize_reference(value) for value in URL_RE.findall(text)]
    occupied_dois = {match.lower() for ref in references for match in DOI_RE.findall(ref)}
    for doi in DOI_RE.findall(text):
        if doi.lower() not in occupied_dois:
            references.append(normalize_reference(doi))
    return list(dict.fromkeys(references))


def split_claims(text: str) -> list[str]:
    claims: list[str] = []
    for paragraph in re.split(r"\n\s*\n+", text):
        cleaned = " ".join(paragraph.split())
        if not cleaned or cleaned.startswith("#"):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned):
            sentence = sentence.strip()
            if len(TOKEN_RE.findall(sentence)) >= 3:
                claims.append(sentence)
    return claims


def tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text)
        if token.lower() not in STOPWORDS and len(token) > 2
    }


def lexical_alignment(claim: str, source_text: str) -> float:
    claim_tokens = tokens(URL_RE.sub("", claim))
    source_tokens = tokens(source_text)
    if not claim_tokens or not source_tokens:
        return 0.0
    return round(len(claim_tokens & source_tokens) / len(claim_tokens), 4)


def _validate_public_destination(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http and https references are supported")
    if not parsed.hostname:
        raise ValueError("reference has no hostname")
    if parsed.username or parsed.password:
        raise ValueError("embedded credentials are not allowed")
    if parsed.port and parsed.port not in {80, 443}:
        raise ValueError("nonstandard network ports are blocked")

    destination_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        records = socket.getaddrinfo(parsed.hostname, destination_port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"hostname resolution failed: {exc}") from exc
    for record in records:
        address = ipaddress.ip_address(record[4][0])
        if not address.is_global:
            raise ValueError(f"non-public destination blocked: {address}")


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect destination before urllib follows it."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        _validate_public_destination(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_reference(url: str, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Fetch bounded public text after validating the destination."""

    _validate_public_destination(url)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BLOOMCORE-RECEIPT/0.1 (+public evidence inspection)"},
    )
    opener = urllib.request.build_opener(SafeRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            _validate_public_destination(final_url)
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            truncated = len(payload) > MAX_RESPONSE_BYTES
            payload = payload[:MAX_RESPONSE_BYTES]
            try:
                body = payload.decode(charset, errors="replace")
            except LookupError:
                body = payload.decode("utf-8", errors="replace")
            if content_type in {"text/html", "application/xhtml+xml"}:
                parser = PageTextParser()
                parser.feed(body)
                title = parser.title
                source_text = " ".join(part for part in (title, parser.description, parser.text) if part)
            elif content_type.startswith("text/") or content_type in {
                "application/json",
                "application/xml",
            }:
                title = ""
                source_text = body
            else:
                title = ""
                source_text = ""
            return {
                "status": "reachable",
                "http_status": response.status,
                "final_url": final_url,
                "content_type": content_type,
                "title": title,
                "text": source_text,
                "truncated": truncated,
            }
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return {
            "status": "unreachable",
            "error": str(exc),
            "text": "",
            "title": "",
        }


def _reference_findings(
    claim: str,
    references: list[str],
    online: bool,
    fetcher: Callable[[str], dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for reference in references:
        if reference not in claim:
            continue
        if not online:
            findings.append({
                "kind": "reference",
                "claim": claim,
                "reference": reference,
                "source_status": "not_checked",
                "alignment": None,
                "verdict": "unresolved",
                "reason": "offline mode preserves the reference without asserting reachability",
            })
            continue
        try:
            source = fetcher(reference)
        except (OSError, ValueError) as exc:
            source = {"status": "unreachable", "error": str(exc), "text": "", "title": ""}
        if source.get("status") != "reachable":
            findings.append({
                "kind": "reference",
                "claim": claim,
                "reference": reference,
                "source_status": "unreachable",
                "alignment": 0.0,
                "verdict": "red_flag",
                "reason": source.get("error", "source could not be reached"),
            })
            continue
        score = lexical_alignment(claim, f"{source.get('title', '')} {source.get('text', '')}")
        if score >= 0.45:
            verdict, reason = "aligned", "strong deterministic token overlap"
        elif score >= 0.2:
            verdict, reason = "weak_alignment", "partial deterministic token overlap"
        else:
            verdict, reason = "red_flag", "little deterministic token overlap"
        findings.append({
            "kind": "reference",
            "claim": claim,
            "reference": reference,
            "source_status": "reachable",
            "http_status": source.get("http_status"),
            "final_url": source.get("final_url", reference),
            "content_type": source.get("content_type"),
            "title": source.get("title", ""),
            "alignment": score,
            "verdict": verdict,
            "reason": reason,
        })
    return findings


def audit_text(
    text: str,
    *,
    online: bool = False,
    fetcher: Callable[[str], dict[str, Any]] = fetch_reference,
    now: Callable[[], dt.datetime] | None = None,
) -> dict[str, Any]:
    """Inspect visible citation surfaces and return an observational receipt."""

    clock = now or (lambda: dt.datetime.now(dt.timezone.utc))
    all_claims = split_claims(text)
    all_references = extract_references(text)
    claims = all_claims[:MAX_CLAIMS]
    references = all_references[:MAX_REFERENCES]
    findings: list[dict[str, Any]] = []

    if len(all_claims) > MAX_CLAIMS:
        findings.append({
            "kind": "inspection_limit",
            "claim": None,
            "reference": None,
            "source_status": "not_applicable",
            "alignment": None,
            "verdict": "unresolved",
            "reason": f"claim inspection limited to the first {MAX_CLAIMS} parsed claims",
        })
    if len(all_references) > MAX_REFERENCES:
        findings.append({
            "kind": "inspection_limit",
            "claim": None,
            "reference": None,
            "source_status": "not_applicable",
            "alignment": None,
            "verdict": "unresolved",
            "reason": f"network inspection limited to the first {MAX_REFERENCES} references",
        })

    for claim in claims:
        attached = [ref for ref in references if ref in claim]
        if attached:
            findings.extend(_reference_findings(claim, attached, online, fetcher))
        else:
            findings.append({
                "kind": "claim",
                "claim": claim,
                "reference": None,
                "source_status": "absent",
                "alignment": None,
                "verdict": "unresolved",
                "reason": "no explicit URL or DOI was attached to this claim",
            })

    used = {finding.get("reference") for finding in findings}
    for reference in references:
        if reference not in used:
            findings.append({
                "kind": "orphan_reference",
                "claim": None,
                "reference": reference,
                "source_status": "not_checked",
                "alignment": None,
                "verdict": "unresolved",
                "reason": "reference was detected outside a parsed claim",
            })

    duplicate_count = (
        len(URL_RE.findall(text)) + len(DOI_RE.findall(text)) - len(all_references)
    )
    if duplicate_count > 0:
        findings.append({
            "kind": "duplicate_reference",
            "claim": None,
            "reference": None,
            "source_status": "not_applicable",
            "alignment": None,
            "verdict": "notice",
            "reason": f"{duplicate_count} repeated reference occurrence(s) detected",
        })

    red_flags = sum(finding["verdict"] == "red_flag" for finding in findings)
    unresolved = sum(finding["verdict"] == "unresolved" for finding in findings)
    return {
        "schema": "BLOOMCORE.RECEIPT.v1",
        "created_utc": clock().astimezone(dt.timezone.utc).isoformat(),
        "mode": "online" if online else "offline",
        "authority": "observational",
        "summary": {
            "claims": len(claims),
            "references": len(references),
            "red_flags": red_flags,
            "unresolved": unresolved,
        },
        "findings": findings,
        "limitations": [
            "Reachability does not establish truth, quality, authorship or support.",
            "Lexical alignment is deterministic overlap, not semantic entailment.",
            "Sources requiring scripts, authentication or unsupported binary parsing may remain unresolved.",
            "No receipt produced here certifies identity or semantic continuity.",
            "Human review remains required.",
        ],
    }


def render_json(receipt: dict[str, Any]) -> str:
    return json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"


def render_markdown(receipt: dict[str, Any]) -> str:
    summary = receipt["summary"]
    rows = [
        "# BLOOMCORE RECEIPT",
        "",
        f"- Created: `{receipt['created_utc']}`",
        f"- Mode: `{receipt['mode']}`",
        f"- Authority: `{receipt['authority']}`",
        f"- Claims: **{summary['claims']}**",
        f"- References: **{summary['references']}**",
        f"- Red flags: **{summary['red_flags']}**",
        f"- Unresolved: **{summary['unresolved']}**",
        "",
        "| Verdict | Source | Alignment | Claim or note |",
        "| --- | --- | ---: | --- |",
    ]
    for finding in receipt["findings"]:
        claim = (finding.get("claim") or finding.get("reason") or "").replace("|", "\\|")
        source = (finding.get("reference") or "—").replace("|", "%7C")
        alignment = finding.get("alignment")
        value = "—" if alignment is None else f"{alignment:.2f}"
        rows.append(f"| {finding['verdict']} | {source} | {value} | {claim} |")
    rows.extend(["", "## Limitations", ""])
    rows.extend(f"- {item}" for item in receipt["limitations"])
    rows.extend([
        "",
        "> This receipt is an observational inspection surface. It does not certify truth.",
        "",
    ])
    return "\n".join(rows)
