"""Knowledge Lineage — full data provenance from source to wisdom.

This module is a re-export hub. Functionality has been split into:
  - lineage_types: data classes
  - lineage_graph: LineageGraph class
  - lineage_core: core logic (cross-references, persistence)
  - lineage_wisdom: consolidation, pattern mining
  - lineage_cycle: full knowledge cycle
  - lineage_precip: skill precipitation events
"""

import logging

from skillos.knowledge.lineage_core import *
from skillos.knowledge.lineage_cycle import *
from skillos.knowledge.lineage_graph import *

# Explicit re-exports for private utilities used by tests
from skillos.knowledge.lineage_precip import *
from skillos.knowledge.lineage_types import *
from skillos.knowledge.lineage_wisdom import *

_log = logging.getLogger(__name__)
