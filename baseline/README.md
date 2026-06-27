# Extraction with LLMs

> **Origin / провенанс.** Этот каталог — single-agent бейзлайн из репозитория
> [ai-chem/ChemX](https://github.com/ai-chem/ChemX) (папка `LLM/`), перенесённый сюда
> как стартовая точка решения DataCon'26. Папка `result/` (выходы прогонов) не переносилась.
> В `reference_metrics/` лежат опубликованные метрики single-agent — **эталон, который
> наше решение должно превзойти** (источник: репозиторий задачи DataCon'26, папка `metrics/`).

The code for chemical information extraction from PDF and images of PDF pages using GPT-4o as a baseline model.

## 🔧 Installation

```pip install -r requirements.txt```

Poppler has to be installed and added to PATH, follow the instructions [here](https://pdf2image.readthedocs.io/en/latest/installation.html#installing-poppler).

## 🚀 Usage

1. Put open access article PDFs into ```data/pdfs/pdf_<dataset>``` folders.

2. Merge article and supporting infromation files. Dataset keys: ```oxazolidinone, benzimidazole, cocrystals, complexes, nanozymes, magnetic, cytotoxicity, seltox, synergy```.

```python src/merge_suppl.py  --dataset <dataset>```

3. Convert PDF into JPEG images

```python src/pdf_to_images.py  --dataset <dataset>  --poppler_path <poppler_path>```

4. Extraction from PDF

```python src/pdf_extraction.py  --dataset <dataset>  --openai_api_key <YOUR_API_KEY>```

Results will appear in the ```result/from_pdf``` folder.

5. Extraction from images

```python src/images_extraction.py --dataset <dataset>  --openai_api_key <YOUR_API_KEY>```

Results will appear in the ```result/from_image``` folder.

6. Calculate metrics

```python src/metric_calc.py  --dataset <dataset>  --source <pdf_or_image>```

Metrics will appear in the ```result/metrics``` folder.