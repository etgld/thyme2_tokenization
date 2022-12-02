import os
import json
import stanza


def tokenize(tokenizer, input_text_dir):
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
            # See https://stanfordnlp.github.io/stanza/data_conversion.html#document-to-python-object
            # This dicts, contains a list of sentences, each sentence is a list of tokens,
            # each token is a dictionary {"id": token_index_in_cur_sentence, "text": token_text,
            # "start_char": token_document_level_start_char_position_in_original_document,
            # "end_char": token_document_level_end_char_position_in_original_document}.
            # Please note, "id" is at sentence level, start_char and end_char are at document level.
            dicts = tokenized_sentences.to_dict()
            with open(note_name + "_stanza_tokenized.json", "w", encoding="utf-8") as fw:
                json.dump(dicts, fw)


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
        if patient_id[:2] != 'ID':
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
                    assert file_path[:len(patient_id)] == patient_id, \
                        (file_path[:len(patient_id)], patient_id)
                    patient_clinic_dir = os.path.join(patient_path, file_path)

                    for clinic_f in os.listdir(patient_clinic_dir):
                        if not clinic_f.endswith("xml"):
                            # The clinic notes has the same name as the clinic notes dir,
                            # e.g. ID001_clinic_001/ID001_clinic_001
                            assert clinic_f == file_path
                            # Get the patient clinic plain txt
                            patient_clinic_note_dirs.append(os.path.join(patient_clinic_dir, clinic_f))

        # Make sure clinical notes match the xml annotations
        assert patient_xml
        assert patient_id in patient_xml
        all_patients_xml[patient_id] = patient_xml
        all_patients_clinic_txt[patient_id] = patient_clinic_note_dirs

    assert len(all_patients_xml) == len(all_patients_clinic_txt)
    return all_patients_xml, all_patients_clinic_txt


if __name__ == '__main__':
    tokenizer = stanza.Pipeline('en', package='mimic', processors='tokenize')

    # This data path is the gold thyme corpus on R drive, i.e.
    # //rc-fs/chip-nlp/public/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal
    train_thyme2_data_path = '/home/jiarui/mnt/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Train/'
    dev_thyme2_data_path = '/home/jiarui/mnt/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Dev/'
    test_thyme2_data_path = '/home/jiarui/mnt/r/THYME2/2022_THYME2Colon/Cross-THYMEColonFinal/Test/'

    # Read in text path
    _, all_patients_clinic_txt_train = read_thyme2_text(train_thyme2_data_path)
    # _, all_patients_clinic_txt_dev = read_thyme2_text(dev_thyme2_data_path)
    # _, all_patients_clinic_txt_test = read_thyme2_text(test_thyme2_data_path)

    # Tokenize and write training text to json
    tokenize(tokenizer, all_patients_clinic_txt_train)
    # tokenize(tokenizer, all_patients_clinic_txt_dev)
    # tokenize(tokenizer, all_patients_clinic_txt_dev)




