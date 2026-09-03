"""Baseline systems used in controlled comparisons."""

from .head_match import HeadMatchBaseline
from .mention_pair import MentionPairLogisticBaseline

__all__ = ["HeadMatchBaseline", "MentionPairLogisticBaseline"]
