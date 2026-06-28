# CHEMX_FINDINGS.md: что берем в работу

Источник: `C:\Users\Максим\Downloads\Telegram Desktop\CHEMX_FINDINGS.md`.

## Главное

Файл тиммейта полезный и хорошо стыкуется с нашим направлением в части метрики:

- scoring — это column-wise multiset exact string match;
- row order/row linking внутри статьи менее важны, чем полный набор правильных значений в каждой колонке;
- нормализация под формат GT критична;
- лишние галлюцинированные значения дают FP, поэтому blank/`NOT_DETECTED` стратегия важна;
- перед сильными архитектурными решениями нужно посмотреть реальный GT формат: числа, пустоты, регистр, SMILES.

## Важная поправка по Co-crystals

В файле есть тезис, что Co-crystals содержит 37 колонок и может биться через метаполя. По нашему локальному baseline-коду для scoring используются только 7 extracted columns:

```text
name_cocrystal
ratio_cocrystal
name_drug
SMILES_drug
name_coformer
SMILES_coformer
photostability_change
```

Это видно в `baseline/src/constants.py` через `EXTRACTED_COLUMNS["cocrystals"]`.

Значит “дешевые метаполя” не дают прямого прироста в официальной baseline-метрике для Co-crystals, если организаторы используют тот же extracted-column scoring. Co-crystals все равно интересен как second domain, но не выглядит настолько бесплатной победой, как следует из файла.

## Что меняем в текущем плане

SelTox оставляем основным MVP, потому что:

- baseline `0.045`, то есть низкая планка;
- scoring columns действительно совпадают с тем, что мы уже строим: activity, NP characterization, synthesis;
- наш текущий skeleton уже заточен под blank-first extraction и exact-string normalization;
- вывод тиммейта про SelTox прямо подтверждает главный рычаг: не галлюцинировать пустые поля и нормализовать числа/биологическую номенклатуру.

Но архитектуру стоит держать domain-agnostic:

- schema передается как параметр;
- LLM prompt строится из схемы;
- normalizer должен иметь domain-specific правила;
- после первого SelTox smoke можно добавить Co-crystals как второй домен с OCSR/RDKit, если будет время.

## Immediate actions

1. Получить `YANDEX_FOLDER_ID` и проверить `python -m src.cli llm-smoke`.
2. Подключить LLM к SelTox activity extraction.
3. Получить/положить локальный GT cache и посмотреть реальный формат пустот/чисел.
4. Прогнать evaluator на GT-vs-GT sanity, потом на baseline predictions.
5. После SelTox smoke оценить, стоит ли добавлять Co-crystals как второй домен.
