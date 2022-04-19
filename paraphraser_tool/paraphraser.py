import json
import clipboard
import time
import re
import csv, openpyxl, sys
import torch
from transformers import PegasusForConditionalGeneration, PegasusTokenizer
from parrot import Parrot
from num2words import num2words
from pathlib import Path

#Remove special characters
def remove_char(string):

   #Remove curly and words between
   string = re.sub(r"\s*{.*}\s*", " ", string)

   #Remove brackets
   string=string.replace("[", "").strip()
   string=string.replace("]", "").strip()

   #Remove whitespace before punctuations and extra spacing
   string = re.sub(' +', ' ', string)
   string = re.sub(r'\s([?.!"](?:\s|$))', r'\1', string)

   return string

# Get list of words matching the string
def f(string, match):
    string_list = string.split()
    match_list = []
    for word in string_list:
        if match in word:
            match_list.append(word)
    return match_list

#Obtain new data string for yml
def get_new_string(new_string):

   # Ensures string has punctuation at the back
   if (new_string[-1].isalpha() == True) or (new_string[-1] == '}'):
         new_string = new_string + "."

   #Replace punctuation with blank space
   punct_mark = "#"

   if new_string[-1] == ".":
       new_string = new_string.replace("."," ")
       punct_mark = "."

   if new_string[-1] == "?":
       new_string = new_string.replace("?"," ")
       punct_mark = "?"

   #Makes first char of string lowercase
   new_string = new_string[0].lower() + new_string[1:]

   #Replace backward(s) with random string first
   match_backward = f(new_string,"backward")
   for i in range(0,len(match_backward)):
       new_string=new_string.replace(match_backward[i], "#$%^"+str(i),1)

   #Three entity strings
   entity_back = '{"entity": "back_or_leg","value":"back"}'
   entity_leg = '{"entity": "back_or_leg","value":"leg"}'
   entity_backleg = '{"entity": "back_or_leg","value":"back_and_leg"}'

   #Check for back or leg or 'back and leg' in new string
   word1 = 'back'
   word2 = 'leg'
   if word1 in new_string: 
      backcount = 1
   else:
       backcount = 0
       
   if word2 in new_string: 
      legcount = 1
   else:
       legcount = 0

   #Returning Brackets and adding back intent
   #back and leg
   if (backcount == 1) & (legcount == 1):
      back_num = new_string.find('back')
      leg_num = new_string.find('leg')

      
      #back first
      if back_num < leg_num:
        match = f(new_string,"back")  
        new_string=new_string.replace(match[0], "["+match[0],1)

        match = f(new_string,"leg")
        new_string=new_string.replace(match[len(match)-1], match[len(match)-1]+"]",1)
            
      #leg first
      else:
        match = f(new_string,"back")
        new_string=new_string.replace(match[len(match)-1], match[len(match)-1]+"]",1)

        match = f(new_string,"leg")
        new_string=new_string.replace(match[0], "["+match[0],1)

      new_string=new_string.replace("]", "]" + entity_backleg)
        
   elif backcount == 1:
      match = f(new_string,"back")
      for i in match:
        if i == "back":
            new_string = new_string.replace("back"+" ","["+"back"+"] ")
        else:
            new_string = new_string.replace(i,"["+i+"]")
             
      new_string=new_string.replace("]", "]" + entity_back)
   else:
      match = f(new_string,"leg")
      for i in match:
        if i == "leg":
            new_string = new_string.replace("leg"+" ","["+"leg"+"] ")
        else:
            new_string = new_string.replace(i,"["+i+"]")

      new_string=new_string.replace("]", "]" + entity_leg)

   new_string = new_string.strip()

   #Replaces back . or ? if needed
   if (new_string[-1].isalpha() == True) or (new_string[-1] == '}'):
      if punct_mark == "#":
         new_string = new_string + "."
      else:
         new_string = new_string + punct_mark
         
   #Replace random string with original words
   for i in range(0,len(match_backward)):
       new_string=new_string.replace("#$%^"+str(i),match_backward[i],1)
   
   return new_string

#Load Pegasus Model
model_name = 'tuner007/pegasus_paraphrase'
torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'
tokenizer = PegasusTokenizer.from_pretrained(model_name)
model = PegasusForConditionalGeneration.from_pretrained(model_name).to(torch_device)
#Load Parrot Model
parrot = Parrot(model_tag="prithivida/parrot_paraphraser_on_T5", use_gpu=False)
#Get string response function

def get_response(input_text,num_return_sequences,num_beams):
  batch = tokenizer([input_text],truncation=True,padding='longest',max_length=60, return_tensors="pt").to(torch_device)
  translated = model.generate(**batch,max_length=60,num_beams=num_beams, num_return_sequences=num_return_sequences, temperature=1.5)
  tgt_text = tokenizer.batch_decode(translated, skip_special_tokens=True)
  
  #Remove phrases with 3 or less words.
  text_store = []
  for text in tgt_text:
      if len(text.split()) > 3:
          text_store.append(text)
  print(text_store)
  #Remove duplicates
  text_store = list(dict.fromkeys(text_store))
  return text_store


