1. Convert Yaml to Excel using:
https://www.convertcsv.com/yaml-to-csv.htm

2. Update nlu_workfile.xlsx


3. Run split.py to generate a new expanded.tsv file:
python split.py nlu_workfile.xlsx
NOTE: Intent goes under column D, Examples goes under column E

4. Update nlu_workfile.xlsx 's nlu_examples_expanded

5. add "- " to nlu_examples_expanded by ="- "&<cell>

6. Run paraphraser.py
