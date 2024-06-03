import pandas as pd
import numpy as np
import nltk
import string
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.config['STATIC_FOLDER']='static'

mysql_config = {
    'host':'localhost',
    'user':'root',
    'password':'admin',
    'database':'kabuutaask'
}

connection = mysql.connector.connect(**mysql_config)
dataset_query = "SELECT * FROM dataset"

# Preprocessing
def preprocess_data(text):
    if isinstance(text, str):
        # Mengonversi seluruh teks menjadi huruf kecil
        text = text.lower()
        
        # Tokenisasi kata
        tokens = word_tokenize(text)
        
        processed_data = ' '.join(tokens)

        return processed_data
    else:
        return ''

import string

def preprocess_text(text):
    if isinstance(text, str):
         # Menghapus tanda baca
        text = text.translate(str.maketrans("", "", string.punctuation))
        
        # Mengonversi seluruh teks menjadi huruf kecil
        text = text.lower()

        # Tokenisasi kata
        tokens = word_tokenize(text)

        # Join kembali token-token untuk membentuk teks yang telah diproses
        processed_text = ' '.join(tokens)

        return processed_text
    else:
        return ''

@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/Qas")
def Qas():
    return render_template("question.html")

@app.route("/Answer", methods=['POST'])
def Answer():
    # Membaca dataset
    dataset = pd.read_sql(dataset_query, connection)

    user_question = request.form['question']

    preprocessed_user_question = preprocess_text(user_question)
    print(preprocessed_user_question)
    
    dataset['data'] = dataset['data'].apply(preprocess_data)
    
    #code dari https://github.com/nikitaa30/Content-based-Recommender-System/blob/master/recommender_system.py
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    
    vectors = vectorizer.fit_transform([preprocessed_user_question] + list(dataset['data']))
    print("vectors: ", vectors)

    similarities = cosine_similarity(vectors)
    print("similarities:", similarities)
    
    # Menggunakan np.argsort() untuk mendapatkan indeks yang diurutkan
    sorted_indices = np.argsort(similarities[0])[::-1]
    
    batas_similarity = 0.7
    most_similar_idx = next((idx for idx in sorted_indices if similarities[0, idx] >= batas_similarity), None)
    # Mencari indeks terbaik yang bukan indeks pertanyaan pengguna
    most_similar_idx = next(idx for idx in sorted_indices if idx != 0)
    
    mendekati_similar_idx = sorted_indices[1:8]  # Mengambil 7 indeks
    
    print("most_similar_idx:", most_similar_idx)
    print("mendekati_similar_idx:", mendekati_similar_idx)

    # Memastikan best_answer tidak muncul di dalam mendekati_similar_answers
    if most_similar_idx in mendekati_similar_idx:
        mendekati_similar_idx = mendekati_similar_idx[1:]
    if most_similar_idx is not None:
        best_answer = dataset.iloc[most_similar_idx]['data']
        mendekati_similar_answers = dataset.iloc[mendekati_similar_idx]['data'].tolist()
        return render_template('Answer.html', user_question=user_question, preprocessed_user_question=preprocessed_user_question, best_answer=best_answer, mendekati_similar_answers=mendekati_similar_answers)
    else:
        return f"Maaf, tidak ada jawaban atau jawaban mendekati untuk pertanyaan: {user_question}"
    
@app.route("/Artikel")
def Artikel():
    return render_template("Artikel.html")

@app.route("/AboutUs")
def AboutUs():
    return render_template("AboutUs.html")

@app.route("/view_data")
def view_data():
    try:
        # Mengambil data dari MySQL
        connection = mysql.connector.connect(**mysql_config)
        dataset_query = "SELECT * FROM dataset"
        dataset = pd.read_sql(dataset_query, connection)
        connection.close()
    
        dataset = dataset.fillna('NA')
    
        return render_template("view_data.html", dataset=dataset)
    except Exception as e:
        print("Error:", str(e))
        # Atau berikan pesan kesalahan umum.

    return render_template("view_data.html", dataset=pd.DataFrame())

@app.route("/add_data", methods=['GET', 'POST'])
def add_data():
    try:
        if request.method == 'POST':
            # Mengambil data dari formulir
            new_data = request.form['new_data']

            # Menambahkan data ke MySQL (ID akan otomatis di-generate)
            connection = mysql.connector.connect(**mysql_config)
            cursor = connection.cursor()
            query = "INSERT INTO dataset (data) VALUES (%s)"
            cursor.execute(query, (new_data,))
            connection.commit()
            connection.close()

            return redirect(url_for('view_data'))
    except Exception as e:
        print("Error:", str(e))
        # Atau berikan pesan kesalahan umum.

    return render_template("add_data.html")

@app.route("/edit_data/<int:data_id>", methods=['GET', 'POST'])
def edit_data(data_id):
    # Mengambil data dari MySQL berdasarkan ID
    connection = mysql.connector.connect(**mysql_config)
    query = "SELECT * FROM dataset WHERE id = %s"
    data = pd.read_sql_query(query, connection, params=(data_id,))
    connection.close()

    if request.method == 'POST':
        # Mengambil data yang diedit dari formulir
        edited_data = request.form['edited_data']

        # Memperbarui data di MySQL
        connection = mysql.connector.connect(**mysql_config)
        cursor = connection.cursor()
        query = "UPDATE dataset SET data = %s WHERE id = %s"
        cursor.execute(query, (edited_data, data_id))
        connection.commit()
        connection.close()

        return redirect(url_for('view_data'))

    return render_template("edit_data.html", data=data.iloc[0])

@app.route("/delete_data/<int:data_id>")
def delete_data(data_id):
    try:
        # Koneksi ke database
        connection = mysql.connector.connect(**mysql_config)
        cursor = connection.cursor()

        # Menghapus data berdasarkan ID
        delete_query = "DELETE FROM dataset WHERE id = %s"
        cursor.execute(delete_query, (data_id,))
        connection.commit()

        # Mengambil semua data yang tersisa dan mengurutkan ulang ID
        reset_id_query = "SET @new_id = 0; UPDATE dataset SET id = (@new_id := @new_id + 1); ALTER TABLE dataset AUTO_INCREMENT = 1;"
        cursor.execute(reset_id_query, multi=True)
        connection.commit()

        connection.close()
        return redirect(url_for('view_data'))
    except Exception as e:
        print("Error:", str(e))
        # Atau berikan pesan kesalahan umum.

    return redirect(url_for('view_data'))



if __name__ == '__main__':
    app.run(debug=True)