import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from Bio.Align import MultipleSeqAlignment
from Bio.Phylo.TreeConstruction import BaseTree, DistanceCalculator, DistanceTreeConstructor
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from tree_builder.services.calculator_upgma import (
    DistanceMatrixCalculator,
    PhylogeneticTreeConstructor,
    SequenceAligner,
    TreeBuilder,
    TreeVisualizer,
)

MODULE = "tree_builder.services.calculator_upgma"

_ALIGNMENT = MultipleSeqAlignment([
    SeqRecord(Seq("ACGT"), id="seq1"),
    SeqRecord(Seq("ACGT"), id="seq2"),
    SeqRecord(Seq("TGCA"), id="seq3"),
])


def _make_distance_matrix() -> object:
    """Return a real DistanceMatrix built from _ALIGNMENT."""
    calculator = DistanceCalculator("identity")
    return calculator.get_distance(_ALIGNMENT)


def _make_tree(method: str = "upgma") -> BaseTree.Tree:
    """Return a real phylogenetic tree built from _ALIGNMENT."""
    dm = _make_distance_matrix()
    constructor = DistanceTreeConstructor()
    return constructor.upgma(dm) if method == "upgma" else constructor.nj(dm)


class TestSequenceAligner(unittest.TestCase):
    """Unit tests for SequenceAligner."""

    def setUp(self) -> None:
        """Create a fresh SequenceAligner for each test."""
        self.aligner = SequenceAligner()

    # --- align_sequences ---

    def test_align_sequences_raises_when_no_args(self) -> None:
        """ValueError is raised when neither lists nor a FASTA file are supplied."""
        with self.assertRaises(ValueError):
            self.aligner.align_sequences()

    def test_align_sequences_with_lists_delegates_to_write_temp_fasta(self) -> None:
        """When lists are given, _write_temp_fasta is called with those lists."""
        with patch.object(
            self.aligner, "_write_temp_fasta", return_value="/tmp/t.fasta"
        ) as mock_write, \
             patch.object(self.aligner, "_run_clustalw", return_value="/tmp/t_aligned.aln"), \
             patch.object(self.aligner, "_read_alignment", return_value=_ALIGNMENT):
            self.aligner.align_sequences(["seq1"], ["ACGT"])
            mock_write.assert_called_once_with(["seq1"], ["ACGT"])

    def test_align_sequences_with_fasta_skips_write_temp_fasta(self) -> None:
        """When a FASTA file is given, _write_temp_fasta is not called."""
        with patch.object(self.aligner, "_write_temp_fasta") as mock_write, \
             patch.object(self.aligner, "_run_clustalw", return_value="/tmp/t_aligned.aln"), \
             patch.object(self.aligner, "_read_alignment", return_value=_ALIGNMENT):
            self.aligner.align_sequences(fasta_file="/tmp/t.fasta")
            mock_write.assert_not_called()

    def test_align_sequences_returns_none_when_clustalw_fails(self) -> None:
        """None is returned when ClustalW fails (i.e. _run_clustalw returns None)."""
        with patch.object(self.aligner, "_write_temp_fasta", return_value="/tmp/t.fasta"), \
             patch.object(self.aligner, "_run_clustalw", return_value=None):
            result = self.aligner.align_sequences(["seq1"], ["ACGT"])
            self.assertIsNone(result)

    def test_align_sequences_returns_alignment_on_success(self) -> None:
        """The alignment from _read_alignment is returned on the happy path."""
        with patch.object(self.aligner, "_write_temp_fasta", return_value="/tmp/t.fasta"), \
             patch.object(self.aligner, "_run_clustalw", return_value="/tmp/t_aligned.aln"), \
             patch.object(self.aligner, "_read_alignment", return_value=_ALIGNMENT):
            result = self.aligner.align_sequences(["seq1"], ["ACGT"])
            self.assertEqual(result, _ALIGNMENT)

    # --- _write_temp_fasta ---

    def test_write_temp_fasta_creates_valid_fasta_file(self) -> None:
        """A valid FASTA file is created with correct content and its path returned."""
        names = ["seq1", "seq2"]
        sequences = ["ACGT", "TGCA"]
        path = self.aligner._write_temp_fasta(names, sequences)
        try:
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as fh:
            with open(path) as fh:
                content = fh.read()
            self.assertIn(">seq1\nACGT\n", content)
            self.assertIn(">seq2\nTGCA\n", content)
        finally:
            if os.path.exists(path):
                os.remove(path)

    # --- _run_clustalw ---

    def test_run_clustalw_returns_aln_path_on_success(self) -> None:
        """The expected .aln output path is returned when ClustalW succeeds."""
        with patch(f"{MODULE}.subprocess.run"):
            result = self.aligner._run_clustalw("/tmp/t.fasta")
            self.assertEqual(result, "/tmp/t_aligned.aln")

    def test_run_clustalw_returns_none_on_called_process_error(self) -> None:
        """None is returned when the ClustalW subprocess exits non-zero."""
        error = subprocess.CalledProcessError(1, "clustalw")
        with patch(f"{MODULE}.subprocess.run", side_effect=error):
            result = self.aligner._run_clustalw("/tmp/t.fasta")
            self.assertIsNone(result)

    # --- _read_alignment ---

    def test_read_alignment_returns_alignment(self) -> None:
        """The alignment object is returned when the .aln file is readable."""
        with patch(f"{MODULE}.AlignIO.read", return_value=_ALIGNMENT), \
             patch(f"{MODULE}.os.path.exists", return_value=True), \
             patch(f"{MODULE}.os.remove"):
            result = self.aligner._read_alignment("/tmp/t_aligned.aln")
            self.assertEqual(result, _ALIGNMENT)

    def test_read_alignment_returns_none_when_file_missing(self) -> None:
        """None is returned when AlignIO cannot find the alignment file."""
        with patch(f"{MODULE}.AlignIO.read", side_effect=FileNotFoundError()), \
             patch(f"{MODULE}.os.path.exists", return_value=False), \
             patch(f"{MODULE}.os.remove"):
            result = self.aligner._read_alignment("/tmp/t_aligned.aln")
            self.assertIsNone(result)

    def test_read_alignment_cleans_up_both_files(self) -> None:
        """Both the .fasta and .aln files are removed in the finally block."""
        with patch(f"{MODULE}.AlignIO.read", return_value=_ALIGNMENT), \
             patch(f"{MODULE}.os.path.exists", return_value=True), \
             patch(f"{MODULE}.os.remove") as mock_remove:
            self.aligner._read_alignment("/tmp/t_aligned.aln")
            mock_remove.assert_any_call("/tmp/t.fasta")
            mock_remove.assert_any_call("/tmp/t_aligned.aln")

    # --- _excel_rows_to_seq_records ---

    def test_excel_rows_to_seq_records_encodes_correctly(self) -> None:
        """Marker values 1→A and 0→T; spaces are stripped from the sequence ID."""
        data = pd.DataFrame({
            "name": ["Sample 1", "Sample2"],
            "marker1": [1, 0],
            "marker2": [0, 1],
        })
        records = self.aligner._excel_rows_to_seq_records(data)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].id, "Sample1")
        self.assertEqual(str(records[0].seq), "AT")
        self.assertEqual(records[1].id, "Sample2")
        self.assertEqual(str(records[1].seq), "TA")

    # --- reformat ---

    def test_reformat_returns_alignment_from_valid_excel(self) -> None:
        """A MultipleSeqAlignment with the correct number of sequences is returned."""
        mock_df = pd.DataFrame({
            "name": ["seq1", "seq2"],
            "marker1": [1, 0],
            "marker2": [0, 1],
        })
        with patch(f"{MODULE}.pd.read_excel", return_value=mock_df), \
             patch.object(self.aligner, "_write_clustal_aln_file"):
            result = self.aligner.reformat("/fake/path.xlsx")
            self.assertIsInstance(result, MultipleSeqAlignment)
            self.assertEqual(len(result), 2)

    def test_reformat_returns_none_on_exception(self) -> None:
        """None is returned when reading the Excel file raises an exception."""
        with patch(f"{MODULE}.pd.read_excel", side_effect=ValueError("bad file")):
            result = self.aligner.reformat("/fake/path.xlsx")
            self.assertIsNone(result)


