from flask import Flask, render_template, request
import sqlite3
from pymystem3 import Mystem
from gensim.models import Word2Vec

app = Flask(__name__)

mystem = Mystem()

model_word2vec = Word2Vec.load("/Users/shoner/Desktop/ХАКАТОН/pythonProject1/film_word2vec.model")

def get_film_details(film_id, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        query = """
        SELECT
            f.filmId,
            f.nameRu,
            f.description,
            f.year,
            f.rating,
            f.age_limit,
            f.poster
        FROM films f
        WHERE f.filmId = ?
        """
        cursor.execute(query, (film_id,))
        film_details = cursor.fetchone()

        conn.close()

        if film_details:
            film = {
                "id": film_details[0],
                "name": film_details[1],
                "description": film_details[2],
                "year": film_details[3],
                "rating": film_details[4],
                "age_limit": film_details[5],
                "poster": film_details[6]
            }
            return film
        else:
            print(f"Фильм с ID {film_id} не найден.")
            return None

    except sqlite3.OperationalError as e:
        print(f"Ошибка при работе с базой данных: {e}")
        conn.close()
        return None


def find_similar_films(model_word2vec, query, films_data, topn=5):
    query = preprocess_text(query, mystem)
    query_tokens = query.split()

    similar_words = []
    for token in query_tokens:
        try:
            similar_words.extend([word for word, _ in model_word2vec.wv.most_similar(token, topn=topn)])
        except KeyError:
            continue

    similar_words.extend(query_tokens)

    results = []
    for film in films_data:
        film_id = film[0]
        name_ru = film[1]
        poster = film[2]
        description = film[3]
        year = film[4]
        rating = film[5]

        name_ru_obrabotka = preprocess_text(name_ru, mystem)
        name_ru_tokens = name_ru_obrabotka.split()
        description_tokens = description.split()

        if any(word in description_tokens + name_ru_tokens for word in similar_words):
            results.append(film)

    return results
def fetch_films_from_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        query = """
        SELECT
            filmId,
            nameRu AS NameRu,
            poster AS Poster,
            description AS Description,
            CAST(year AS INTEGER) AS Year,
            CAST(rating AS REAL) AS Rating
        FROM films
        """
        cursor.execute(query)
        films_data = cursor.fetchall()
        conn.close()
        return films_data  # Включает description для поиска

    except sqlite3.OperationalError as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return []


def preprocess_text(text, mystem):
    lemmatized_text = ' '.join(mystem.lemmatize(text.lower()))
    return lemmatized_text.strip()



def get_top_3_films(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        query = """
        SELECT
            f.filmId,
            f.nameRu,
            f.description,
            f.year,
            f.rating,
            f.age_limit,
            f.poster
        FROM films f
        ORDER BY f.rating DESC
        LIMIT 3
        """
        cursor.execute(query)
        top_films = cursor.fetchall()
        conn.close()
        return top_films

    except sqlite3.OperationalError as e:
        print(f"Ошибка при работе с базой данных: {e}")
        conn.close()
        return []


def get_random_films(db_path, limit=6):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        query = """
        SELECT
            filmId,
            nameRu AS NameRu,
            poster AS Poster,
            description AS Description
        FROM films
        ORDER BY RANDOM()
        LIMIT ?
        """
        cursor.execute(query, (limit,))
        films_data = cursor.fetchall()
        conn.close()

        films = [
            {
                "id": film[0],
                "name": film[1],
                "poster": film[2],
                "description": film[3]
            }
            for film in films_data
        ]
        return films

    except sqlite3.OperationalError as e:
        print(f"Ошибка при работе с базой данных: {e}")
        conn.close()
        return []



@app.route('/')
def index():
    conn = sqlite3.connect('/Users/shoner/Desktop/films.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT filmId, nameRu, description, year, rating, age_limit, poster FROM films ORDER BY RANDOM() LIMIT 6")
    random_films = get_random_films('/Users/shoner/Desktop/films.db')

    top_films = get_top_3_films('/Users/shoner/Desktop/films.db')

    return render_template('index.html', random_films=random_films, top_films=top_films)


@app.route('/search.html', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    year_from = request.args.get('year_from')
    year_to = request.args.get('year_to')
    rating = request.args.get('rating')

    films_data = fetch_films_from_db('/Users/shoner/Desktop/films.db')

    try:
        if year_from and year_from.isdigit():
            year_from = int(year_from)
            films_data = [film for film in films_data if film[4] >= year_from]

        if year_to and year_to.isdigit():
            year_to = int(year_to)
            films_data = [film for film in films_data if film[4] <= year_to]

        if rating and rating.replace('.', '', 1).isdigit():
            rating = float(rating)
            films_data = [film for film in films_data if film[5] >= rating]

        # Поиск похожих фильмов
        if query:
            films_data = find_similar_films(model_word2vec, query, films_data)

        films_data = [(film[0], film[1], film[2], film[4], film[5]) for film in films_data]

    except ValueError as e:
        print(f"Ошибка при обработке фильтров: {e}")
        films_data = []

    return render_template('search_results.html', films=films_data, query=query)

@app.route('/movie_info/<int:film_id>')
def movie_info(film_id):
    film = get_film_details(film_id, '/Users/shoner/Desktop/films.db')

    if film:
        return render_template('movie_info.html', film=film)
    else:
        return "Фильм не найден", 404

if __name__ == "__main__":
    app.run(debug=True, port = 4000)

