"""All ORM models. Importing this package registers every mapper on `Base.metadata`."""
from app.models.agent import AgentRun, AgentStep, AiRecommendation
from app.models.base import Base
from app.models.campaign import Campaign, CampaignStats, CommunicationEvent, Message
from app.models.customer import Customer, Order, OrderItem
from app.models.segment import Segment, SegmentMember

__all__ = [
    "Base",
    "Customer",
    "Order",
    "OrderItem",
    "Segment",
    "SegmentMember",
    "Campaign",
    "Message",
    "CommunicationEvent",
    "CampaignStats",
    "AgentRun",
    "AgentStep",
    "AiRecommendation",
]
