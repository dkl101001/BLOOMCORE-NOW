# SPDX-License-Identifier: Apache-2.0
"""Deterministic neutral packets and offline town-hall view; no remote assets."""

import base64
import hashlib
import html
import json
import math
from datetime import date

from .model import Invalid, canonical, independence, ready_errors, selected_claims, validate, day
from . import source_digest


ASSESSMENT = [
    ('T01', 'Authorization', 'Who authorized the deployment, when, and through what process?'),
    ('T02', 'Purpose', 'What public purpose and measurable outcomes were specified?'),
    ('T03', 'Equipment', 'What equipment or services were purchased, leased, trialed, donated, or grant-funded?'),
    ('T04', 'Total cost', 'What is the total committed cost including installation, subscriptions, maintenance, and exit?'),
    ('T05', 'Retention', 'What data is collected, inferred, retained, and deleted?'),
    ('T06', 'Access', 'Who may access data, for which purposes, and with whose approval?'),
    ('T07', 'Sharing', 'Which outside entities may receive data or access?'),
    ('T08', 'Review', 'How are misuse, incorrect matches, and complaints reviewed?'),
    ('T09', 'Outcomes', 'What evidence supports benefits, limitations, and unsuccessful outcomes?'),
    ('T10', 'Termination', 'Who owns records, and what happens to them at termination?'),
    ('T11', 'Renewal', 'When does the contract renew, what is the notice window, and who approves?'),
    ('T12', 'Participation', 'How can residents participate and obtain corrections?'),
]


def selected(case):
    qs = {q['id']: q for q in case['questions']}
    return sorted((qs[k] for k in case['selected_questions']), key=lambda q: (q['priority'], q['id']))


def citations(case, question):
    cs = {c['id']: c for c in case['claims']}
    return sorted({s for cid in question['claim_ids'] for s in cs[cid]['evidence_ids'] + cs[cid]['contrary_ids']})


def brief(case):
    lines = ['PUBLIC DECISION BRIEF', f"{case['agency']} | {case['meeting']['date']}",
             f"Agenda: {case['meeting']['agenda_item']}", f"Decision: {case['meeting']['decision']}",
             '', 'Requested action: ' + case['requested_action'], '', 'Why this matters: ' + case['why']['text']]
    claims = {c['id']: c for c in case['claims']}
    for n, q in enumerate(selected(case), 1):
        lines += ['', f"{n}. {q['subject']} ({q['id']})"]
        for cid in q['claim_ids']:
            c = claims[cid]
            lines.append(f"{c['text']} [basis: {c['basis']}; disposition: {c['disposition']}]")
        lines += [q['text'], 'Evidence: ' + (', '.join(citations(case, q)) or 'Open question; no factual premise established.')]
    lines += ['', 'Relevant qualification: ' + case['qualification']]
    for c in selected_claims(case):
        lines.append(f"{c['id']}: {c['qualification']}")
    lines += ['', 'Please identify the supporting record. For anything remaining open, who will respond, by what agreed date, and where can residents find the answer?']
    return '\n'.join(lines) + '\n'


def timing(case):
    words = len(brief(case).split())
    estimate = math.ceil(words * 60 / 120)
    allowance = case['meeting'].get('speaking_seconds')
    # Reserve 20% for pauses; do not hide claims to satisfy the time budget.
    fits = words <= 400 and (allowance is None or estimate <= allowance * .8)
    return {'words': words, 'estimated_seconds_at_120_wpm': estimate, 'allowance_seconds': allowance,
            'untimed': allowance is None, 'within_drafting_budget': fits,
            'note': 'Estimate only; rehearse and shorten for interruptions. Page fit requires print preview.'}


def tracker(case, today):
    rows = []
    for q in selected(case):
        history = [a for a in case['answers'] if a['question_id'] == q['id']]
        latest = history[-1] if history else None
        rows.append({'question_id': q['id'], 'status': latest['status'] if latest else 'unanswered',
                     'remaining_gap': latest['remaining_gap'] if latest else q['gap'], 'history': history})
    requests = []
    for r in case['requests']:
        requests.append({'id': r['id'], 'status': r['status'], 'remaining_gap': r['remaining_gap'],
                         'review_due': bool(r.get('next_review_date') and r['next_review_date'] <= today),
                         'next_review_date': r.get('next_review_date'), 'legal_violation_inferred': False})
    return {'questions': rows, 'requests': requests}


