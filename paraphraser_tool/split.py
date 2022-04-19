import csv, openpyxl, sys

# If missing file name, print error
if len(sys.argv) < 2:
    print("The command is: python run.py <XLSX_FILE>")
    exit()

# Load xlsx file
xlsfile = openpyxl.load_workbook(sys.argv[1], data_only=True)

# Create new file called "domain.yml"
with open("expanded.tsv", "w") as f:

    # Open 'Utterances & Audio_new' sheet - may have to update this name
    checklist = xlsfile['NLU_Checklist'] 
    for row in range(1, checklist.max_row + 1):
        r = list(map(lambda x : x.value if x.value is not None else "", checklist[str(row)]))
        if '-' not in r[4]:
            f.write('\t'.join(r) + '\n')
        else:
            dataSplitted = r[4].split("-")[1:]
            for data in dataSplitted:
                r[4] = data.strip()
                f.write('\t'.join(r) + '\n')