from pypdf import PdfWriter
import argparse, os
from tqdm import tqdm

from constants import DATASETS

def get_parameters() -> argparse.Namespace:
    """Parses and returns a command-line argument for dataset selection."""
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--dataset', type=str, choices=DATASETS, required=True)
    return parser.parse_args()

def main() -> None:
    """
    Merges supplementary PDF files with their corresponding articles in the specified dataset.

    This function:
        - Parses command-line arguments to get the dataset name.
        - Sets up paths to the folder containing PDFs and a new folder for merged PDFs.
        - Iterates through all PDFs in the original dataset folder:
            - Identifies supplementary PDF files (those ending with '_si.pdf' or '_SI.pdf').
            - Attempts to merge each supplementary PDF with its corresponding article PDF (with matching names).
        - The merged PDFs are saved in a new folder with the suffix '_merged' appended to the dataset name.
    """
    args = vars(get_parameters())
    dataset = args['dataset']
    
    path_to_pdfs = f'data/pdfs/pdf_{dataset}/'
    
    # create new path for merged pdfs
    path_to_merged_pdfs = f'data/pdfs/pdf_{dataset}_merged/'
    if not os.path.exists(path_to_merged_pdfs):
        os.makedirs(path_to_merged_pdfs)
    
    for filename in tqdm(os.listdir(path_to_pdfs)):
        # if file is supplementary information, merge it with the article
        if filename.endswith('_si.pdf') or filename.endswith('_SI.pdf'):
            article_filename = filename.replace('_si', '').replace('_SI', '')
            suppl_filename = filename
            try:    
                input1 = open(path_to_pdfs + article_filename, "rb")
                input2 = open(path_to_pdfs + suppl_filename, "rb")
                merger = PdfWriter()
                merger.append(input1)
                merger.append(input2)
                output = open(path_to_merged_pdfs + article_filename, "wb")
                merger.write(output)
                merger.close()
                output.close()
            except:
                print(f'Cannot process {filename}')
        else:
            continue
        
if __name__ == "__main__":
    main()