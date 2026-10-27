# SPDX-License-Identifier: Apache-2.0
"""Strict input contracts. Evidence availability never establishes legal compliance."""

import copy
import hashlib
import json
import re
from datetime import date, datetime
from urllib.parse import urlsplit


class Invalid(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def obj(value, required, optional=(), path="object"):
    if not isinstance(value, dict):
        raise Invalid(f"{path}: expected object")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        raise Invalid(f"{path}: missing {sorted(missing)}, unknown {sorted(extra)}")


def text(value, path, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise Invalid(f"{path}: expected {'possibly empty ' if empty else ''}text")
    if len(value) > 20000 or any(ord(c) < 32 and c not in '\n\t\r' for c in value):
        raise Invalid(f"{path}: oversized text or control character")


def ident(value, path):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value):
        raise Invalid(f"{path}: use a short opaque ID")


def strings(values, path):
    if not isinstance(values, list):
        raise Invalid(f"{path}: expected array")
    for v in values:
        text(v, path)
    if len(values) != len(set(values)):
        raise Invalid(f"{path}: duplicate values")


def choice(value, options, path):
    if not isinstance(value, str) or value not in options:
        raise Invalid(f"{path}: expected one of {sorted(options)}")


def day(value, path):
    text(value, path)
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError as e:
        raise Invalid(f"{path}: expected YYYY-MM-DD") from e


def instant(value, path):
    text(value, path)
    try:
        if datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset() is None:
            raise ValueError()
    except ValueError as e:
        raise Invalid(f"{path}: expected timestamp with timezone") from e


def url(value, path):
    text(value, path)
    if any(c.isspace() for c in value) or '\\' in value:
        raise Invalid(f'{path}: whitespace and backslashes are not allowed in source URLs')
    try:
        u = urlsplit(value)
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
            raise ValueError()
        _ = u.port
    except ValueError as e:
        raise Invalid(f"{path}: expected public HTTP(S) URL without credentials") from e


def refs(values, known, path):
    strings(values, path)
    if set(values) - set(known):
        raise Invalid(f"{path}: unresolved references {sorted(set(values) - set(known))}")


STATUSES = {'answered', 'partial', 'disputed', 'unanswered', 'withdrawn', 'superseded'}
ASSESSMENT_STATES = {'documented', 'partially_documented', 'unanswered', 'disputed', 'not_applicable'}
REQUEST_STATES = {'draft', 'submitted', 'acknowledged', 'clarification_needed', 'partial_response', 'fulfilled', 'closed_unresolved', 'withdrawn'}
REVIEW_CHECKS = {'premises_checked', 'contrary_evidence_checked', 'meeting_rules_checked'}


def core(case):
    return {k: v for k, v in case.items() if k != 'review'}


def validate(case):
    obj(case, ('schema_version', 'id', 'agency', 'meeting', 'requested_action', 'why', 'qualification',
               'sources', 'claims', 'questions', 'selected_questions', 'answers', 'assessment', 'requests'),
        ('review', 'private'), 'case')
    if case['schema_version'] != '1.0':
        raise Invalid('unsupported schema_version')
    ident(case['id'], 'case.id')
    for k in ('agency', 'requested_action', 'qualification'):
        text(case[k], k)
    m = case['meeting']
    obj(m, ('date', 'agenda_item', 'decision', 'url'), ('speaking_seconds', 'rules_url', 'rules_verified'), 'meeting')
    day(m['date'], 'meeting.date')
    for k in ('agenda_item', 'decision'):
        text(m[k], 'meeting.' + k)
    url(m['url'], 'meeting.url')
    if 'rules_verified' in m and type(m['rules_verified']) is not bool:
        raise Invalid('rules_verified must be boolean')
    if 'speaking_seconds' in m:
        if type(m['speaking_seconds']) is not int or not 15 <= m['speaking_seconds'] <= 7200:
            raise Invalid('speaking_seconds must be 15..7200')
        if not m.get('rules_verified') or not m.get('rules_url'):
            raise Invalid('timed briefs require verified meeting rules and their URL')
    if 'rules_url' in m:
        url(m['rules_url'], 'rules_url')
    collections = ('sources', 'claims', 'questions', 'answers', 'requests')
    maps = {}
    for kind in collections:
        if not isinstance(case[kind], list) or len(case[kind]) > 2000:
            raise Invalid(f'{kind}: expected bounded array')
        maps[kind] = {}
        for item in case[kind]:
            if not isinstance(item, dict):
                raise Invalid(f'{kind}: expected objects')
            ident(item.get('id'), kind + '.id')
            if item['id'] in maps[kind]:
                raise Invalid(f'{kind}: duplicate ID')
            maps[kind][item['id']] = item
    sources, claims, questions = (maps[k] for k in ('sources', 'claims', 'questions'))
    for s in sources.values():
        obj(s, ('id', 'title', 'issuer', 'document_date', 'retrieved_at', 'url', 'locator',
                'content', 'content_kind', 'limits'), ('parent_id', 'superseded_by', 'sha256', 'license'), 'source')
        for k in ('title', 'issuer', 'locator', 'content', 'limits'):
            text(s[k], 'source.' + k)
        day(s['document_date'], 'document_date')
        instant(s['retrieved_at'], 'retrieved_at')
        url(s['url'], 'source.url')
        choice(s['content_kind'], {'excerpt', 'paraphrase'}, 'content_kind')
        if 'license' in s:
            text(s['license'], 'license')
        if 'sha256' in s and (not isinstance(s['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', s['sha256'])):
            raise Invalid('invalid document sha256')
        for edge in ('parent_id', 'superseded_by'):
            if edge in s and (not isinstance(s[edge], str) or s[edge] not in sources or s[edge] == s['id']):
                raise Invalid('source edge unresolved or self-referencing')
    # Both provenance and amendment graphs must be acyclic.
    for edge in ('parent_id', 'superseded_by'):
        for sid in sources:
            seen = set()
            while sid in sources:
                if sid in seen:
                    raise Invalid(f'cyclic source {edge}')
                seen.add(sid)
                sid = sources[sid].get(edge)
    for c in claims.values():
        obj(c, ('id', 'text', 'basis', 'evidence_ids', 'contrary_ids', 'qualification', 'disposition'), (), 'claim')
        for k in ('text', 'qualification'):
            text(c[k], 'claim.' + k)
        choice(c['basis'], {'document', 'attributed_statement', 'inference', 'open_question'}, 'basis')
        choice(c['disposition'], {'supported', 'partial', 'disputed', 'unverified', 'corrected', 'withdrawn'}, 'disposition')
        for k in ('evidence_ids', 'contrary_ids'):
            refs(c[k], sources, k)
    obj(case['why'], ('text', 'claim_ids'), (), 'why')
    text(case['why']['text'], 'why.text')
    refs(case['why']['claim_ids'], claims, 'why.claim_ids')
    for q in questions.values():
        obj(q, ('id', 'subject', 'text', 'claim_ids', 'gap', 'follow_up', 'rank_reason', 'priority'), (), 'question')
        for k in ('subject', 'text', 'gap', 'follow_up', 'rank_reason'):
            text(q[k], 'question.' + k)
        refs(q['claim_ids'], claims, 'question.claim_ids')
        if type(q['priority']) is not int or not 1 <= q['priority'] <= 100:
            raise Invalid('question.priority must be 1..100; lower is earlier, not a confidence score')
    refs(case['selected_questions'], questions, 'selected_questions')
    if not 1 <= len(case['selected_questions']) <= 3:
        raise Invalid('select one to three questions')
    for a in maps['answers'].values():
        obj(a, ('id', 'question_id', 'kind', 'text', 'context', 'speaker_role', 'source', 'locator',
                'recorded_at', 'status', 'reviewer', 'remaining_gap', 'corroboration', 'evidence_ids'),
            ('quote_verified', 'commitment'), 'answer')
        if not isinstance(a['question_id'], str) or a['question_id'] not in questions:
            raise Invalid('answer references unknown question')
        for k in ('text', 'context', 'speaker_role', 'source', 'locator', 'reviewer'):
            text(a[k], 'answer.' + k)
        text(a['remaining_gap'], 'remaining_gap', empty=True)
        instant(a['recorded_at'], 'recorded_at')
        choice(a['kind'], {'quote', 'paraphrase', 'note'}, 'answer.kind')
        choice(a['status'], STATUSES, 'answer.status')
        choice(a['corroboration'], {'attributed_only', 'document_supported', 'disputed'}, 'corroboration')
        refs(a['evidence_ids'], sources, 'answer.evidence_ids')
        if 'quote_verified' in a and type(a['quote_verified']) is not bool:
            raise Invalid('quote_verified must be boolean')
        if a['kind'] == 'quote' and a.get('quote_verified') is not True:
            raise Invalid('unverified notes cannot become verbatim quotations')
        if a['corroboration'] == 'document_supported' and not a['evidence_ids']:
            raise Invalid('document-supported answers need evidence')
        if a['status'] in ('partial', 'disputed', 'unanswered') and not a['remaining_gap'].strip():
            raise Invalid('unresolved answer status requires a specific remaining gap')
        if 'commitment' in a:
            obj(a['commitment'], ('owner', 'due_date', 'text', 'agreed'), (), 'commitment')
            if a['commitment']['agreed'] is not True:
                raise Invalid('commitment must have been actually agreed')
            for k in ('owner', 'text'):
                text(a['commitment'][k], 'commitment.' + k)
            day(a['commitment']['due_date'], 'commitment.due_date')
    if not isinstance(case['assessment'], dict) or set(case['assessment']) != {f'T{i:02}' for i in range(1, 13)}:
        raise Invalid('assessment must contain exactly T01..T12')
    for tid, entry in case['assessment'].items():
        obj(entry, ('state', 'evidence_ids', 'explanation'), (), tid)
        choice(entry['state'], ASSESSMENT_STATES, tid + '.state')
        refs(entry['evidence_ids'], sources, tid + '.evidence_ids')
        text(entry['explanation'], tid + '.explanation')
        if entry['state'] in ('documented', 'partially_documented') and not entry['evidence_ids']:
            raise Invalid(f'{tid}: documented assessment needs evidence')
    for req in maps['requests'].values():
        validate_request(req, sources)
    if 'private' in case:
        obj(case['private'], (), ('contact', 'notes', 'requester'), 'private')
        for k, v in case['private'].items():
            text(v, 'private.' + k, empty=True)
    if 'review' in case:
        obj(case['review'], ('reviewer', 'at', 'checks'), (), 'review')
        text(case['review']['reviewer'], 'reviewer')
        instant(case['review']['at'], 'review.at')
        strings(case['review']['checks'], 'review.checks')
        if set(case['review']['checks']) != REVIEW_CHECKS:
            raise Invalid('review must attest all required checks')
    canonical(case)
    return copy.deepcopy(case)


def validate_request(r, sources):
    obj(r, ('id', 'scope', 'start_date', 'end_date', 'categories', 'recipient_url', 'recipient_verified_at',
            'fee_ceiling', 'status', 'existing_evidence_ids', 'remaining_gap'),
        ('reference', 'sent_at', 'next_review_date', 'legal_deadline', 'renewal', 'response_ids', 'responsible_role', 'corrections'), 'request')
    for k in ('scope', 'fee_ceiling', 'remaining_gap'):
        text(r[k], 'request.' + k)
    day(r['start_date'], 'start_date')
    day(r['end_date'], 'end_date')
    if r['end_date'] < r['start_date']:
        raise Invalid('request date range reversed')
    strings(r['categories'], 'categories')
    if not r['categories']:
        raise Invalid('request needs bounded categories')
    url(r['recipient_url'], 'recipient_url')
    day(r['recipient_verified_at'], 'recipient_verified_at')
    choice(r['status'], REQUEST_STATES, 'request.status')
    refs(r['existing_evidence_ids'], sources, 'existing_evidence_ids')
    if 'response_ids' in r:
        refs(r['response_ids'], sources, 'response_ids')
    for k in ('sent_at', 'next_review_date'):
        if k in r:
            day(r[k], k)
    for k in ('reference', 'responsible_role', 'corrections'):
        if k in r:
            text(r[k], k)
    if r['status'] not in ('draft', 'withdrawn') and ('sent_at' not in r or 'reference' not in r):
        raise Invalid('submitted requests require an actual sent date and reference')
    if 'legal_deadline' in r:
        obj(r['legal_deadline'], ('date', 'rule_url', 'calculation', 'reviewer', 'verified_at'), (), 'legal_deadline')
        day(r['legal_deadline']['date'], 'legal_deadline.date')
        day(r['legal_deadline']['verified_at'], 'verified_at')
        url(r['legal_deadline']['rule_url'], 'rule_url')
        for k in ('calculation', 'reviewer'):
            text(r['legal_deadline'][k], k)
    if 'renewal' in r:
        obj(r['renewal'], ('date', 'notice_window', 'evidence_id', 'clause'), (), 'renewal')
        day(r['renewal']['date'], 'renewal.date')
        refs([r['renewal']['evidence_id']], sources, 'renewal.evidence_id')
        for k in ('notice_window', 'clause'):
            text(r['renewal'][k], k)


def independence(case, ids):
    sources = {s['id']: s for s in case['sources']}
    # Equal saved-document digests collapse even when a parent edge was omitted.
    same_digest = {}
    root_for = {}
    for original in sources:
        sid = original
        while sources[sid].get('parent_id'):
            sid = sources[sid]['parent_id']
        root_for[original] = sid
    parent = {s: s for s in set(root_for.values())}
    def find(s):
        while parent[s] != s:
            s = parent[s]
        return s
    for sid, source in sources.items():
        sha = source.get('sha256')
        if sha:
            root = find(root_for[sid])
            if sha in same_digest:
                a, b = sorted((root, find(same_digest[sha])))
                parent[b] = a
            same_digest[sha] = root
    roots = set()
    for sid in ids:
        roots.add(find(root_for[sid]))
    return sorted(roots)


def selected_claims(case):
    qs = {q['id']: q for q in case['questions']}
    ids = set(case['why']['claim_ids'])
    for qid in case['selected_questions']:
        ids.update(qs[qid]['claim_ids'])
    return [c for c in case['claims'] if c['id'] in ids]


def ready_errors(case):
    validate(case)
    errors = []
    if 'review' not in case:
        errors.append('Human premise, contrary-evidence, and meeting-rule review is missing.')
    sources = {s['id']: s for s in case['sources']}
    for c in selected_claims(case):
        if c['basis'] != 'open_question' and (not c['evidence_ids'] or c['disposition'] in ('unverified', 'withdrawn')):
            errors.append(f"{c['id']}: factual premise is unsupported, unverified, or withdrawn.")
        for sid in c['evidence_ids']:
            if sources[sid].get('superseded_by'):
                errors.append(f"{c['id']}: {sid} is superseded; revise the premise or cite the current document.")
    return errors
