from pdf2image import convert_from_path
import os, argparse, sys
import pandas as pd
from tqdm import tqdm
from datasets import load_dataset

from constants import DATASETS, DATASETS_IDS, MAGNETIC_ARTICLES, SELTOX_ARTICLES

def get_parameters() -> argparse.Namespace:
    """Parses and returns command-line arguments for dataset selection and Poppler path."""
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--dataset', type=str, choices=DATASETS, required=True)
    parser.add_argument('--poppler_path', type=str, required=True)
    return parser.parse_args()

def main() -> None:
    """
    Converts open-access PDF articles from a specified dataset into images, saving each page as a JPEG.

    This function:
        - Parses command-line arguments to get the dataset name and Poppler path for PDF processing.
        - Loads the dataset metadata and determines which PDF files are open access.
        - Validates the presence of required PDF files in the expected directories.
        - For datasets with supplementary material, prioritizes merged PDFs when available.
        - Creates dedicated folders for each PDF.
        - Converts each page of each PDF into a JPEG image and saves the images into the corresponding folder.
    """
    args = vars(get_parameters())
    dataset = args['dataset']
    dataset_id = DATASETS_IDS[dataset]
    dataset_hf = load_dataset(dataset_id)
    df_dataset = dataset_hf["train"].to_pandas()
    
    folder_name = 'pdf_' + dataset
    merged_folder_name = 'pdf_' + dataset + '_merged'
    folder_path = os.path.normpath(f'data/pdfs/{folder_name}')
    merged_folder_path = os.path.normpath(f'data/pdfs/{merged_folder_name}')
    poppler_path = args['poppler_path']
    
    # open access pdfs filenames
    df_dataset['pdf'] = df_dataset['pdf'].apply(lambda x: x + '.pdf' if x.endswith('.pdf') == False else x)
    all_oa_pdfs = df_dataset[df_dataset.access == 1].pdf.tolist()
    if dataset == 'magnetic':
        access_files = MAGNETIC_ARTICLES
    elif dataset == 'seltox':
        access_files = SELTOX_ARTICLES
    else:
        access_files = set(all_oa_pdfs)
    
    print(f'The dataset has {len(set(all_oa_pdfs))} open access articles. Working with {len(access_files)} of them.')
    
    # check presence of open access pdfs
    lower_access_files = set([i.lower() for i in access_files])
    intersec = lower_access_files.intersection([i.lower() for i in os.listdir(folder_path)])
    if len(lower_access_files) == len(intersec):
        print('All pdfs in the folder!')
    else:
        sys.exit(f'Check pdfs! {len(lower_access_files) - len(intersec)} pdfs are missing: {list(lower_access_files - intersec)}')
    
    # find all open access pdf paths 
    if dataset in ['cocrystals', 'magnetic', 'nanozymes']: # have supplementary materials
        pdf_paths = []
        for filename in access_files:
            if filename in os.listdir(merged_folder_path):
                pdf_paths.append(os.path.join(merged_folder_path, filename))
            else:
                pdf_paths.append(os.path.join(folder_path, filename))
    else: # no supplementary materials
        pdf_paths = [
        os.path.join(folder_path, filename)
        for filename in access_files
        ]

    # create images folder
    images_path = 'data/images'
    if not os.path.exists(images_path):
        os.makedirs(images_path)

    # create folders for each pdf
    folder_paths = [os.path.join(os.path.normpath(f'data/images/{dataset}'), i.split('\\')[-1].replace('.pdf', '')) for i in pdf_paths]
    
    for path in folder_paths:
        if not os.path.exists(path):
            os.makedirs(path)
    
    # convert each pdf page into image and put all images into corresponding pdf folder
    print('Converting pdfs into images...')
    for i, pdf in enumerate(tqdm(pdf_paths)):
        if not os.listdir(folder_paths[i]):
            pages = convert_from_path(pdf,
                                poppler_path = poppler_path,
                                dpi=500)
            for count, page in enumerate(pages):
                save_path = f'{folder_paths[i]}/out_{count}.jpg'
                page.save(save_path, 'JPEG')
            
if __name__ == "__main__":
    main()
    