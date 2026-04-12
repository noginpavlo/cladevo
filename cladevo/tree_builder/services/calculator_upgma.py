"""
Phylogenetic tree construction pipeline.

Provides the TreeBuilder orchestrator and its constituent single-responsibility
collaborators: SequenceAligner, DistanceMatrixCalculator,
PhylogeneticTreeConstructor, and TreeVisualizer.
"""

import os
import subprocess
import tempfile
import uuid
from typing import List, Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from Bio import AlignIO, Phylo
from Bio.Align import MultipleSeqAlignment
from Bio.Phylo.TreeConstruction import (
    DistanceCalculator,
    DistanceTreeConstructor,
    BaseTree,
)
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

matplotlib.use("Agg")


class SequenceAligner:
    """Produces a MultipleSeqAlignment from raw sequences, FASTA files, or Excel files."""

    def align_sequences(
        self,
        list1: Optional[List[str]] = None,
        list2: Optional[List[str]] = None,
        fasta_file: Optional[str] = None,
    ) -> Optional[MultipleSeqAlignment]:
        """Align DNA sequences using ClustalW and return the resulting alignment.

        Accepts either a pair of parallel lists (names and sequences) or a path
        to an existing FASTA file.  Returns None if ClustalW fails or the output
        alignment file cannot be read.
        """
        if not (list1 and list2) and not fasta_file:
            raise ValueError("No data passed to align_sequences")

        if list1 and list2:
            input_path = self._write_temp_fasta(list1, list2)
        else:
            input_path = fasta_file

        output_aln = self._run_clustalw(input_path)
        if output_aln is None:
            return None

        return self._read_alignment(output_aln)

    def reformat(self, xls_file_path: str) -> Optional[MultipleSeqAlignment]:
        """Convert an Excel SSR genotyping file into a MultipleSeqAlignment.

        Binary marker values (1 / 0) are encoded as nucleotides (A / T) so the
        resulting alignment is compatible with Biopython's distance calculator.
        Returns None if an error occurs during processing.
        """
        try:
            data = pd.read_excel(xls_file_path)
            data = data.dropna()
            seq_records = self._excel_rows_to_seq_records(data)
            self._write_clustal_aln_file(data)
            return MultipleSeqAlignment(seq_records)
        except Exception as e:
            return None

    def _write_temp_fasta(self, names: List[str], sequences: List[str]) -> str:
        """Write name/sequence pairs to a temporary FASTA file and return its path."""
        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".fasta"
        ) as temp_fasta:
            for seq in sequences:
                if isinstance(seq, str):
                    record = SeqRecord(Seq(seq), id=f"{names[sequences.index(seq)]}")
                temp_fasta.write(f">{record.id}\n{record.seq}\n")
            return temp_fasta.name

    def _run_clustalw(self, input_path: str) -> Optional[str]:
        """Invoke ClustalW on the given FASTA file and return the output .aln path.

        Returns None if the subprocess exits with a non-zero status.
        Removes both the input FASTA and the output .aln file after reading,
        but only removes the input when it was a temporary file created internally.
        """
        output_aln = input_path.replace(".fasta", "_aligned.aln")
        clustal_command = [
            "/usr/bin/clustalw",
            f"-INFILE={input_path}",
            f"-OUTFILE={output_aln}",
            "-ALIGN",
        ]
        try:
            subprocess.run(clustal_command, check=True)
        except subprocess.CalledProcessError:
            return None
        return output_aln

    def _read_alignment(self, aln_path: str) -> Optional[MultipleSeqAlignment]:
        """Read a Clustal-format alignment file and return a MultipleSeqAlignment.

        Cleans up the .aln file after reading. Returns None if the file is missing.
        """
        try:
            alignment = AlignIO.read(aln_path, "clustal")
        except FileNotFoundError:
            return None
        finally:
            fasta_path = aln_path.replace("_aligned.aln", ".fasta")
            if os.path.exists(fasta_path):
                os.remove(fasta_path)
            if os.path.exists(aln_path):
                os.remove(aln_path)

        return alignment

    def _excel_rows_to_seq_records(
        self, data: pd.DataFrame
    ) -> List[SeqRecord]:
        """Convert DataFrame rows into SeqRecord objects with encoded sequences."""
        seq_records = []
        for _, row in data.iterrows():
            seq_id = str(row.iloc[0]).replace(" ", "")
            sequence = "".join(map(str, row.iloc[1:].values))
            sequence = sequence.replace("1", "A").replace("0", "T")
            seq_records.append(SeqRecord(Seq(sequence), id=seq_id))
        return seq_records

    def _write_clustal_aln_file(self, data: pd.DataFrame) -> None:
        """Write a Clustal-format .aln file from a DataFrame and then remove it."""
        output_path = "static/uploads/sequence_aligned.aln"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as aln_file:
            aln_file.write("CLUSTAL W (1.83) multiple sequence alignment\n\n")
            for _, row in data.iterrows():
                seq_id = str(row.iloc[0]).replace(" ", "")
                sequence = "".join(map(str, row.iloc[1:].values))
                sequence = sequence.replace("1", "A").replace("0", "T")
                aln_file.write(f"{seq_id:<10} {sequence}\n")
        os.remove(output_path)


