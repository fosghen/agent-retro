import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from agent_retro.cli import main
from agent_retro.models import EvidenceReference, ProposalObservation, ProposalStatus, SchemaError
from agent_retro.store import ProposalStore
