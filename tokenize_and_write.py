import os
import json
import requests
from itertools import chain



def ctakes_process(text):
    url = "http://localhost:8080/ctakes-web-rest/service/analyze"
    r = requests.post(url, data=text, params={"format": "full"})
    return r.json()

def token_to_stanza(ctakes_token_pair, sent_text, sent_begin):
    index, ctakes_token = ctakes_token_pair 
    begin = ctakes_token["begin"]
    end = ctakes_token["end"]
    local_index = ctakes_token["tokenNumber"]
    token_text = sent_text[begin:end]
    return {
        "id": index + 1,
        "token_text": token_text,
        "start_char": begin + sent_begin,
        "end_char": end + sent_begin,
    }
    

def process_sentence(sentence):
    begin = sentence["begin"]
    end = sentence["end"]
    sent_text = sentence["text"]
    relevant_view = ctakes_process(sent_text)["_views"]["_InitialView"]
    token_keys = {
        'WordToken',
        'PunctuationToken',
        'SymbolToken',
        # 'NewlineToken',
        'NumToken',
        'ContractionToken',
    }
    
    """
    if "WordToken" not in relevant_view:
        print("NO TOKENS")
        print(sent_text)
        print(relevant_view)
        return []
        #exit()
    """
    tokens = [*chain.from_iterable([relevant_view.get(t_key, []) for t_key in token_keys])]# relevant_view["WordToken"]
    def local_stanza(ctakes_token_pair):
        return token_to_stanza(ctakes_token_pair, sent_text, begin)
    def start(stanza_token):
        return stanza_token["start_char"]
    return [*map(local_stanza, enumerate(sorted(tokens, key=lambda s: s["begin"])))]

def process_text(text):
    relevant_view = ctakes_process(text)["_views"]["_InitialView"]
    ctakes_sentences = relevant_view["Sentence"]
    def basic_dict(sent):
        begin = sent["begin"]
        end = sent["end"]
        return {
            "begin": begin,
            "end": end,
            "text": text[begin:end]
        }
    sorted_sents = sorted(map(basic_dict, ctakes_sentences), key=lambda s: s["begin"])
    return [*map(process_sentence, sorted_sents)]

def tokenize(tokenizer, input_text_dir, out_dir):
    for patient_id, patient_note_path in input_text_dir.items():
        # if "ID032" not in patient_id:
        #     continue
        for one_patient_note in patient_note_path:
            # E.g. [ID045_path_131, ID045_clinic_130, ID045_clinic_132]
            note_id, note_name_, note_name = one_patient_note.split("/")[-3:]
            assert note_name_ == note_name
            assert note_id in note_name
            one_patient_one_note_text = readin_txt(one_patient_note)
            tokenized_sentences = tokenizer(one_patient_one_note_text)
            if not all(tokenized_sentences):
                print(f"{note_id}, {note_name_}, {note_name}")
            # See https://stanfordnlp.github.io/stanza/data_conversion.html#document-to-python-object
            # This dicts, contains a list of sentences, each sentence is a list of tokens,
            # each token is a dictionary {"id": token_index_in_cur_sentence, "text": token_text,
            # "start_char": token_document_level_start_char_position_in_original_document,
            # "end_char": token_document_level_end_char_position_in_original_document}.
            # Please note, "id" is at sentence level, start_char and end_char are at document level.
            #dicts = tokenized_sentences.to_dict()
            filepath = os.path.join(
                out_dir,
                note_name + "_ctakes_tokenized.json",
            )
            with open(
                filepath, "w", encoding="utf-8"
            ) as fw:
                #json.dump(dicts, fw)
                json.dump(tokenized_sentences, fw)