class DistanceMatrixCalculator:
    """Computes a pairwise distance matrix from a multiple sequence alignment."""

    def calculate(
        self, alignment: MultipleSeqAlignment
    ) -> Optional[object]:
        """Return an identity-based distance matrix for the given alignment.

        Prints each record and the resulting matrix for diagnostic purposes.
        Returns None if the alignment is None.
        """
        if alignment is None:
            return None

        calculator = DistanceCalculator("identity")
        return calculator.get_distance(alignment)


class PhylogeneticTreeConstructor:
    """Builds a phylogenetic tree from a distance matrix using UPGMA or NJ."""

    def build(
        self, distance_matrix: object, method: str
    ) -> Optional[BaseTree.Tree]:
        """Construct and return a phylogenetic tree using the specified method.

        Accepted method values are 'upgma' and 'nj' (case-insensitive).
        Returns None if the distance matrix is None.
        Raises ValueError for unrecognised method names.
        """
        if distance_matrix is None:
            return None

        constructor = DistanceTreeConstructor()
        if method.lower() == "upgma":
            return constructor.upgma(distance_matrix)
        if method.lower() == "nj":
            return constructor.nj(distance_matrix)
        raise ValueError(f"Unsupported method: {method}. Use 'upgma' or 'nj'.")


class TreeVisualizer:
    """Renders a phylogenetic tree to a PNG file and returns a unique identifier."""

    def visualize(
        self,
        tree: Optional[BaseTree.Tree],
        output_file: Optional[str] = None,
        output_format: str = "png",
    ) -> Optional[str]:
        """Draw the tree and save it to disk, returning the UUID used in the filename.

        Saves to static/plots/ by default.  Clears internal node labels before
        drawing.  Returns None if tree is None.
        """
        if tree is None:
            return None

        save_directory = os.path.join("static", "plots")
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        unique_id = str(uuid.uuid4())

        if output_file is None:
            output_file = os.path.join(
                save_directory, f"tree_{unique_id}.{output_format}"
            )

        self._strip_internal_labels(tree)
        self._render_and_save(tree, output_file, output_format)

        return unique_id

    def _strip_internal_labels(self, tree: BaseTree.Tree) -> None:
        """Remove name labels from all internal (non-terminal) nodes."""
        for clade in tree.find_clades():
            if not clade.is_terminal():
                clade.name = None

    def _render_and_save(
        self,
        tree: BaseTree.Tree,
        output_file: str,
        output_format: str,
    ) -> None:
        """Create the Matplotlib figure, draw the tree, and write it to disk."""
        fig = plt.figure(figsize=(18, 12))
        ax = fig.add_subplot(1, 1, 1)

        Phylo.draw(
            tree,
            axes=ax,
            do_show=False,
            branch_labels=lambda c: (
                f"{c.branch_length:.3f}" if c.branch_length != 0 else None
            ),
        )

        for text in ax.texts:
            if text.get_text():
                text.set_fontsize(14)
                text.set_weight("bold")

        ax.set_facecolor("whitesmoke")

        plt.savefig(output_file, format=output_format, dpi=300)
        plt.close(fig)


class TreeBuilder:
    """Orchestrates the full phylogenetic tree construction pipeline.

    Delegates each stage to a focused collaborator:
    alignment → distance matrix → tree construction → visualization.
    Intermediate results are retained on instance attributes so that callers
    can invoke the stages individually in sequence.
    """

    def __init__(self) -> None:
        """Initialise the pipeline with empty state and collaborator instances."""
        self.aligned_file: Optional[MultipleSeqAlignment] = None
        self.dissimilarity_matrix: Optional[object] = None
        self.tree: Optional[BaseTree.Tree] = None
        self.n_seq: int = 2

        self._aligner = SequenceAligner()
        self._matrix_calculator = DistanceMatrixCalculator()
        self._tree_constructor = PhylogeneticTreeConstructor()
        self._visualizer = TreeVisualizer()

    def align_sequences(
        self,
        list1: Optional[List[str]] = None,
        list2: Optional[List[str]] = None,
        fasta_file: Optional[str] = None,
    ) -> None:
        """Align sequences and store the result in self.aligned_file.

        Accepts either parallel name/sequence lists or a FASTA file path.
        """
        self.aligned_file = self._aligner.align_sequences(list1, list2, fasta_file)

    def reformat(self, xls_file_path: str) -> None:
        """Parse an Excel SSR file and store the encoded alignment in self.aligned_file."""
        self.aligned_file = self._aligner.reformat(xls_file_path)

    def calculate_dissimilarity_matrix(self) -> None:
        """
        Compute the distance matrix from self.aligned_file and store in self.dissimilarity_matrix.
        """
        self.dissimilarity_matrix = self._matrix_calculator.calculate(self.aligned_file)

    def build_tree(self, method: str) -> None:
        """Build the phylogenetic tree from self.dissimilarity_matrix and store in self.tree."""
        self.tree = self._tree_constructor.build(self.dissimilarity_matrix, method)

    def visualize_tree(
        self,
        output_file: Optional[str] = None,
        output_format: str = "png",
    ) -> Optional[str]:
        """Render self.tree to a PNG and return the UUID portion of the filename."""
        return self._visualizer.visualize(self.tree, output_file, output_format)