class TestDistanceMatrixCalculator(unittest.TestCase):
    """Unit tests for DistanceMatrixCalculator."""

    def setUp(self) -> None:
        """Create a fresh DistanceMatrixCalculator for each test."""
        self.calculator = DistanceMatrixCalculator()

    def test_calculate_returns_none_when_alignment_is_none(self) -> None:
        """None is returned without raising when alignment is None."""
        result = self.calculator.calculate(None)
        self.assertIsNone(result)

    def test_calculate_returns_distance_matrix_with_correct_names(self) -> None:
        """A distance matrix whose names match the alignment sequence IDs is returned."""
        result = self.calculator.calculate(_ALIGNMENT)
        self.assertIsNotNone(result)
        self.assertEqual(set(result.names), {"seq1", "seq2", "seq3"})


class TestPhylogeneticTreeConstructor(unittest.TestCase):
    """Unit tests for PhylogeneticTreeConstructor."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build a shared distance matrix once for all tree-construction tests."""
        cls.distance_matrix = _make_distance_matrix()

    def setUp(self) -> None:
        """Create a fresh PhylogeneticTreeConstructor for each test."""
        self.constructor = PhylogeneticTreeConstructor()

    def test_build_returns_none_when_matrix_is_none(self) -> None:
        """None is returned when distance_matrix is None."""
        result = self.constructor.build(None, "upgma")
        self.assertIsNone(result)

    def test_build_upgma_returns_tree(self) -> None:
        """A BaseTree.Tree is returned for the 'upgma' method."""
        tree = self.constructor.build(self.distance_matrix, "upgma")
        self.assertIsInstance(tree, BaseTree.Tree)

    def test_build_nj_returns_tree(self) -> None:
        """A BaseTree.Tree is returned for the 'nj' method."""
        tree = self.constructor.build(self.distance_matrix, "nj")
        self.assertIsInstance(tree, BaseTree.Tree)

    def test_build_upgma_case_insensitive(self) -> None:
        """'UPGMA' (uppercase) is accepted and returns a tree."""
        tree = self.constructor.build(self.distance_matrix, "UPGMA")
        self.assertIsInstance(tree, BaseTree.Tree)

    def test_build_nj_case_insensitive(self) -> None:
        """'NJ' (uppercase) is accepted and returns a tree."""
        tree = self.constructor.build(self.distance_matrix, "NJ")
        self.assertIsInstance(tree, BaseTree.Tree)

    def test_build_raises_for_unknown_method(self) -> None:
        """ValueError is raised for an unrecognised method name."""
        with self.assertRaises(ValueError):
            self.constructor.build(self.distance_matrix, "foo")


