import os
import json
import requests
from itertools import chain

token_keys = {
    "WordToken",
    "PunctuationToken",
    "SymbolToken",
    # Ignoring these
    # 'NewlineToken',
    "NumToken",
    "ContractionToken",
}

annotation_keys = {
    "DateAnnotation",
    "FractionAnnotation",
    "MeasurementAnnotation",
    "PersonTitleAnnotation",
    "TimeAnnotation",
    "RangeAnnotation",
    "RomanNumeralAnnotation",
}


def ctakes_process(text):
    url = "http://localhost:8080/ctakes-web-rest/service/analyze"
    r = requests.post(url, data=text, params={"format": "full"})
    return r.json()


def token_to_stanza(ctakes_token_pair, sent_text, sent_begin):
    index, ctakes_token = ctakes_token_pair
    begin = ctakes_token["begin"]
    end = ctakes_token["end"]
    token_text = sent_text[begin:end]
    return {
        "id": index + 1,
        "token_text": token_text,
        "start_char": begin + sent_begin,
        "end_char": end + sent_begin,
    }


def process_sentence(sentence):
    
    begin = sentence["begin"]
    sent_text = sentence["text"]
    print(sent_text)
    relevant_view = ctakes_process(sent_text)["_views"]["_InitialView"]
    #print(relevant_view)
    raw_tokens =  sorted(
        chain.from_iterable([relevant_view.get(t_key, []) for t_key in token_keys]),
        key=lambda s: (s["begin"], s["end"]),
    )
    if len(raw_tokens) == 0:
        print("Something wrong")
        print(sent_text)
        print(relevant_view)

        
    raw_annotations = sorted(
        chain.from_iterable(
            [relevant_view.get(a_key, []) for a_key in annotation_keys]
        ),
        key=lambda s: (s["begin"], s["end"]),
    )

    prime_annotations = []

    def to_str_ls(ls):
        return "\n".join([f"{(l['begin'], l['end'])}: {sent_text[l['begin']:l['end']]}" for l in ls])
    
    # print("BUILDING")
    # print(f"ORIGINAL RAW: {to_str_ls(raw_annotations)}")
    for i in range(0, len(raw_annotations)):
        
        prev = {"begin": -1, "end": -1} if i == 0 else prime_annotations[-1]
        curr = raw_annotations[i]
        # print(f"{i} {(prev['begin'], prev['end'])} {(curr['begin'], curr['end'])}")
        # if (prev["begin"] <= curr["begin"]) and (curr["end"] <= prev["end"]):
        if (prev["begin"] >= curr["begin"]) and (curr["end"] >= prev["end"]):
            # remove prev
            # print("main case")
            prime_annotations = [*prime_annotations[:-1], curr]
            # print(f"{to_str_ls(prime_annotations)}")
        elif prev["end"] < curr["begin"]:
            # print("second case")
            prime_annotations = [*prime_annotations, curr]
            # print(f"{to_str_ls(prime_annotations)}")

    annotations_and_tokens = sorted(
        [*prime_annotations, *raw_tokens], key=lambda s: (s["begin"], s["end"])
    )

    final_spans = []

    for i in range(0, len(annotations_and_tokens)):
        prev = {"begin": -1, "end": -1} if i == 0 else final_spans[-1]
        curr = annotations_and_tokens[i]
        if (prev["begin"] >= curr["begin"]) and (curr["end"] >= prev["end"]):
            # remove prev
            final_spans = [*final_spans[:-1], curr]
        elif prev["end"] < curr["begin"]:
            final_spans = [*final_spans, curr]


    
            
    if len(raw_annotations) > 1:
        print(f"raw_tokens {to_str_ls(raw_tokens)}")
        print("\n\n")
        print(f"raw_annotations {to_str_ls(raw_annotations)}")
        print("\n\n")
        print(f"prime_annotations {to_str_ls(prime_annotations)}")
        print("\n\n")
        print(f"final_spans {to_str_ls(final_spans)}")
        print("\n\n")
        
            
    def local_stanza(ctakes_token_pair):
        return token_to_stanza(ctakes_token_pair, sent_text, begin)

    return [
        *map(local_stanza, enumerate(sorted(final_spans, key=lambda s: s["begin"])))
    ]


def process_text(text):
    relevant_view = ctakes_process(text)["_views"]["_InitialView"]
    ctakes_sentences = relevant_view["Sentence"]

    def basic_dict(sent):
        begin = sent["begin"]
        end = sent["end"]
        return {"begin": begin, "end": end, "text": text[begin:end]}

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
            print(f"{note_id}, {note_name_}, {note_name}")
            tokenized_sentences = tokenizer(one_patient_one_note_text)
            if not all(tokenized_sentences):
                print(f"{note_id}, {note_name_}, {note_name}")
            # See https://stanfordnlp.github.io/stanza/data_conversion.html#document-to-python-object
            # This dicts, contains a list of sentences, each sentence is a list of tokens,
            # each token is a dictionary {"id": token_index_in_cur_sentence, "text": token_text,
            # "start_char": token_document_level_start_char_position_in_original_document,
            # "end_char": token_document_level_end_char_position_in_original_document}.
            # Please note, "id" is at sentence level, start_char and end_char are at document level.
            # dicts = tokenized_sentences.to_dict()
            filepath = os.path.join(
                out_dir,
                note_name + "_ctakes_tokenized.json",
            )
            with open(filepath, "w", encoding="utf-8") as fw:
                # json.dump(dicts, fw)
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
    # This data path is the gold thyme corpus on R drive, i.e.
    # //rc-fs/chip-nlp/public/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal
    train_thyme2_data_path = (
        "/home/ch231037/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Train/"
    )
    dev_thyme2_data_path = (
        "/home/ch231037/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Dev/"
    )
    test_thyme2_data_path = (
        "/home/ch231037/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Test/"
    )

    # Read in text path
    _, all_patients_clinic_txt_train = read_thyme2_text(train_thyme2_data_path)
    _, all_patients_clinic_txt_dev = read_thyme2_text(dev_thyme2_data_path)
    _, all_patients_clinic_txt_test = read_thyme2_text(test_thyme2_data_path)

    tokenizer = process_text
    # Tokenize and write training text to json
    tokenize(tokenizer, all_patients_clinic_txt_train, "train")
    tokenize(tokenizer, all_patients_clinic_txt_dev, "dev")
    tokenize(tokenizer, all_patients_clinic_txt_test, "test")