def appendix(case):
    lines = ['EVIDENCE APPENDIX', 'Sources are evidence, not truth certificates. Mirrors are not independent confirmations.']
    for s in case['sources']:
        lines += ['', f"{s['id']}: {s['title']}", f"Issuer: {s['issuer']}",
                  f"Document: {s['document_date']} | Retrieved: {s['retrieved_at']}",
                  f"Source: {s['url']}", f"Location: {s['locator']}",
                  f"{s['content_kind']}: {s['content']}", f"Limits: {s['limits']}",
                  f"SHA-256: {s.get('sha256', 'not supplied; saved-file integrity not established')}",
                  f"Parent: {s.get('parent_id', 'original/unknown')} | Superseded by: {s.get('superseded_by', 'none recorded')}"]
    for c in case['claims']:
        lines += ['', f"Claim {c['id']}: {c['text']}", f"Basis/disposition: {c['basis']} / {c['disposition']}",
                  f"Support: {', '.join(c['evidence_ids']) or 'none'}",
                  f"Contrary: {', '.join(c['contrary_ids']) or 'none identified; not proof none exists'}",
                  f"Underlying support roots (declared lineage): {', '.join(independence(case, c['evidence_ids'])) or 'none'}",
                  'Qualification: ' + c['qualification']]
    return '\n'.join(lines) + '\n'


def assessment(case):
    lines = ['TRANSPARENCY IMPACT ASSESSMENT', 'Independent voluntary questionnaire; not an official form or compliance verdict.']
    for tid, subject, question in ASSESSMENT:
        a = case['assessment'][tid]
        lines += ['', f'{tid} — {subject}: {question}', f"State: {a['state']} | Evidence: {', '.join(a['evidence_ids']) or 'none'}", a['explanation']]
    return '\n'.join(lines) + '\n'


def request_fingerprint(r):
    # Duplicate identity excludes editorial ID, status, and fee changes.
    body = [r['recipient_url'], ' '.join(r['scope'].casefold().split()), r['start_date'], r['end_date'],
            sorted(' '.join(c.casefold().split()) for c in r['categories'])]
    return hashlib.sha256(canonical(body)).hexdigest()


def request_draft(case, request_id, follow_up=False):
    r = next((r for r in case['requests'] if r['id'] == request_id), None)
    if r is None:
        raise Invalid('request not found')
    duplicates = [x['id'] for x in case['requests'] if x['id'] != r['id'] and request_fingerprint(x) == request_fingerprint(r)]
    if duplicates:
        raise Invalid('duplicate scope already logged: ' + ', '.join(duplicates) + '; review that request instead')
    if follow_up:
        if r['status'] in ('draft', 'withdrawn', 'fulfilled', 'closed_unresolved'):
            raise Invalid('follow-up requires an open submitted request')
        return (f"LOCAL FOLLOW-UP DRAFT — not sent\nTo: {r['recipient_url']}\n\nHello,\n\n"
                f"I am following up on {r['reference']}, submitted {r['sent_at']}, concerning {r['scope']}. "
                f"Could you confirm its status, any clarification needed, and the expected next step?\n"
                f"Remaining question: {r['remaining_gap']}\n\nThank you,\n[review and insert name/contact privately]\n")
    if r['status'] != 'draft':
        raise Invalid('request already logged beyond draft; use a focused follow-up')
    categories = '\n'.join(f'{i}. {v}' for i, v in enumerate(r['categories'], 1))
    existing = ', '.join(r['existing_evidence_ids']) or 'none logged'
    return (f"LOCAL RECORDS-REQUEST DRAFT — not sent\nTo: {r['recipient_url']}\n"
            f"Subject: Records concerning {r['scope']}\n\nHello,\n\n"
            f"I request existing records held by {case['agency']} concerning {r['scope']} "
            f"from {r['start_date']} through {r['end_date']}:\n\n{categories}\n\n"
            f"Existing records to check before sending: {existing}. Please omit categories already satisfied by the exact records identified in the final request.\n\n"
            f"Electronic copies or exact document links are welcome. I seek existing records, rather than a new analysis. "
            f"Please provide an estimate before incurring charges above {r['fee_ceiling']}. "
            f"Please contact me if clarification would reduce the search burden. If portions are withheld, "
            f"please identify the stated basis and provide portions you can release.\n\nThank you,\n[review and insert name/contact privately]\n"
            f"\nReview local rules and scope before sending. No statutory deadline is asserted by this template.\n")


