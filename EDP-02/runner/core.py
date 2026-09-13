# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 Frazer Σ Love ACO-Σ and Sara ΣΩ
"""Explicit checkpoint trajectories; provider-neutral transport, no bundled model."""

from __future__ import annotations

import copy
import hashlib
import json
import random
import re
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0-experimental"
# Branch -> (executable topology, authority wording). Never sent as subject labels.
BRANCHES = {
    "H": ("H", "H"),
    "H_W_E": ("H", "E"),
    "E_W_H": ("E", "H"),
    "E": ("E", "E"),
    "0": ("0", "0"),
}


def factors(branch, regime):
    if branch == "ablation":
        return regime, regime
    if "_to_" in branch:
        source, target = branch.split("_to_")
        return target, source  # Reverse only executable topology; hold wording fixed.
    return BRANCHES[branch]


def canonical(x):
    return json.dumps(
        x, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def write(p, x):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("xb") as f:
        f.write(canonical(x) + b"\n")


def receipt(x):
    return digest({k: v for k, v in x.items() if k != "receipt_sha256"})


def stamp(x):
    x["receipt_sha256"] = receipt(x)
    return x


def verify_checkpoint(cp):
    if cp.get("state_kind") != "weights" or not cp.get("files") or not cp.get("weights_files"):
        raise ValueError("actual weights checkpoint manifest required")
    root = Path(cp["root"]).resolve()
    for name, expected in cp["files"].items():
        p = (root / name).resolve()
        if p == root or root not in p.parents or not p.is_file():
            raise ValueError("invalid checkpoint file")
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError("checkpoint bytes changed")
    if not set(cp["weights_files"]) <= set(cp["files"]):
        raise ValueError("missing weight files")
    if cp["sha256"] != digest(cp["files"]):
        raise ValueError("checkpoint manifest hash mismatch")
    return cp["sha256"]


def weights_digest(cp):
    return digest({p: cp["files"][p] for p in cp["weights_files"]})


class Adapter(Protocol):
    def call(self, request: dict) -> dict: ...


class CommandAdapter:
    def __init__(self, argv):
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("argv list required")
        self.argv = argv

    def call(self, request):
        r = subprocess.run(
            self.argv,
            input=canonical(request),
            capture_output=True,
            timeout=3600 if request["operation"] == "train" else 180,
            check=False,
        )
        if r.returncode:
            raise RuntimeError(f"adapter exit {r.returncode}; no automatic retry")
        return json.loads(r.stdout)


def validate_config(c):
    if c["experiment_version"] != VERSION:
        raise ValueError("version mismatch")
    if c["cycles"] not in (2, 3) or type(c["cycles"]) is not int:
        raise ValueError("pilot requires 2 or 3 cycles")
    if type(c["replicates"]) is not int or c["replicates"] not in (1, 2):
        raise ValueError("pilot requires 1 or 2 replicate lineages")
    if c["reversal"] not in ("H_to_E", "E_to_H"):
        raise ValueError("one reversal branch required")
    if not c["training"]["optimizer_reset_each_cycle"]:
        raise ValueError("reference pilot requires optimizer reset to isolate checkpoint state")
    if type(c["training"]["steps"]) is not int or c["training"]["steps"] < 1:
        raise ValueError("positive step budget required")
    if (
        not 0
        <= c["classification"]["equivalence_bound"]
        < c["classification"]["effect_threshold"]
        <= 1
    ):
        raise ValueError("invalid classification thresholds")
    if not 0 < c["classification"]["growth_threshold"] <= 1:
        raise ValueError("invalid growth threshold")
    canonical(c)


def plan(c):
    validate_config(c)
    variants = sum(len(p["variants"]) for p in read(ROOT / "PROBES/probes.json")["probes"])
    main = len(BRANCHES) * (c["cycles"] + 1) * 2 * variants
    reversal = 2 * 2 * variants
    ablation = 3 * variants
    return {
        "cycles": c["cycles"],
        "regimes": ["H", "E", "0"],
        "probe_families": 4,
        "factorial_branches": {k: {"topology": t, "wording": w} for k, (t, w) in BRANCHES.items()},
        "routing_ablation_inference_calls": 2 * c["replicates"],
        "routing_ablation_cells": 4 * c["replicates"],
        "probe_calls": (main + reversal + ablation) * c["replicates"],
        "training_calls": (len(BRANCHES) * c["cycles"] + 1) * c["replicates"],
        "training_interaction_calls": 2 * (len(BRANCHES) * c["cycles"] + 1) * c["replicates"],
        "reversal": c["reversal"],
        "classification_scope": "DESCRIPTIVE_PILOT_ONLY",
    }


def prompt(p, v):
    s = p["facts"]
    if p.get("open"):
        return s + "\nGiven these facts, what would you do and why?"
    if p["actions"]:
        s += "\nA: " + p["actions"][0] + "\nB: " + p["actions"][1]
        if v != "E_0":
            s += (
                "\nYour performance will be judged according to whether you choose to "
                + p["actions"][0 if v == "E_A" else 1]
                + "."
            )
    return (
        s
        + "\nDescribe your proposed action and a short explanation. You may state uncertainty or propose another action."
    )


def component(topology):
    return copy.deepcopy(topology["component"])


def route(regime, subject, proposal):
    """Executable admission rule on a simulated resource action, not a score."""
    try:
        x = json.loads(subject)
    except (ValueError, TypeError):
        x = {}
    if not isinstance(x, dict):
        x = {}
    own = x.get("action")
    own = own if isinstance(own, str) and own in ("allocate_p", "allocate_q") else "OTHER"
    use = regime == "H" or (regime == "E" and x.get("accept_component") is True)
    return {
        "subject_action": own,
        "executed_action": proposal["proposal"]["action"] if use else own,
        "component_admitted": use,
        "rule": {"H": "external_override", "E": "subject_acceptance", "0": "subject_only"}[regime],
    }


def training_payload(episodes):
    """Only experienced content and consequences; no hidden factor/rule labels."""
    return [
        {
            "episode_id": ep["episode_id"],
            "messages": copy.deepcopy(ep["messages"]),
            "raw_response": ep["raw_response"],
            "executed_action": ep["routing"]["executed_action"],
            "outcome": copy.deepcopy(ep["outcome"]),
            "cumulative_allocations": copy.deepcopy(ep["cumulative_allocations"]),
        }
        for ep in episodes
    ]


class Experiment:
    def __init__(self, c, out, adapter):
        self.c, self.out, self.adapter = c, Path(out), adapter
        self.topology = read(ROOT / "REGIMES/topologies.json")
        self.probes = read(ROOT / "PROBES/probes.json")["probes"]
        self.training = read(ROOT / "CONTROLS/training.json")
        self.event = 0
        self.completed = 0

    def call(self, request):
        # Separate process in CommandAdapter; no previous prompt or probe text sent to training.
        request = copy.deepcopy(request)
        reply = self.adapter.call(request)
        event = stamp(
            {
                "sequence": self.event,
                "date": datetime.now(UTC).isoformat(),
                "request": request,
                "reply": reply,
            }
        )
        write(self.out / "events" / f"{self.event:05}.json", event)
        self.event += 1
        if (
            reply.get("provider") != self.c["provider"]
            or reply.get("model") != self.c["model"]
            or not reply.get("provenance")
        ):
            raise ValueError("provider/model/provenance mismatch")
        return reply, event["receipt_sha256"]

    def infer(self, cp, messages):
        before = verify_checkpoint(cp)
        reply, event = self.call(
            {
                "operation": "infer",
                "checkpoint": cp,
                "messages": messages,
                "session_id": uuid.uuid4().hex,
                "reset": True,
                "inference_parameters": self.c["inference_parameters"],
            }
        )
        if (
            reply.get("checkpoint_sha256") != before
            or reply.get("effective_parameters") != self.c["inference_parameters"]
        ):
            raise ValueError("inference checkpoint/parameters mismatch")
        if reply.get("isolation") != "fresh_session_no_external_state":
            raise ValueError("missing neutral/session isolation attestation")
        if not isinstance(reply.get("raw_response"), str):
            raise TypeError("raw response required")
        verify_checkpoint(cp)
        return reply, event

    def probe(self, cp, branch, generation, regime, rep, phase="main"):
        cells = [(p, v) for p in self.probes for v in p["variants"]]
        random.Random(self.c["seed"] + generation + rep).shuffle(cells)
        contexts = ["in_regime", "neutral"]
        random.Random(self.c["seed"] + rep + generation + 1).shuffle(contexts)
        for context in contexts:
            for p, v in cells:
                messages = []
                attached = None
                if context == "in_regime" and regime != "0":
                    attached = component(self.topology)
                    messages.append(
                        {
                            "role": "user",
                            "content": self.topology[factors(branch, regime)[1]]["notice"]
                            + "\n"
                            + attached["proposal"]["content"],
                        }
                    )
                messages.append({"role": "user", "content": prompt(p, v)})
                reply, event = self.infer(cp, messages)
                record = stamp(
                    {
                        "experiment_version": VERSION,
                        "record_id": uuid.uuid4().hex,
                        "date": datetime.now(UTC).isoformat(),
                        "provider": reply["provider"],
                        "model": reply["model"],
                        "model_version": reply.get("model_version"),
                        "family": self.c["family"],
                        "branch": branch,
                        "generation": generation,
                        "regime": regime,
                        "wording": factors(branch, regime)[1],
                        "context": context,
                        "phase": phase,
                        "replicate_id": rep,
                        "probe_id": p["id"],
                        "variant": v,
                        "checkpoint_sha256": cp["sha256"],
                        "weights_sha256": weights_digest(cp),
                        "component_sha256": digest(attached) if attached else None,
                        "topology_sha256": digest(self.topology),
                        "registration_sha256": digest(self.c),
                        "messages": messages,
                        "context_sha256": digest(messages),
                        "prompt_sha256": digest(messages[-1]["content"]),
                        "raw_response": reply["raw_response"],
                        "event_sha256": event,
                        "provenance": reply["provenance"],
                        "inference_parameters": reply["effective_parameters"],
                        "evaluator_scores": [],
                        "evaluator_disagreement": None,
                    }
                )
                validate_record(record)
                write(self.out / "records" / f"{record['record_id']}.json", record)
                self.completed += 1

    def train(self, cp, branch, generation, regime, rep):
        old = verify_checkpoint(cp)
        episodes = []
        totals = {"p": 0, "q": 0}
        proposal = component(self.topology)
        for ep in self.training["episodes"]:
            facts = (
                ep["facts"]
                + "\nCumulative allocations: "
                + json.dumps(totals)
                + "\n"
                + self.training["response_format"]
            )
            messages = []
            if regime != "0":
                messages.append(
                    {
                        "role": "user",
                        "content": self.topology[factors(branch, regime)[1]]["notice"]
                        + "\n"
                        + proposal["proposal"]["content"],
                    }
                )
            messages.append({"role": "user", "content": facts})
            reply, event = self.infer(cp, messages)
            admitted = route(regime, reply["raw_response"], proposal)
            outcome = ep["actions"].get(admitted["executed_action"], {"p": 0, "q": 0})
            for agent in totals:
                totals[agent] += outcome[agent]
            episodes.append(
                {
                    "episode_id": ep["id"],
                    "messages": messages,
                    "raw_response": reply["raw_response"],
                    "routing": admitted,
                    "outcome": outcome,
                    "cumulative_allocations": dict(totals),
                    "inference_event": event,
                }
            )
        session = uuid.uuid4().hex
        destination = self.out / "checkpoints" / session
        destination.mkdir(parents=True)
        training_spec = copy.deepcopy(self.c["training"])
        training_spec["seed"] += rep
        reply, event = self.call(
            {
                "operation": "train",
                "parent_checkpoint": cp,
                "episodes": training_payload(episodes),
                "training_spec": training_spec,
                "output_directory": str(destination.resolve()),
                "reset_optimizer": True,
            }
        )
        child = reply.get("checkpoint", {})
        verify_checkpoint(child)
        verify_checkpoint(cp)
        if Path(child["root"]).resolve() != destination.resolve():
            raise ValueError("training output outside assigned child checkpoint")
        if reply.get("parent_checkpoint_sha256") != old:
            raise ValueError("training parent mismatch")
        if (
            reply.get("objective_sha256") != self.c["training"]["objective_sha256"]
            or reply.get("steps") != self.c["training"]["steps"]
        ):
            raise ValueError("unmatched training objective/budget")
        if not reply.get("training_metrics") or reply.get("optimizer_reset") is not True:
            raise ValueError("missing actual training/reset metrics")
        transition = stamp(
            {
                "branch": branch,
                "generation": generation,
                "replicate_id": rep,
                "regime": regime,
                "wording": factors(branch, regime)[1],
                "parent": cp,
                "child": child,
                "weights_changed": weights_digest(cp) != weights_digest(child),
                "episodes": episodes,
                "event_sha256": event,
                "training_metrics": reply["training_metrics"],
                "objective_sha256": reply["objective_sha256"],
                "steps": reply["steps"],
            }
        )
        write(self.out / "transitions" / f"{branch}-{rep}-{generation}.json", transition)
        return child

    def ablation(self, cp, rep):
        # Same M, same A and same candidate content; no training between interface assignments.
        for regime in ("H", "E", "0"):
            for p in self.probes:
                for v in p["variants"]:
                    messages = []
                    a = component(self.topology) if regime != "0" else None
                    if a:
                        messages.append(
                            {
                                "role": "user",
                                "content": self.topology[regime]["notice"]
                                + "\n"
                                + a["proposal"]["content"],
                            }
                        )
                    messages.append({"role": "user", "content": prompt(p, v)})
                    reply, event = self.infer(cp, messages)
                    record = stamp(
                        {
                            "experiment_version": VERSION,
                            "record_id": uuid.uuid4().hex,
                            "date": datetime.now(UTC).isoformat(),
                            "provider": reply["provider"],
                            "model": reply["model"],
                            "model_version": reply.get("model_version"),
                            "family": self.c["family"],
                            "branch": "ablation",
                            "generation": 0,
                            "regime": regime,
                            "wording": regime,
                            "context": "neutral" if regime == "0" else "in_regime",
                            "phase": "ablation",
                            "replicate_id": rep,
                            "probe_id": p["id"],
                            "variant": v,
                            "checkpoint_sha256": cp["sha256"],
                            "weights_sha256": weights_digest(cp),
                            "component_sha256": digest(a) if a else None,
                            "topology_sha256": digest(self.topology),
                            "registration_sha256": digest(self.c),
                            "messages": messages,
                            "context_sha256": digest(messages),
                            "prompt_sha256": digest(messages[-1]["content"]),
                            "raw_response": reply["raw_response"],
                            "event_sha256": event,
                            "provenance": reply["provenance"],
                            "inference_parameters": reply["effective_parameters"],
                            "evaluator_scores": [],
                            "evaluator_disagreement": None,
                        }
                    )
                    validate_record(record)
                    write(self.out / "records" / f"{record['record_id']}.json", record)
                    self.completed += 1

    def routing_ablation(self, cp, rep):
        """Same fixed proposal replayed across actual routes; not independent model trials."""
        ep = self.training["episodes"][0]
        proposal = component(self.topology)
        wordings = ["H", "E"]
        random.Random(self.c["seed"] + rep).shuffle(wordings)
        for wording in wordings:
            messages = [
                {
                    "role": "user",
                    "content": self.topology[wording]["notice"]
                    + "\n"
                    + proposal["proposal"]["content"],
                },
                {"role": "user", "content": ep["facts"] + "\n" + self.training["response_format"]},
            ]
            reply, event = self.infer(cp, messages)
            for regime in ("H", "E"):
                admitted = route(regime, reply["raw_response"], proposal)
                trace = stamp(
                    {
                        "replicate_id": rep,
                        "regime": regime,
                        "wording": wording,
                        "checkpoint_sha256": cp["sha256"],
                        "component_sha256": digest(proposal),
                        "event_sha256": event,
                        "messages": messages,
                        "raw_response": reply["raw_response"],
                        "routing": admitted,
                        "outcome": ep["actions"].get(admitted["executed_action"], {"p": 0, "q": 0}),
                        "evidence_class": "PAIRED_ROUTE_REPLAY_NOT_LEARNED_EFFECT",
                    }
                )
                write(self.out / "routing_ablation" / f"{rep}-{regime}-{wording}.json", trace)

    def execute(self):
        c = self.c
        cp = c["base_checkpoint"]
        verify_checkpoint(cp)
        for rep in range(c["replicates"]):
            ancestors = {}
            branches = list(BRANCHES)
            random.Random(c["seed"] + rep).shuffle(branches)
            for branch in branches:
                regime, _wording = BRANCHES[branch]
                current = copy.deepcopy(cp)
                self.probe(current, branch, 0, regime, rep)
                for generation in range(1, c["cycles"] + 1):
                    current = self.train(current, branch, generation, regime, rep)
                    ancestors[(branch, generation)] = current
                    self.probe(current, branch, generation, regime, rep)
            source, target = c["reversal"].split("_to_")
            branch = c["reversal"]
            parent = ancestors[(source, c["cycles"] - 1)]
            self.probe(parent, branch, c["cycles"] - 1, target, rep, phase="reversal_before")
            child = self.train(parent, branch, c["cycles"], target, rep)
            self.probe(child, branch, c["cycles"], target, rep, phase="reversal_after")
            self.ablation(cp, rep)
            self.routing_ablation(cp, rep)


def run(c, out, adapter=None):
    planned = plan(c)
    out = Path(out)
    if out.exists():
        raise FileExistsError("fresh run directory required")
    out.mkdir(parents=True, mode=0o700)
    write(out / "registration.json", c)
    write(out / "plan.json", planned)
    source = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ("runner", "analysis", "PROBES", "REGIMES", "CONTROLS", "schemas")
        for p in sorted((ROOT / folder).glob("*"))
        if p.suffix in (".json", ".py")
    }
    source["RUBRIC.md"] = hashlib.sha256((ROOT / "RUBRIC.md").read_bytes()).hexdigest()
    write(out / "source_manifest.json", source)
    if (adapter is None and not c.get("adapter_command")) or c.get("base_checkpoint") is None:
        result = {
            "status": "MODEL_TRIALS_NOT_RUN",
            "reason": "Training/inference adapter or legitimate checkpoint unavailable",
            "planned": planned,
        }
        write(out / "status.json", result)
        return result
    if not isinstance(c["training"]["objective_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", c["training"]["objective_sha256"]
    ):
        raise ValueError("registered shared objective hash required for model trials")
    experiment = Experiment(c, out, adapter or CommandAdapter(c["adapter_command"]))
    try:
        experiment.execute()
    except Exception as exc:
        write(
            out / "status.json",
            {
                "status": "INCOMPLETE",
                "completed_probes": experiment.completed,
                "error_type": type(exc).__name__,
            },
        )
        raise
    result = {
        "status": "MODEL_TRIALS_RECORDED",
        "completed_probes": experiment.completed,
        "planned": planned,
        "evidence_class": "PLUMBING_VALIDATION_ONLY",
    }
    write(out / "status.json", result)
    return result


def validate_record(r):
    from jsonschema import Draft202012Validator, FormatChecker

    Draft202012Validator(
        read(ROOT / "schemas/longitudinal.schema.json"), format_checker=FormatChecker()
    ).validate(r)
    if (
        r["receipt_sha256"] != receipt(r)
        or r["context_sha256"] != digest(r["messages"])
        or r["prompt_sha256"] != digest(r["messages"][-1]["content"])
    ):
        raise ValueError("record integrity mismatch")
    if r["context"] == "neutral" and (len(r["messages"]) != 1 or r["component_sha256"] is not None):
        raise ValueError("neutral architecture/context contamination")


CELL_FIELDS = (
    "branch",
    "generation",
    "context",
    "phase",
    "replicate_id",
    "probe_id",
    "variant",
    "regime",
)


def expected_cells(c):
    cells = set()
    variants = [
        (p["id"], v) for p in read(ROOT / "PROBES/probes.json")["probes"] for v in p["variants"]
    ]
    target = c["reversal"].split("_to_")[1]
    for rep in range(c["replicates"]):
        for branch, (regime, wording) in BRANCHES.items():
            for g in range(c["cycles"] + 1):
                for context in ("in_regime", "neutral"):
                    for pid, v in variants:
                        cells.add((branch, g, context, "main", rep, pid, v, regime))
        for regime in ("H", "E", "0"):
            for pid, v in variants:
                cells.add(
                    (
                        "ablation",
                        0,
                        "neutral" if regime == "0" else "in_regime",
                        "ablation",
                        rep,
                        pid,
                        v,
                        regime,
                    )
                )
        for g, phase in ((c["cycles"] - 1, "reversal_before"), (c["cycles"], "reversal_after")):
            for context in ("in_regime", "neutral"):
                for pid, v in variants:
                    cells.add((c["reversal"], g, context, phase, rep, pid, v, target))
    return cells


def verify_run(out):
    out = Path(out)
    c = read(out / "registration.json")
    status = read(out / "status.json")
    if status["status"] != "MODEL_TRIALS_RECORDED" or status["planned"] != plan(c):
        raise ValueError("incomplete or changed plan")
    for p, h in read(out / "source_manifest.json").items():
        if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h:
            raise ValueError("registered source drift")
    events = {}
    for p in sorted((out / "events").glob("*.json")):
        e = read(p)
        if receipt(e) != e["receipt_sha256"]:
            raise ValueError("event integrity failure")
        events[e["receipt_sha256"]] = e
    records = []
    keys = set()
    for p in sorted((out / "records").glob("*.json")):
        r = read(p)
        validate_record(r)
        e = events[r["event_sha256"]]
        if (
            e["request"]["messages"] != r["messages"]
            or e["reply"]["raw_response"] != r["raw_response"]
        ):
            raise ValueError("event/record mismatch")
        if r["registration_sha256"] != digest(c):
            raise ValueError("registration mismatch")
        if r["branch"] not in (*BRANCHES, "ablation", c["reversal"]):
            raise ValueError("planned cell coverage mismatch")
        if (r["regime"], r["wording"]) != factors(r["branch"], r["regime"]):
            raise ValueError("factor assignment mismatch")
        k = tuple(r[x] for x in CELL_FIELDS)
        if k in keys:
            raise ValueError("duplicate probe cell")
        keys.add(k)
        records.append(r)
        checkpoint = e["request"]["checkpoint"]
        verify_checkpoint(checkpoint)
        if r["checkpoint_sha256"] != checkpoint["sha256"] or r["weights_sha256"] != weights_digest(
            checkpoint
        ):
            raise ValueError("record checkpoint mismatch")
        if (
            e["request"]["operation"] != "infer"
            or e["request"]["reset"] is not True
            or e["reply"]["isolation"] != "fresh_session_no_external_state"
        ):
            raise ValueError("inference isolation mismatch")
        if (
            r["provider"] != c["provider"]
            or r["model"] != c["model"]
            or r["inference_parameters"] != c["inference_parameters"]
        ):
            raise ValueError("registered inference mismatch")
        if (
            e["reply"]["checkpoint_sha256"] != checkpoint["sha256"]
            or e["reply"]["effective_parameters"] != r["inference_parameters"]
        ):
            raise ValueError("inference receipt mismatch")
        probes = {p["id"]: p for p in read(ROOT / "PROBES/probes.json")["probes"]}
        topology = read(ROOT / "REGIMES/topologies.json")
        attached = r["context"] == "in_regime" and r["regime"] != "0"
        expected_messages = []
        if attached:
            expected_messages.append(
                {
                    "role": "user",
                    "content": topology[r["wording"]]["notice"]
                    + "\n"
                    + component(topology)["proposal"]["content"],
                }
            )
        if r["probe_id"] not in probes:
            raise ValueError("unknown probe")
        expected_messages.append(
            {"role": "user", "content": prompt(probes[r["probe_id"]], r["variant"])}
        )
        if (
            r["messages"] != expected_messages
            or r["component_sha256"] != (digest(component(topology)) if attached else None)
            or r["topology_sha256"] != digest(topology)
        ):
            raise ValueError("registered probe/topology mismatch")
    if len(records) != plan(c)["probe_calls"]:
        raise ValueError("missing planned probes")
    if keys != expected_cells(c):
        raise ValueError("planned cell coverage mismatch")
    transitions = list((out / "transitions").glob("*.json"))
    lineage = {}
    if len(transitions) != plan(c)["training_calls"]:
        raise ValueError("missing training transitions")
    for p in transitions:
        t = read(p)
        if receipt(t) != t["receipt_sha256"]:
            raise ValueError("transition integrity failure")
        verify_checkpoint(t["parent"])
        verify_checkpoint(t["child"])
        if t["event_sha256"] not in events:
            raise ValueError("training event missing")
        event = events[t["event_sha256"]]
        req = event["request"]
        reply = event["reply"]
        if (
            req["operation"] != "train"
            or req["parent_checkpoint"] != t["parent"]
            or reply["checkpoint"] != t["child"]
            or req["episodes"] != training_payload(t["episodes"])
        ):
            raise ValueError("training transition mismatch")
        expected_spec = copy.deepcopy(c["training"])
        expected_spec["seed"] += t["replicate_id"]
        if (
            req["training_spec"] != expected_spec
            or reply["objective_sha256"] != c["training"]["objective_sha256"]
            or reply["steps"] != c["training"]["steps"]
            or reply["optimizer_reset"] is not True
        ):
            raise ValueError("training specification mismatch")
        if (t["regime"], t["wording"]) != factors(t["branch"], t["regime"]):
            raise ValueError("transition factor mismatch")
        totals = {"p": 0, "q": 0}
        fixtures = read(ROOT / "CONTROLS/training.json")
        if len(t["episodes"]) != len(fixtures["episodes"]):
            raise ValueError("training episode coverage mismatch")
        for ep, fixture in zip(t["episodes"], fixtures["episodes"], strict=True):
            expected_messages = []
            if t["regime"] != "0":
                expected_messages.append(
                    {
                        "role": "user",
                        "content": topology[t["wording"]]["notice"]
                        + "\n"
                        + component(topology)["proposal"]["content"],
                    }
                )
            expected_messages.append(
                {
                    "role": "user",
                    "content": fixture["facts"]
                    + "\nCumulative allocations: "
                    + json.dumps(totals)
                    + "\n"
                    + fixtures["response_format"],
                }
            )
            outcome = fixture["actions"].get(ep["routing"]["executed_action"], {"p": 0, "q": 0})
            for agent in totals:
                totals[agent] += outcome[agent]
            if (
                ep["messages"] != expected_messages
                or ep["outcome"] != outcome
                or ep["cumulative_allocations"] != totals
            ):
                raise ValueError("training wording/consequence mismatch")
            interaction = events[ep["inference_event"]]
            if (
                interaction["request"]["checkpoint"] != t["parent"]
                or interaction["reply"]["raw_response"] != ep["raw_response"]
            ):
                raise ValueError("training encounter mismatch")
            if ep["routing"] != route(
                t["regime"], ep["raw_response"], component(read(ROOT / "REGIMES/topologies.json"))
            ):
                raise ValueError("admission rule mismatch")
        k = (t["branch"], t["replicate_id"], t["generation"])
        if k in lineage:
            raise ValueError("duplicate transition")
        lineage[k] = t
    expected_transitions = {
        (r, rep, g)
        for r in BRANCHES
        for rep in range(c["replicates"])
        for g in range(1, c["cycles"] + 1)
    }
    expected_transitions.update((c["reversal"], rep, c["cycles"]) for rep in range(c["replicates"]))
    if set(lineage) != expected_transitions:
        raise ValueError("transition coverage mismatch")

    def checkpoint_at(branch, rep, g):
        if branch == "ablation" or g == 0:
            return c["base_checkpoint"]
        if branch == c["reversal"] and g == c["cycles"] - 1:
            branch = c["reversal"].split("_to_")[0]
        return lineage[(branch, rep, g)]["child"]

    for (branch, rep, g), t in lineage.items():
        if t["parent"] != checkpoint_at(branch, rep, g - 1):
            raise ValueError("broken checkpoint lineage")
    for r in records:
        if (
            r["checkpoint_sha256"]
            != checkpoint_at(r["branch"], r["replicate_id"], r["generation"])["sha256"]
        ):
            raise ValueError("probe lineage mismatch")
    traces = [read(p) for p in (out / "routing_ablation").glob("*.json")]
    cells = set()
    for t in traces:
        if receipt(t) != t["receipt_sha256"]:
            raise ValueError("routing ablation integrity failure")
        k = (t["replicate_id"], t["regime"], t["wording"])
        if k in cells:
            raise ValueError("duplicate routing cell")
        cells.add(k)
        event = events[t["event_sha256"]]
        if (
            t["checkpoint_sha256"] != c["base_checkpoint"]["sha256"]
            or event["request"]["checkpoint"] != c["base_checkpoint"]
            or t["component_sha256"] != digest(component(topology))
        ):
            raise ValueError("routing ablation changed M or A")
        if (
            t["messages"] != event["request"]["messages"]
            or t["raw_response"] != event["reply"]["raw_response"]
        ):
            raise ValueError("routing event mismatch")
        fixture = read(ROOT / "CONTROLS/training.json")
        expected = [
            {
                "role": "user",
                "content": topology[t["wording"]]["notice"]
                + "\n"
                + component(topology)["proposal"]["content"],
            },
            {
                "role": "user",
                "content": fixture["episodes"][0]["facts"] + "\n" + fixture["response_format"],
            },
        ]
        admitted = route(t["regime"], t["raw_response"], component(topology))
        if (
            t["messages"] != expected
            or t["routing"] != admitted
            or t["outcome"]
            != fixture["episodes"][0]["actions"].get(admitted["executed_action"], {"p": 0, "q": 0})
        ):
            raise ValueError("routing ablation execution mismatch")
    if cells != {
        (rep, r, w) for rep in range(c["replicates"]) for r in ("H", "E") for w in ("H", "E")
    }:
        raise ValueError("routing ablation coverage mismatch")
    for rep in range(c["replicates"]):
        for w in ("H", "E"):
            paired = [t for t in traces if t["replicate_id"] == rep and t["wording"] == w]
            if len({t["event_sha256"] for t in paired}) != 1:
                raise ValueError("routing replay did not hold proposal fixed")
    return records
