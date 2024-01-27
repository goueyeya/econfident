import re
import spacy

from transformers import AutoTokenizer, TextClassificationPipeline, TFCamembertForSequenceClassification

model = None
tokenizer = None

nlp = spacy.load("fr_core_news_sm")

'''
categories_b = {
    0:'african_descent hateful', 1:'african_descent non-hateful', 2:'arabs hateful', 3:'arabs non-hateful', 4:'asians hateful', 5:'asians non-hateful', 
    6:'christian hateful', 7:'christian non-hateful', 8:'gay hateful', 9:'gay non-hateful', 10:'hispanics hateful', 11:'hispanics non-hateful', 
    12: 'immigrants hateful', 13:'immigrants non-hateful', 14:'indian/hindu hateful', 15:'indian/hindu non-hateful', 16:'jews hateful', 17:'jews non-hateful',
    18: 'left_wing_people hateful', 19: 'left_wing_people non-hateful', 20:'muslims hateful', 21:'muslims non-hateful', 
    22:'other hateful', 23:'other non-hateful', 
    24:'special_needs hateful', 25:'special_needs non-hateful', 26:'women hateful', 27: 'women non-hateful'
}
'''


categories = {
    0:'afro_descendant hateful', 1:'afro_descendant non-hateful', 2:'arabe hateful', 3:'arabe non-hateful', 4:'asiatique hateful', 5:'asiatique non-hateful',
    6:'chrétien hateful', 7:'chrétien non-hateful', 8:'lgbt hateful', 9:'lgbt non-hateful', 10:'hispanique hateful', 11:'hispanique non-hateful',
    12: 'immigrant hateful', 13:'immigrant non-hateful', 14:'indien/hindu hateful', 15:'indien/hindu non-hateful', 16:'juif hateful', 17:'juif non-hateful',
    18: 'personnes_de_gauche hateful', 19: 'personnes_de_gauche non-hateful', 20:'musulmans hateful', 21:'musulmans non-hateful',
    22:'autres hateful', 23:'autres non-hateful',
    24:'handicapé hateful', 25:'handicapé non-hateful', 26:'femme hateful', 27: 'femme non-hateful'
}

def load_model():
    global model
    global tokenizer
    tokenizer = AutoTokenizer.from_pretrained("./data/bert_tokenizer")
    model = TFCamembertForSequenceClassification.from_pretrained(
        "./data/bert_model",
        id2label=categories
    )
    
def stopwords(s):
    doc = nlp(s)
    filtered = ""
    for token in doc:
        if token.is_stop == False:
            filtered += token.text
            filtered += " "
    return filtered

def predict(text):
    global model
    global tokenizer
    if isinstance(text, str):
        text = [text]
        
    instances = []
    for t in text:
        # Tout d'abord, on s'assure que toutes les données sont bien au format textuel
        t = str(t).lower() \
            .replace("@user", "") \
            .replace("@url", "")
        t = re.sub(r"[\.,\?\!]", "", t)
        t = re.sub(r"\d*", "", t)
        t = re.sub(r"\s+", " ", t)
        t = stopwords(t)
        instances.append(t)
        
    pipe = TextClassificationPipeline(model=model, tokenizer=tokenizer)
    return pipe(instances)
