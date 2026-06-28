"""SkillOpt — Optimize skill documents through bounded edits, trajectory analysis, cross-model validation, and meta-learning.

This module is a re-export hub. Functionality has been split into:
  - skillopt_types: data classes
  - skillopt_traces: trace collection & analysis
  - skillopt_gate: validation gating
  - skillopt_engine: optimization engine
  - skillopt_elite: elite pool management
  - skillopt_audit: audit & fresh agent testing
  - skillopt_moe: MoE router & evolution
"""

import logging

from skillos.evolution.skillopt_audit import *
from skillos.evolution.skillopt_elite import *
from skillos.evolution.skillopt_engine import *
from skillos.evolution.skillopt_gate import *
from skillos.evolution.skillopt_moe import *
from skillos.evolution.skillopt_traces import *
from skillos.evolution.skillopt_types import *

_log = logging.getLogger(__name__)
