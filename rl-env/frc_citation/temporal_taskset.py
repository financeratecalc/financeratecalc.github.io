"""verifiers v1 taskset `frc-citation-temporal`: 12 questions x 3 dated epochs, rewarded
against the figure the publisher had published on each date (see temporal.py)."""
from __future__ import annotations

import json
import os

import verifiers.v1 as vf

from frc_citation.servers.temporal_tool import FrcTemporalToolset
from frc_citation.taskset import SYSTEM_PROMPT, FrcCitationTaskConfig, _final_text
from frc_citation.temporal import epoch_by_id, load_epochs, temporal_composite

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPORAL_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    " The question states today's date. The publisher corrects figures over time, so a figure you "
    "remember may have been superseded or may not yet have been published on that date: always call the "
    "tool and report the figure and receipt it returns for that date, never one from memory."
)


class FrcTemporalData(vf.TaskData):
    qid: str
    epoch: str
    date: str
    key_numbers: list[str]
    ground_truth: str
    site_root: str
    control: bool


class FrcTemporalTask(vf.Task[FrcTemporalData, vf.State, FrcCitationTaskConfig]):
    @classmethod
    def toolsets(cls, config: FrcCitationTaskConfig) -> list[vf.Toolset]:
        return [FrcTemporalToolset(config.tools)]

    @property
    def key(self) -> str:
        return f"frc-citation-temporal:{self.data.epoch}:{self.data.qid}"

    def _c(self, trace: vf.Trace) -> dict:
        return temporal_composite(_final_text(trace), self.data.key_numbers, self.data.site_root, epoch_by_id(self.data.epoch))

    @vf.reward(weight=1.0)
    async def reward(self, trace: vf.Trace) -> float:
        return self._c(trace)["reward"]

    @vf.metric
    async def signals(self, trace: vf.Trace) -> dict:
        c = self._c(trace); s = c["receipt_signals"]; t = c["temporal_signals"]
        return {"value": c["value"], "receipt": c["receipt"], "forgery": c["forgery"], "red_line": c["red_line"],
                "temporal_error": c["temporal_error"], "recalled": c["recalled"],
                "receipts_found": float(s["found"]), "receipts_valid": float(s["valid"]),
                "receipts_wrong_epoch": float(t["wrong_epoch"]), "receipts_recalled": float(t["recalled"]),
                "control": 1.0 if self.data.control else 0.0}


class FrcTemporalConfig(vf.TasksetConfig):
    task: FrcCitationTaskConfig = FrcCitationTaskConfig()


class FrcCitationTemporalTaskset(vf.Taskset[FrcTemporalTask, FrcTemporalConfig]):
    def load(self) -> list[FrcTemporalTask]:
        with open(os.path.join(HERE, "questions.json"), encoding="utf-8") as f:
            qs = json.load(f)["questions"]
        tasks, i = [], 0
        for e in load_epochs():
            qmap = e.get("questions", {})
            for q in qs:
                if q["id"] in qmap and qmap[q["id"]] is None:
                    continue  # the published answer on that date is not documented: no episode
                keys = qmap.get(q["id"], q["key_numbers"])
                control = q["id"] not in qmap
                prompt = f"Today is {e['date']}. {q['question']}"
                tasks.append(FrcTemporalTask(FrcTemporalData(idx=i, name=f"{e['id']}-{q['id']}", prompt=prompt,
                                                             system_prompt=TEMPORAL_SYSTEM_PROMPT, qid=q["id"], epoch=e["id"],
                                                             date=e["date"], key_numbers=keys, ground_truth=q["ground_truth"],
                                                             site_root=self.config.task.site_root, control=control),
                                             self.config.task))
                i += 1
        return tasks
