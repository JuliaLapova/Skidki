import streamlit as st
import pandas as pd
import re
import ast
from io import StringIO
import uuid
import os

# Путь для сохранения файлов
SAVE_DIR = "saved_files/"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def find_word_starting_with(text, prefix):
    pattern = r'\b' + re.escape(prefix) + r'\w*\b'
    matches = re.finditer(pattern, text, re.IGNORECASE)
    for match in matches:
        start_index = len(re.findall(r'\b\w+\b', text[:match.start()]))
        return start_index + 1
    return -1


def initialize_labels(text):
    words = text.split()
    return ['O'] * len(words)


def update_labels(texts, labels_col, prefix, tag):
    updated_labels = []
    for index, text in enumerate(texts):
        try:
            labels = ast.literal_eval(labels_col[index])
        except (ValueError, SyntaxError):
            print(f"Invalid format at index {index}: {labels_col[index]}")
            updated_labels.append(labels_col[index])
            continue
        position = find_word_starting_with(text, prefix)
        if position != -1:
            labels[position - 1] = tag
        updated_labels.append(str(labels))
    return updated_labels


def highlight_special_words(text, labels):
    words = text.split()
    highlighted_text = []

    for word, label in zip(words, labels):
        if label == 'B-discount':
            highlighted_text.append(f"<span style='background-color: yellow;'>{word}</span>")
        elif label in ['B-value', 'I-value']:
            highlighted_text.append(f"<span style='background-color: yellow;'>{word}</span>")
        else:
            highlighted_text.append(word)

    return ' '.join(highlighted_text)


def main():
    st.title("Upload CSV File or Enter Text")

    menu = ["Upload CSV", "Enter Text"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Upload CSV":
        st.subheader("Upload CSV File")

        data_file = st.file_uploader("Upload CSV", type=["csv"])
        if data_file is not None:
            df = pd.read_csv(data_file)

            # Проверка наличия колонки 'label' и инициализация меток при её отсутствии
            if 'label' not in df.columns:
                df['label'] = df['processed_text'].apply(lambda x: str(initialize_labels(x)))

            df['label'] = update_labels(df['processed_text'], df['label'], 'скидк', 'B-discount')

            # Подготовка html представления с подсветкой
            df['processed_text'] = df.apply(
                lambda row: highlight_special_words(row['processed_text'], ast.literal_eval(row['label'])), axis=1)

            st.dataframe(df)

            temp_file_name = os.path.join(SAVE_DIR, f"processed_{uuid.uuid4().hex}.csv")
            df.to_csv(temp_file_name, index=False)
            with open(temp_file_name, 'rb') as f:
                st.download_button(f"Download Updated CSV", f, file_name="processed.csv")

    elif choice == "Enter Text":
        st.subheader("Enter Text")

        text_input = st.text_area("Input Text", "Введите текст здесь...")
        if st.button("Process Text"):
            texts = [text_input]
            labels_col = [str(initialize_labels(text_input))]

            # Обновить метки
            updated_labels = update_labels(texts, labels_col, 'скидк', 'B-discount')

            # Преобразовать метки отметок в список слов и меток
            labels = ast.literal_eval(updated_labels[0])

            # Выделить слова согласно меткам
            highlighted_text = highlight_special_words(text_input, labels)

            st.markdown(f"### Original Text:")
            st.markdown(highlighted_text, unsafe_allow_html=True)
            st.markdown(f"### Updated Labels:")
            st.markdown(f"{updated_labels[0]}")


if __name__ == '__main__':
    main()