class TestTreeVisualizer(unittest.TestCase):
    """Unit tests for TreeVisualizer."""

    def setUp(self) -> None:
        """Create a fresh TreeVisualizer for each test."""
        self.visualizer = TreeVisualizer()

    def test_visualize_returns_none_when_tree_is_none(self) -> None:
        """None is returned when tree is None."""
        result = self.visualizer.visualize(None)
        self.assertIsNone(result)

    def test_visualize_returns_uuid_string(self) -> None:
        """A UUID string is returned on the happy path."""
        fake_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with patch(f"{MODULE}.uuid.uuid4", return_value=fake_uuid), \
             patch(f"{MODULE}.os.path.exists", return_value=True), \
             patch(f"{MODULE}.os.makedirs"), \
             patch.object(self.visualizer, "_render_and_save"):
            result = self.visualizer.visualize(_make_tree())
            self.assertEqual(result, str(fake_uuid))

    def test_visualize_creates_directory_when_missing(self) -> None:
        """os.makedirs is called when the output directory does not exist."""
        with patch(f"{MODULE}.os.path.exists", return_value=False), \
             patch(f"{MODULE}.os.makedirs") as mock_makedirs, \
             patch(f"{MODULE}.uuid.uuid4", return_value="test-uuid"), \
             patch.object(self.visualizer, "_render_and_save"):
            self.visualizer.visualize(_make_tree())
            mock_makedirs.assert_called_once()

    def test_visualize_passes_custom_output_file_to_render(self) -> None:
        """When output_file is provided, it is forwarded to _render_and_save unchanged."""
        tree = _make_tree()
        with patch(f"{MODULE}.os.path.exists", return_value=True), \
             patch(f"{MODULE}.os.makedirs"), \
             patch(f"{MODULE}.uuid.uuid4", return_value="test-uuid"), \
             patch.object(self.visualizer, "_render_and_save") as mock_render:
            self.visualizer.visualize(tree, output_file="/custom/output.png")
            mock_render.assert_called_once_with(tree, "/custom/output.png", "png")

    def test_strip_internal_labels_clears_internal_node_names(self) -> None:
        """All internal (non-terminal) clade names are set to None."""
        tree = _make_tree()
        self.visualizer._strip_internal_labels(tree)
        for clade in tree.find_clades():
            if not clade.is_terminal():
                self.assertIsNone(clade.name)

    def test_strip_internal_labels_preserves_terminal_names(self) -> None:
        """Terminal (leaf) clade names are not modified."""
        tree = _make_tree()
        terminal_names_before = {c.name for c in tree.get_terminals()}
        self.visualizer._strip_internal_labels(tree)
        terminal_names_after = {c.name for c in tree.get_terminals()}
        self.assertEqual(terminal_names_before, terminal_names_after)

    def test_render_and_save_calls_savefig_with_correct_args(self) -> None:
        """plt.savefig is called with the expected path, format, and dpi."""
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_ax.texts = []
        mock_fig.add_subplot.return_value = mock_ax
        with patch(f"{MODULE}.plt.figure", return_value=mock_fig), \
             patch(f"{MODULE}.plt.savefig") as mock_savefig, \
             patch(f"{MODULE}.plt.close"), \
             patch(f"{MODULE}.Phylo.draw"):
            self.visualizer._render_and_save(_make_tree(), "/tmp/output.png", "png")
            mock_savefig.assert_called_once_with("/tmp/output.png", format="png", dpi=300)


