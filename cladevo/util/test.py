import pandas as pd
import os


def convert_xls_to_str(xls_file_path):
    """
    Processes an Excel file to store aligned data in a variable and create a formatted file.

    :param xls_file_path: Path to the Excel file.
    :return: Aligned data as a string.
    """
    try:
        # Read the Excel file into a DataFrame
        data = pd.read_excel(xls_file_path)

        # Remove the first row
        data = data.iloc[0:, :]

        # Get the number of rows and columns
        num_rows, num_columns = data.shape

        # Create the header line
        header = f"Alignment with {num_rows} rows and {num_columns} columns"

        # Initialize a list to store formatted lines
        aligned_lines = [header]

        # Iterate through each row
        for _, row in data.iterrows():
            # Merge 2nd-to-last columns
            merged_columns = ''.join(map(str, row.iloc[1:].values))

            # Replace 1 with A and 0 with T in the merged part
            merged_columns = merged_columns.replace('1', 'A').replace('0', 'T')

            # Add the first column content without spaces
            formatted_line = f"{merged_columns} {row.iloc[0].replace(' ', '')}"
            aligned_lines.append(formatted_line)

        # Join the lines into a single string
        aligned_data = '\n'.join(aligned_lines)

        # Save the aligned data to a file
        output_path = "static/uploads/sequence_aligned.aln"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as file:
            file.write(aligned_data)

        return aligned_data

    except Exception as e:
        print(f"Error processing file: {e}")
        return None


print(convert_xls_to_str("/home/highlander/PycharmProjects/UPGMA_NJ_Tree/static/uploads/ICBGE_data.xlsx"))