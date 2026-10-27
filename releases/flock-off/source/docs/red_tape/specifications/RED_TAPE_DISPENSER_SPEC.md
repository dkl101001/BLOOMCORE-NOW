# RED TAPE DISPENSER

**Dense with evidence. Economical with words.**

FLOCK OFF companion module · Specification and town-hall packet templates · v0.1 · 2026-10-27

Originating concept: Frazer Love. This is a draft module contract and usable packet template, not implemented software. It neither changes the frozen FLOCK OFF runtime nor assigns a new release version. No jurisdiction, meeting, contract, or deployment has been selected. All bracketed material is a placeholder; examples below are hypothetical.

## 1. What the module does

Turn a specific public decision and its supporting records into three coordinated outputs:

1. A one-page speaking brief containing the decision, up to three material questions, and one requested action.
2. A compact evidence appendix that lets another person check every material assertion.
3. An answer tracker that preserves answers, partial answers, disputes, corrections, and commitments after the meeting.

The design objective is answerability and informed public decision-making. Document count, recipient workload, delay, and number of submissions are not success measures.

**Primary button: DISPENSE RED TAPE.** It prepares a local draft. It does not send, publish, record audio, or create obligations.

## 2. Town Hall Mode

### Prepare

Enter the agency, meeting date, agenda item, proposed decision, and verified official meeting link. Add the actual speaking-time allowance and its source. If meeting rules have not been checked, mark the allowance unknown and produce an untimed draft.

Attach the contract, policy, agenda packet, and existing evaluation documents that bear on the question. Record document dates, versions, page numbers or section anchors, original issuers, URLs, retrieval dates, and local file hashes. Identify copies and mirrors of the same underlying record.

Choose up to three questions. Rank them by relevance to the pending decision, quality of support, and whether an answer could change that decision. Show the ranking reason; do not present a numerical certainty score.

### Review

For each question, preview its factual premise, exact source location, unresolved issue, strongest relevant contrary evidence, and requested answer. Distinguish a missing document from an actual conflict between documents. Require human review before a packet is marked ready.

### Speak

Show a large, offline-readable brief. Display source references beside each question. Provide an optional user-started timer; no microphone access is required. Reading-time estimates are estimates and must allow for interruptions.

The follow-up button reveals one short clarification tied to the unanswered part of the question. It does not generate an endless chain of demands.

### Reconcile

Add an answer manually or cite an official meeting record. Label verbatim quotations, paraphrases, and personal notes separately. Record speaker role, timestamp where available, and source. An unverified note cannot silently become an authenticated quotation.

Suggest an answer status, then require human confirmation. Preserve the full answer and relevant context even when only part addresses the question. Record a commitment only when one was actually made.

### Follow through

Prepare one focused clarification or records-request draft for the remaining gap. Check existing requests and responses first. Ask the user to review the verified recipient, scope, fee language, and content before any future sending capability acts. Public export requires separate review and route/contact-data removal.

## 3. The one-page speaking brief

Use plain formatting and readable type. Target 300–400 words or fewer, reducing the content further when the verified speaking allowance requires it. This is a drafting target, not a guaranteed page or timing result. Move supporting detail to the appendix, never into tiny print.

---

**PUBLIC DECISION BRIEF**

Agency / meeting: [name, date]  
Agenda item / decision: [item and exact action under consideration]  
Packet ID / revision: [ID, revision, date]  
Prepared by: [consenting name or organization]

**Requested action:** [One concrete action the council can consider, such as publishing a written clarification before deciding the item. This is a request, not an asserted legal duty.]

**Why this matters:** [One or two factual sentences linking the evidence gap to cost, authorized use, retention, sharing, oversight, or renewal. Cite evidence IDs.]

**Question 1 — [short subject]**  
[Source-backed premise.] [Precise unresolved issue.] [Single answerable question.] [E-001, page/section]

**Question 2 — [short subject]**  
[Same structure.] [E-002, page/section]

**Question 3 — [short subject]**  
[Same structure, or omit if unnecessary.] [E-003, page/section]

**Relevant qualification:** [Strongest material limitation, explanation, or contrary evidence.]

**Close:** Please identify the record supporting those answers. For anything remaining open, who will respond, by what agreed date, and where will residents be able to find it?

Evidence appendix: [packet attachment / reviewed public link]

---

## 4. Question construction

**Documented premise → decision-relevant gap → bounded question → requested record.**

| Situation | Question pattern | Follow-up if necessary |
| --- | --- | --- |
| Two records appear inconsistent | “Section [X] permits [practice], while policy [Y] states [limit]. How do these provisions operate together, and what written record establishes the applicable limit?” | “Does that explanation address contractual permission, current settings, or both?” |
| Public price omits a category | “The quoted amount covers [listed scope]. What is the committed total including [specific missing category], and which schedule supports it?” | “Is that the current-term total or a projection including renewals?” |
| Outcome claim lacks a method | “The report states [claimed result]. What method and comparison support attributing that result to this deployment?” | “If no evaluation was performed, can the record distinguish reported activity from demonstrated impact?” |
| Sharing scope is unclear | “Which external entities are currently authorized to access these records, and which agreement or policy defines that scope?” | “Does the answer cover current access, permission to share, or both?” |
| Renewal window is unresolved | “Which clause governs renewal and cancellation notice, and which office owns the next review?” | “Can the clause and review date be included in the public record?” |