def readin_txt(txt_path):
    """
    Read in plain text of one clinical patient note, return string
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        plain_txt = f.read()
    return plain_txt


def read_thyme2_text(data_path):
    """
    THYME2:
        Train/:
            ID001/:
                ...xml
                ...xml
                ID001_clinic_001/:
                    ...txt
                ID001_clinic_002/:
                    ...txt
                ID001_path_003/:
                    ...txt
        Dev/:
        Test/:
    """
    all_patients_xml, all_patients_clinic_txt = {}, {}

    for patient_id in os.listdir(data_path):
        if patient_id[:2] != "ID":
            continue

        patient_clinic_note_dirs = []
        patient_xml = None
        patient_path = os.path.join(data_path, patient_id)
        for file_path in os.listdir(patient_path):
            if file_path.endswith("xml"):
                if "Thyme2v1-PostProc.ahel0839" in file_path:
                    patient_xml = os.path.join(patient_path, file_path)
            else:
                # Get both clinic and path notes
                if "clinic" not in file_path and "path" not in file_path:
                    # Should be DS_Store
                    assert ".DS_Store" in file_path
                    continue
                if not file_path.endswith("xml"):
                    # Get the patient clinic dirs
                    assert file_path[: len(patient_id)] == patient_id, (
                        file_path[: len(patient_id)],
                        patient_id,
                    )
                    patient_clinic_dir = os.path.join(patient_path, file_path)

                    for clinic_f in os.listdir(patient_clinic_dir):
                        if not clinic_f.endswith("xml"):
                            # The clinic notes has the same name as the clinic notes dir,
                            # e.g. ID001_clinic_001/ID001_clinic_001
                            assert clinic_f == file_path
                            # Get the patient clinic plain txt
                            patient_clinic_note_dirs.append(
                                os.path.join(patient_clinic_dir, clinic_f)
                            )

        # Make sure clinical notes match the xml annotations
        assert patient_xml
        assert patient_id in patient_xml
        all_patients_xml[patient_id] = patient_xml
        all_patients_clinic_txt[patient_id] = patient_clinic_note_dirs

    assert len(all_patients_xml) == len(all_patients_clinic_txt)
    return all_patients_xml, all_patients_clinic_txt


if __name__ == "__main__":
    """
    # tokenizer = stanza.Pipeline('en', package='mimic', processors='tokenize')
    hemonc_sample = "to primary unresected tumors, 1.8 to 2 Gy fractions (total dose: 65 to 70 Gy). Post-operative areas received 60 Gy. Nodal areas not involved by tumor received at least 45 Gy."
    print(hemonc_sample)
    print("ctakes:")
    ls = process_text(
        "to primary unresected tumors, 1.8 to 2 Gy fractions (total dose: 65 to 70 Gy). Post-operative areas received 60 Gy. Nodal areas not involved by tumor received at least 45 Gy."
    )
    for l in ls:
        print(l)
    nlp = stanza.Pipeline('en', processors='tokenize,pos')
    doc = nlp(hemonc_sample) # doc is class Document
    print("stanza:")
    dicts = doc.to_dict()
    for d in dicts:
        print(d)
    """
    # This data path is the gold thyme corpus on R drive, i.e.
    # //rc-fs/chip-nlp/public/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal
    train_thyme2_data_path = '/home/ch231037/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Train/'
    dev_thyme2_data_path = '/home/ch231037/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Dev/'
    test_thyme2_data_path = '/home/ch231037/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Test/'

    # Read in text path
    _, all_patients_clinic_txt_train = read_thyme2_text(train_thyme2_data_path)
    _, all_patients_clinic_txt_dev = read_thyme2_text(dev_thyme2_data_path)
    _, all_patients_clinic_txt_test = read_thyme2_text(test_thyme2_data_path)

    tokenizer = process_text
    # Tokenize and write training text to json
    tokenize(tokenizer, all_patients_clinic_txt_train, "train")
    tokenize(tokenizer, all_patients_clinic_txt_dev, "dev")
    tokenize(tokenizer, all_patients_clinic_txt_test, "test")
    

    print(token_types)
    
