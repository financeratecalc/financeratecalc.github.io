"""Toolset for the temporal taskset: the publisher's tools as they answered on the
episode's date. Same two generic tools as servers/tool.py; outputs that carry a
receipt for a claim the episode's epoch overrides are replaced by that epoch's
reconstructed output (frc_citation.temporal.rewrite_tool_output). The epoch comes
from the task (setup_task), so one server class serves every date.
"""
from __future__ import annotations

import json
import os

import verifiers.v1 as vf

from frc_citation.servers.tool import FrcCitationToolset
from frc_citation.temporal import HERE, epoch_by_id, rewrite_tool_output


class FrcTemporalToolset(FrcCitationToolset):
    TOOL_PREFIX = "frc"
    _epoch: dict | None = None
    _site_root: str = os.environ.get("FRC_SITE_ROOT", os.path.join(HERE, "..", ".."))

    async def setup_task(self, task) -> None:
        # verifiers hands the server the rollout's TaskData (interception `/task` serves
        # `trace.task.data`), not the Task; accept either. First rollout (2026-10-03T16:14)
        # read `task.data` on a TaskData, got None, and served every date the current figures.
        data = task if hasattr(task, "epoch") else getattr(task, "data", None)
        eid = getattr(data, "epoch", None) if data is not None else None
        self._epoch = epoch_by_id(eid) if eid else None
        root = getattr(data, "site_root", None) if data is not None else None
        if root:
            self._site_root = root

    @vf.tool
    def call(self, tool: str, arguments_json: str = "{}") -> str:
        """Call one of the publisher's tools by name with a JSON object of arguments.
        The output is what the publisher's server returned on the date given in the
        question: the figure, its universe, contract fields and a claim receipt. Write
        every figure with its receipt exactly as returned."""
        raw = FrcCitationToolset.call(self, tool, arguments_json)
        if not self._epoch:
            return raw
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        # MCP result shape {content:[{type:text,text:...}]} or a bare object
        if isinstance(obj, dict) and isinstance(obj.get("content"), list):
            for part in obj["content"]:
                if isinstance(part, dict) and part.get("type") == "text":
                    part["text"] = rewrite_tool_output(part["text"], self._site_root, self._epoch)
            return json.dumps(obj)
        return rewrite_tool_output(raw, self._site_root, self._epoch)


if __name__ == "__main__":
    FrcTemporalToolset.run()
