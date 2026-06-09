"""Campaign tools — including the approval-gated launch."""
from __future__ import annotations

from pydantic import BaseModel

from app.agents.tools.base import Tool


class LaunchCampaignArgs(BaseModel):
    campaign_id: str


class LaunchCampaignTool(Tool):
    name = "launch_campaign"
    description = "Launch an approved campaign to the channel service. Requires human approval."
    Args = LaunchCampaignArgs
    requires_approval = True  # the runtime refuses this unless the run is approved

    async def run(self, args: LaunchCampaignArgs) -> dict:
        # Real fan-out (create messages, call the channel /v1/send) is wired when the DB is live.
        return {"launched": True, "campaign_id": args.campaign_id}
