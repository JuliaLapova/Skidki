# -*- coding: utf-8 -*-
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
import re
import ast
from io import StringIO
import uvicorn
import os

app = FastAPI()

# Путь для сохранения файлов
SAVE_DIR = "saved_files/"
os.makedirs(SAVE_DIR, exist_ok=True)  # Создать папку, если её не существует


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


@app.get("/", response_class=HTMLResponse)
async def main():
    content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload CSV File or Enter Text</title>
        <style>
            .container {
                display: flex;
                flex-direction: row;
            }
            .left, .right {
                flex: 1;
                margin: 10px;
            }
            #resultTable {
                display: none;
            }
            #textResult {
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="left">
                <h1>Upload CSV File</h1>
                <form id="csvForm" enctype="multipart/form-data" method="post">
                    <input type="file" name="file" id="csvFile"><br><br>
                    <input type="submit" value="Upload CSV">
                </form>
                <h2>CSV Data Preview</h2>
                <div id="resultTable"></div>
            </div>

            <div class="right">
                <h1>Or Enter Text</h1>
                <form id="textForm" method="post">
                    <textarea name="text" id="textInput" rows="20" cols="100">NAME только очень быстро да а нет объект объект не смотрели аа потому что аа интересовала меня делать лене скидку они ответили что не сделают и все и на этот у нас как говорится вопрос ну меня интересует но я как говорится не ну не знаю я как бы тут уж разговаривала разные варианты у меня не знаю что вы мне можете предложить мне вот так вот конкретно у меня очень выбор ну в смысле очень много разных факторов которые так просто мне неменя зовут маргарита служба контроля качества самолет вырасовались объектом заречной улицы аген с вами связь смотрели или только планируете разговариваю разные варианты я очень много раз</textarea><br><br>
                    <input type="submit" value="Process Text">
                </form>
                <div id="textResult"></div>
            </div>
        </div>
        <script>
            document.getElementById("csvForm").onsubmit = async function(event) {
                event.preventDefault();
                let formData = new FormData();
                formData.append("file", document.getElementById("csvFile").files[0]);
                let response = await fetch("/process-csv", {
                    method: "POST",
                    body: formData
                });
                let data = await response.text();
                document.getElementById("resultTable").innerHTML = data;
                document.getElementById("resultTable").style.display = "block";
            }

            document.getElementById("textForm").onsubmit = async function(event) {
                event.preventDefault();
                let formData = new FormData();
                formData.append("text", document.getElementById("textInput").value);
                let response = await fetch("/process-text", {
                    method: "POST",
                    body: formData
                });
                let data = await response.text();
                document.getElementById("textResult").innerHTML = data;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=content)


@app.post("/process-csv")
async def process_csv(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_csv(StringIO(contents.decode('utf-8')))

    # Проверка наличия колонки 'label' и инициализация меток при её отсутствии
    if 'label' not in df.columns:
        df['label'] = df['processed_text'].apply(lambda x: str(initialize_labels(x)))

    df['label'] = update_labels(df['processed_text'], df['label'], 'скидк', 'B-discount')

    # Подготовка html представления с подсветкой
    df['processed_text'] = df.apply(lambda row: highlight_special_words(row['processed_text'], ast.literal_eval(row['label'])), axis=1)

    # Подготовка обновленного CSV для скачивания
    updated_csv = df.to_csv(index=False)

    # Укажите путь для сохранения файла
    file_name = os.path.join(SAVE_DIR, "processed.csv")
    with open(file_name, 'w', newline='') as temp_file:
        temp_file.write(updated_csv)

    # Сортировка столбцов для правильного отображения
    df_to_display = df[['processed_text', 'label']]

    # Подготовить HTML представление
    table_html = df_to_display.to_html(escape=False, index=False)

    html_content = f"""
        <h1>Updated CSV Results</h1>
        <a href="/download-processed-csv?file={file_name}" download="processed.csv">Download Updated CSV</a>
        <h2>Data Preview</h2>
        {table_html}
        <a href="/">Go Back</a>
    """

    return HTMLResponse(content=html_content)


@app.post("/process-text")
async def process_text(text: str = Form(...)):
    texts = [text]
    labels_col = [str(initialize_labels(text))]

    # Обновить метки
    updated_labels = update_labels(texts, labels_col, 'скидк', 'B-discount')

    # Преобразовать метки отметок в список слов и меток
    labels = ast.literal_eval(updated_labels[0])

    # Выделить слова согласно меткам
    highlighted_text = highlight_special_words(text, labels)

    html_content = f"""
        <h1>Original Text</h1>
        <p>{highlighted_text}</p>
        <h1>Updated Labels</h1>
        <p>{updated_labels[0]}</p>
    """

    return HTMLResponse(content=html_content)


@app.get("/download-processed-csv")
async def download_processed_csv(file: str):
    # Передача содержимого файла клиенту
    return StreamingResponse(
        open(file, 'rb'),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=processed.csv"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)