class TestTreeBuilder(unittest.TestCase):
    """Unit tests for the TreeBuilder orchestrator."""

    def setUp(self) -> None:
        """Create a fresh TreeBuilder for each test."""
        self.builder = TreeBuilder()

    def test_init_state_is_empty(self) -> None:
        """Pipeline attributes start as None and n_seq defaults to 2."""
        self.assertIsNone(self.builder.aligned_file)
        self.assertIsNone(self.builder.dissimilarity_matrix)
        self.assertIsNone(self.builder.tree)
        self.assertEqual(self.builder.n_seq, 2)

    def test_init_creates_correct_collaborator_types(self) -> None:
        """Each collaborator attribute is an instance of the expected class."""
        self.assertIsInstance(self.builder._aligner, SequenceAligner)
        self.assertIsInstance(self.builder._matrix_calculator, DistanceMatrixCalculator)
        self.assertIsInstance(self.builder._tree_constructor, PhylogeneticTreeConstructor)
        self.assertIsInstance(self.builder._visualizer, TreeVisualizer)

    def test_align_sequences_stores_result_in_aligned_file(self) -> None:
        """The return value of _aligner.align_sequences is stored as aligned_file."""
        mock_alignment = MagicMock()
        self.builder._aligner.align_sequences = MagicMock(return_value=mock_alignment)
        self.builder.align_sequences(["seq1"], ["ACGT"])
        self.assertEqual(self.builder.aligned_file, mock_alignment)

    def test_reformat_stores_result_in_aligned_file(self) -> None:
        """The return value of _aligner.reformat is stored as aligned_file."""
        mock_alignment = MagicMock()
        self.builder._aligner.reformat = MagicMock(return_value=mock_alignment)
        self.builder.reformat("/fake/path.xlsx")
        self.assertEqual(self.builder.aligned_file, mock_alignment)

    def test_calculate_dissimilarity_matrix_stores_result(self) -> None:
        """The distance matrix is stored in dissimilarity_matrix."""
        mock_matrix = MagicMock()
        self.builder._matrix_calculator.calculate = MagicMock(return_value=mock_matrix)
        self.builder.calculate_dissimilarity_matrix()
        self.assertEqual(self.builder.dissimilarity_matrix, mock_matrix)

    def test_build_tree_stores_result_in_tree(self) -> None:
        """The built tree is stored in self.tree."""
        mock_tree = MagicMock()
        self.builder._tree_constructor.build = MagicMock(return_value=mock_tree)
        self.builder.build_tree("upgma")
        self.assertEqual(self.builder.tree, mock_tree)

    def test_visualize_tree_returns_value_from_visualizer(self) -> None:
        """The return value of _visualizer.visualize is passed through unchanged."""
        self.builder._visualizer.visualize = MagicMock(return_value="some-uuid")
        result = self.builder.visualize_tree()
        self.assertEqual(result, "some-uuid")


if __name__ == "__main__":
    unittest.main()