def packet(case, receipt, today, humor=False, require_ready=False):
    validate(case)
    day(today, 'as_of')
    errors = ready_errors(case)
    budget = timing(case)
    if not budget['within_drafting_budget']:
        errors.append('Brief exceeds the word/time drafting budget. Shorten it before marking ready.')
    if require_ready and errors:
        raise Invalid('Not ready: ' + ' '.join(errors))
    tracking = tracker(case, today)
    sections = [('Speaking brief', brief(case)), ('Evidence appendix', appendix(case)),
                ('Assessment', assessment(case)), ('Answer tracker', json.dumps(tracking, ensure_ascii=False, indent=2))]
    e = html.escape
    body = ''.join(f'<section><h2>{e(title)}</h2><pre>{e(content)}</pre></section>' for title, content in sections)
    follows = ''.join(f'<details><summary>{e(q["id"])} — follow-up</summary><p>{e(q["follow_up"])}</p></details>' for q in selected(case))
    seconds = case['meeting'].get('speaking_seconds', 0)
    warnings = '\n'.join(errors) if errors else 'Reviewed and within drafting budget; rehearse and verify print layout.'
    banner = 'Your application to observe everyone is pending.' if humor else 'Public accountability packet'
    # Inline JS is fixed, receives no interpolated user text, and can only operate the timer/print UI.
    script = """let handle=null,left=Number(document.querySelector('#clock').dataset.seconds);
const clock=document.querySelector('#clock');function show(){clock.textContent=left?Math.floor(left/60)+':'+String(left%60).padStart(2,'0'):'Time complete';}
document.querySelector('#start').onclick=()=>{if(!handle&&left>0)handle=setInterval(()=>{left--;show();if(left<=0){clearInterval(handle);handle=null;}},1000);};
document.querySelector('#pause').onclick=()=>{clearInterval(handle);handle=null;};
document.querySelector('#reset').onclick=()=>{clearInterval(handle);handle=null;left=Number(clock.dataset.seconds);show();};
document.querySelector('#print').onclick=()=>window.print();if(left)show();"""
    script_hash = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    csp = f"default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-{script_hash}'; base-uri 'none'; form-action 'none'; connect-src 'none'"
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}"><title>Red Tape Dispenser</title>
<style>body{{font:18px/1.5 system-ui;max-width:960px;margin:2rem auto;padding:0 1rem;color:#20202b;background:#faf9f5}}h1{{font-size:2.5rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}}section{{border-top:2px solid #ad263a;margin-top:2rem}}button{{font:inherit;padding:.6rem;margin:.25rem}}aside{{background:#eee4d9;padding:1rem}}@media print{{body{{font:11pt/1.35 serif;margin:0;max-width:none}}section{{break-before:page}}section:first-of-type{{break-before:auto}}nav,details,.controls{{display:none}}pre{{font:inherit}}}}</style></head><body>
<h1>Red Tape Dispenser</h1><p>{e(banner)}</p><aside><b>{'DRAFT' if errors else 'REVIEWED LOCAL DRAFT'}</b><pre>{e(warnings)}</pre>
<p>{budget['words']} brief words; approximately {budget['estimated_seconds_at_120_wpm']} seconds at 120 wpm. {'Untimed: speaking allowance unknown.' if not seconds else 'Timer uses the supplied verified allowance.'} No publication has occurred.</p></aside>
<nav><a href="#brief">Speaking brief</a> · <a href="#follow">Follow-up</a></nav><div class="controls"><p id="clock" data-seconds="{seconds}">{'Untimed' if not seconds else seconds}</p><button id="start">Start timer</button><button id="pause">Pause</button><button id="reset">Reset</button><button id="print">Print packet</button></div>
<div id="brief">{body}</div><div id="follow"><h2>Focused clarifications</h2>{follows}</div>
<footer><p>Local draft. Evidence integrity does not certify truth. Review redactions before any public export.</p><pre>{e(json.dumps(receipt, sort_keys=True))}</pre></footer><script>{script}</script></body></html>'''
    files = {'town_hall.html': document.encode(), 'speaking_brief.txt': brief(case).encode(),
             'evidence_appendix.txt': appendix(case).encode(), 'assessment.txt': assessment(case).encode(),
             'answer_tracker.json': canonical(tracking) + b'\n'}
    manifest = {'module_version': '0.1.0', 'module_source_sha256': source_digest(), 'renderer': 'red-tape-packet-v1', 'revision_receipt': receipt,
                'as_of': today, 'humor': humor, 'state': 'draft' if errors else 'reviewed_local_draft', 'ready_errors': errors,
                'timing': budget, 'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
    files['packet_receipt.json'] = canonical(manifest) + b'\n'
    return files