These are patterns, not factual claims about any vendor or agency. Verify every inserted premise. A contractual permission does not prove actual use; a current setting does not necessarily change contractual permission.

## 5. Evidence appendix

Each evidence item must be independently inspectable:

| Field | Required content |
| --- | --- |
| Evidence ID | Stable local ID such as E-001 |
| Issuer / title | Actual originating organization and document title |
| Version / dates | Document date, effective date if known, retrieval date |
| Exact location | Page, section, clause, table, or stable anchor |
| Source | Original URL or identified local record; distinguish original from mirror |
| Integrity | SHA-256 of saved public document, when available |
| Relevant content | Brief excerpt or faithful paraphrase, clearly labeled |
| Claim supported | Narrow statement supported by this item |
| Limits | What the item does not establish |
| Contrary evidence | IDs and explanations; “none identified” is not “none exists” |
| Lineage / replacements | Common parent, amendments, superseded records |
| Publication review | Redactions, reviewer, date, private/public disposition |

Only attach pages needed to understand the question, while preserving the complete original privately and citing its context. Respect source license and quotation limits. Do not publish raw sensor captures, observer routes, credentials, or unnecessary personal information.

## 6. Answer tracker

| Question ID | Evidence basis | Status | Answer and source | Remaining gap | Agreed owner / date | Next review |
| --- | --- | --- | --- | --- | --- | --- |
| Q-001 | [E-IDs] | unanswered | [blank until answered] | [specific issue] | [only if agreed] | [chosen reminder] |

Allowed statuses:

- **Answered:** the bounded question is addressed; cite the answer and distinguish whether it is corroborated or only an attributed statement.
- **Partial:** record exactly which parts were answered and which remain open.
- **Disputed:** retain the competing statements and evidence together.
- **Unanswered:** no responsive answer has been recorded; make no inference of wrongdoing.
- **Withdrawn / superseded:** preserve the original question, reason, and replacement reference.

Record both status history and the latest status. A new supporting document can resolve an issue; it should not erase the earlier record. Never equate disagreement with failure to answer.

## 7. Software boundary for future implementation

Inputs: agenda metadata, user-supplied public documents, evidence references, questions, manually entered answers, verified meeting rules, and explicit export choices.

Outputs: speaking brief, evidence appendix, answer tracker, focused follow-up draft, and revision receipt.

Suggested local entities: Meeting, Decision, SourceDocument, EvidenceItem, Claim, Question, Answer, Commitment, PacketRevision, PublicationReview.

Every question binds its premise to evidence IDs. Every answer binds to a question and an attribution record. Every packet revision binds the exact selected questions, evidence versions, answer state, and review disposition. These receipts establish reconstruction and integrity; they do not certify the underlying claims as true.

Keep locally measured RF evidence separate from public records. A radio candidate may motivate a question but cannot establish vendor ownership, legality, purpose, or surveillance capability. No automatic public accusations or promotion from unresolved evidence to fact.

The module must work without an account or network connection after inputs are available. Private source files and contact data remain local by default. Remote AI processing, telemetry, publication, or synchronization require deliberate user choices in any later implementation. No background sending or automatic duplicate requests.

## 8. Acceptance scenarios

| Scenario | Required result |
| --- | --- |
| Five websites mirror one contract | One underlying source, five access paths; no independence inflation |
| A factual premise lacks a source | Keep draft; explicitly mark the premise unverified and block ready status until sourced, removed, or rewritten as an open question |
| An amendment resolves an apparent conflict | Surface it, revise or withdraw the question, retain history |
| Strong contrary evidence exists | Place it beside the claim and include the material qualification in the brief |
| An official answers orally without a document | Record an attributed answer; documentary support remains unverified |
| Notes are paraphrases | Never render them as verbatim quotations |
| Response answers only cost, not renewal | Partial status with the exact renewal gap |
| Speaking allowance is unknown or too short | Untimed draft or shorter brief; no false promise of fitting |
| User requests another identical submission | Show the existing request and status; no automatic resend |
| Public export contains contact data or route information | Require removal/redaction before export approval |
| A chosen reminder passes | Mark review due; do not declare a statutory violation |
| New facts undermine the original objection | Correct the packet and preserve the correction visibly |

## 9. Optional personality layer

Home: **Your application to observe everyone is pending.**

Meeting opener: **Please have your supporting documents ready.**

End of timer: **Your time has expired. Your question has not.**

Humor can be disabled. Official-facing briefs default to neutral language. No fake official seals, compulsory-looking forms, unsupported accusations, or fabricated authority.

## 10. First real deployment

To create a completed meeting packet, supply one city or agency, the agenda item or contract, the meeting date, and available records. Then verify current official meeting rules, source documents, contract versions, and any legal assertions before finalizing. No legal deadlines or jurisdiction-specific rights are asserted in this template.

Success is a checked answer, a corrected public record, a clearly owned follow-up, or a better-informed decision. The strongest packet remains willing to change when the evidence changes.
