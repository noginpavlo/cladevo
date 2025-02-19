import subprocess
import pandas as pd
import tempfile
from Bio import AlignIO
from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
import os
import matplotlib.pyplot as plt
from Bio import Phylo
import matplotlib
import uuid

matplotlib.use('Agg')

class TreeBuilder:
    def __init__(self):
        self.aligned_file = None
        self.dissimilarity_matrix = None
        self.tree = None
        self.n_seq = 2


    def align_sequences(self, list1=None, list2=None, fasta_file=None):

        if not (list1 and list2) and not fasta_file:
            raise ValueError("No data passed to align_sequences")

        elif list1 and list2:
            # Create a temporary FASTA file to hold the input sequences
            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.fasta') as temp_fasta:
                for seq in list2:
                    if isinstance(seq, str):
                        seq = SeqRecord(Seq(seq), id=f"{list1[list2.index(seq)]}")
                    temp_fasta.write(f">{seq.id}\n{seq.seq}\n")
                temp_fasta_name = temp_fasta.name  # Save the temp file name

        elif fasta_file:
            # Use the provided FASTA file directly
            temp_fasta_name = fasta_file

        # Run ClustalW to align the sequences
        output_aln = temp_fasta_name.replace('.fasta', '_aligned.aln')  # Define output file

        clustal_command = [
            '/usr/bin/clustalw',
            f'-INFILE={temp_fasta_name}',
            f'-OUTFILE={output_aln}',
            '-ALIGN'
        ]

        # Run the ClustalW command
        try:
            subprocess.run(clustal_command, check=True)
        except subprocess.CalledProcessError as e:
            # print(f"Error running ClustalW: {e}")
            return

        # Read the alignment from the generated .aln file
        try:
            alignment = AlignIO.read(output_aln, "clustal")
            print("Alignment executed")

        except FileNotFoundError:
            print(f"Alignment file not found: {output_aln}")
            return

        self.aligned_file = alignment
        print(self.aligned_file)

        os.remove(temp_fasta_name)
        os.remove(output_aln)

    def reformat(self, xls_file_path):
        """
        Processes an Excel file to create a correctly structured .aln file and
        generates a MultipleSeqAlignment object.

        :param xls_file_path: Path to the Excel file.
        """
        try:
            # Read the Excel file into a DataFrame
            data = pd.read_excel(xls_file_path)

            # Ensure there are no empty rows or columns
            data = data.dropna()

            # Prepare the output path for the .aln file
            output_path = "static/uploads/sequence_aligned.aln"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Initialize list to store SeqRecords for alignment
            seq_records = []

            # Open the file for writing in Clustal format
            with open(output_path, 'w') as aln_file:
                # Write the Clustal header
                aln_file.write("CLUSTAL W (1.83) multiple sequence alignment\n\n")

                # Iterate through each row of the DataFrame
                for _, row in data.iterrows():
                    # Extract sequence ID from the first column
                    seq_id = str(row.iloc[0]).replace(" ", "")

                    # Create the sequence by concatenating the remaining columns
                    sequence = ''.join(map(str, row.iloc[1:].values))

                    # Replace '1' with 'A' and '0' with 'T'
                    sequence = sequence.replace('1', 'A').replace('0', 'T')

                    # Write to the .aln file in Clustal format
                    aln_file.write(f"{seq_id:<10} {sequence}\n")

                    # Create a SeqRecord and add it to the list
                    seq_records.append(SeqRecord(Seq(sequence), id=seq_id))

            # Create a MultipleSeqAlignment object from the SeqRecords
            alignment = MultipleSeqAlignment(seq_records)

            # Assign the alignment to the class attribute
            self.aligned_file = alignment

            # Clean up: Remove the temporary .aln file
            os.remove(output_path)

        except Exception as e:
            print(f"An error occurred: {e}")


    def calculate_dissimilarity_matrix(self):
        if self.aligned_file is None:
            print("No alignment data available. Run align_sequences first.")
            return

        print("Loaded alignment:")
        for record in self.aligned_file:
            print(f"{record.id}: {record.seq}")

        calculator = DistanceCalculator("identity")
        distance_matrix = calculator.get_distance(self.aligned_file)

        print("\nDissimilarity Matrix:")
        print(distance_matrix)

        self.dissimilarity_matrix = distance_matrix


    def build_tree(self, method):
        if self.dissimilarity_matrix is None:
            print("No distance matrix available. Run calculate_dissimilarity_matrix first.")
            return

        constructor = DistanceTreeConstructor()
        if method.lower() == "upgma":
            tree = constructor.upgma(self.dissimilarity_matrix)
        elif method.lower() == "nj":
            tree = constructor.nj(self.dissimilarity_matrix)
        else:
            raise ValueError(f"Unsupported method: {method}. Use 'upgma' or 'nj'.")

        self.tree = tree

    def visualize_tree(self, output_file=None, output_format="png"):
        if self.tree is None:
            print("No tree data available. Build tree first.")
            return

        """
        Visualizes and optionally exports the phylogenetic tree with custom sample name styles.

        :param output_file: Path to save the tree image (e.g., 'tree.png' or 'tree.jpg')
        :param output_format: Format of the output file ('png', 'jpeg', etc.)
        """
        # Define the directory for saving plots
        save_directory = os.path.join("static", "plots")

        # Ensure the directory exists; create it if it doesn't
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # If no output file is provided, use a default filename
        if output_file is None:
            # Generate a unique ID and use it to create a unique file name
            unique_id = str(uuid.uuid4())
            print(unique_id)
            output_file = os.path.join(save_directory, f"tree_{unique_id}.{output_format}")

        # Remove internal node labels (set name to None)
        for clade in self.tree.find_clades():
            if not clade.is_terminal():
                clade.name = None  # Remove the label of internal nodes

        # Create a new Matplotlib figure
        fig = plt.figure(figsize=(18, 12))
        ax = fig.add_subplot(1, 1, 1)

        Phylo.draw(self.tree, axes=ax, do_show=False,
                   branch_labels=lambda c: f"{c.branch_length:.3f}" if c.branch_length != 0 else None)

        for text in ax.texts:
            if text.get_text():
                text.set_fontsize(14)
                text.set_weight('bold')

        ax.set_facecolor("whitesmoke")

        # Save the tree image
        plt.savefig(output_file, format=output_format, dpi=300)  # High resolution
        # print(f"Tree saved to {output_file} in {output_format} format.")

        # Close the figure to release memory and suppress GUI
        plt.close(fig)

        # Return the unique ID
        return unique_id