#String response function for parrot t5
def get_parrot(phrase):
    
    # Replace numbers in the phrase with words
    phrase = re.sub(r"(\d+)", lambda x: num2words(int(x.group(0))), phrase)

    para_phrases = parrot.augment(input_phrase=phrase)
    print(para_phrases)
    # If the paraphraser can't produce even 1 sentence
    if para_phrases is None or len(phrase) > 70:
        tgt_text = []
        tgt_text.append(phrase)
        tgt_text = list(dict.fromkeys(tgt_text))
        return tgt_text

    #Reverse list so that most confident phrase is first
    if len(para_phrases) > 1:
        para_phrases = list(reversed(para_phrases))
            
    tgt_text = []


    if len(para_phrases) > 2:
        for num in range(0,2):
            parrot_string = str(para_phrases[num])
            #Removes unnecessary parts
            while parrot_string[0].isalpha() != True:
                parrot_string = parrot_string[1:]

            while (parrot_string[-1] == "?" or parrot_string[-1] == "." or (parrot_string[-1].isalpha() == True)) is False:
                parrot_string = parrot_string[:-1]
            #Append only if rephrase is more than 3 words
            if len(parrot_string.split()) > 3:
                tgt_text.append(parrot_string)
    else:
        for para_phrase in para_phrases:
            parrot_string = str(para_phrase)
            while parrot_string[0].isalpha() != True:
                parrot_string = parrot_string[1:]

            while (parrot_string[-1] == "?" or parrot_string[-1] == "." or (parrot_string[-1].isalpha() == True)) is False:
                parrot_string = parrot_string[:-1]

            if len(parrot_string.split()) > 3:
                tgt_text.append(parrot_string)

    tgt_text.append(phrase)
    tgt_text = list(dict.fromkeys(tgt_text))
    return tgt_text

#Number of beams and return sequences
num_beams = 3
num_return_sequences = 3

# Load xlsx file
xlsfile = openpyxl.load_workbook('nlu_workfile.xlsx', data_only=True)


#Create NLU intent store
nlu_intent = []

# Create new file called "nlu.yml"
with open("nlu.yml", "w", encoding='utf8') as nlu_file:
    nlu_file.write("nlu:\n")
    checklist = xlsfile['NLU_Checklist_Expanded'] # Sheet name
    hashmap = {}
    # Scans through the sheet to group same intents together
    for row in range(1, checklist.max_row + 1):
        print(row)
        eData = checklist['E' + str(row)].value
        dData = checklist['D' + str(row)].value
        if eData is not None and '-' in eData:
            if dData is not None and '-' in dData:
                orig = dData.replace("-", "").strip()
                data = eData.replace("-", "").strip()
                
                ## PARAPHRASER CODE HERE

                #Capitalize first letter and get string to be rephrased
                data = data.capitalize()
                #Add fullstop if last letter is alphabet or curly brace
                if (data[-1].isalpha() == True) or (data[-1] == '}'):
                   data = data + '.'
                input_string = str(data)
                
                #only rephrase words without backslash and more than 1 word
                if ("/" not in input_string) & (len(input_string.split()) > 1):
          
                    #remove special characters
                    #print(input_string)
                    input_string = remove_char(input_string)              
                  
                    #get new inputs
                    context = input_string
                    if len(context.split()) < 3:
                        num_return_sequences = 2
                        num_beams = 2
                    #Replace commas with fullstop before reprasing
                    context = context.replace(",",".")
                    if context[-1] == "?":
                        context = context[:-1]
                        context = context + "."

                    #Rephrase the original intent
                    #tgt_text = get_response(context,num_return_sequences,num_beams)
                    tgt_text = get_parrot(context)

                    # Rewrites the rephrased strings to include brackets + entities
                    for i in range(0,len(tgt_text)):
                        tgt_text[i]=get_new_string(tgt_text[i])
                    #Capitalize rephrased sentence and add fullstop if needed
                        tgt_text[i]=tgt_text[i].capitalize()
                        tgt_text[i] = tgt_text[i].replace(" i "," I ")

                    #Remove duplicates
                    tgt_text = tgt_text + [str(data)]
                    tgt_text = list(dict.fromkeys(tgt_text))

                    #Check list for duplicates             
                    for i in tgt_text[:]:
                        if i in nlu_intent:
                            tgt_text.remove(i)

                    for i in range(0,len(tgt_text)):                    
                        print(tgt_text[i])

                    #Write into NLU file and nlu_intent store
                    if orig in hashmap:
                        
                        for k in range(0,len(tgt_text)):
                            hashmap[orig].append(tgt_text[k])
                            nlu_intent.append(tgt_text[k])
                            #print(tgt_text[k])
                    else:
                     
                        hashmap[orig] = [tgt_text[0]]
                        nlu_intent.append(tgt_text[0])
                        for k in range(1,len(tgt_text)):
                            hashmap[orig].append(tgt_text[k])
                            nlu_intent.append(tgt_text[k])
                            #print(tgt_text[k])    

                ## END OF PARAPHRASER CODE

                else:
                    
                    if orig in hashmap:
                        hashmap[orig].append(data)
                    else:
                        hashmap[orig] = [data]

                    
    # Prints out the data
    for key in hashmap:
        nlu_file.write("    - intent: " + key + "\n")
        nlu_file.write("      examples: |\n")
        for value in hashmap[key]:
            nlu_file.write("        - " + value + "\n")


## Replace extra spacings
file = Path("nlu.yml")
file.write_text(file.read_text().replace('}"   "', '}" "'))
file.write_text(file.read_text().replace('"  "', '" "'))