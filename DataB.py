import requests
import json
import sqlite3
import time

BASE_URL = "https://kinopoiskapiunofficial.tech/api/v2.2/films"

API_KEYS = [
    "c76460c4-85fa-4e4a-9376-9153371f284a",
    "7e4891a1-7f84-44ae-80e8-a8911f9d95a9",
    "5ebdfe13-bfec-4f75-b828-52dd304ffa62",
    "414b2717-b11b-48c4-89db-fe21ec6ec492",
    "a8b21308-ad71-492d-b036-3c7f1f02e22d",
    '8a8d111a-0028-4f06-a773-e0eedf86090b'
]

current_api_key_index = 0

conn = sqlite3.connect('films.db', timeout=10)
c = conn.cursor()

def get_current_api_key():
    global current_api_key_index
    return API_KEYS[current_api_key_index]

def switch_api_key():
    global current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(API_KEYS)
    print(f"Переключен на API-ключ: {current_api_key_index + 1}")

def create_table():
    c.execute('''CREATE TABLE IF NOT EXISTS films (
                 filmId INTEGER PRIMARY KEY,
                 nameRu TEXT,
                 description TEXT,
                 year INTEGER,
                 rating REAL,
                 age_limit INTEGER,
                 poster TEXT)''')
    conn.commit()

def save_to_db(film):
    global c, conn
    retries = 3
    while retries > 0:
        try:
            c.execute('''INSERT OR IGNORE INTO films (filmId, nameRu, description, year, rating, age_limit, poster)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (film['filmId'], film['nameRu'], film['description'], film['year'], film['rating'], film['age_limit'], film['poster']))
            conn.commit()
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print("База данных заблокирована. Повторная попытка...")
                retries -= 1
                time.sleep(1)
            else:
                raise e
    else:
        print(f"Не удалось сохранить данные о фильме {film['filmId']} после нескольких попыток.")

def fetch_film_details(film_id):
    headers = {"X-API-KEY": get_current_api_key()}
    response = requests.get(f"{BASE_URL}/{film_id}", headers=headers)

    if response.status_code == 200:
        print(f"Успешно: {film_id}")
        return response.json()
    elif response.status_code == 402:
        print(f"Лимит запросов исчерпан для ключа {current_api_key_index + 1}. Переключение ключа...")
        switch_api_key()
        return fetch_film_details(film_id)  # Повторный запрос с новым ключом
    elif response.status_code == 404:
        print(f"Фильм с ID {film_id} не найден.")
        return None
    else:
        print(f"Ошибка при получении данных о фильме {film_id}: {response.status_code}")
        return None


def fetch_films_by_ids(film_ids):
    films = []
    for film_id in film_ids:
        try:
            details = fetch_film_details(film_id)
            if details:
                description = details.get('description', 'Описание отсутствует')
                name_ru = details.get('nameRu', 'Название отсутствует')
                year = details.get('year', 'Год отсутствует')
                rating = details.get('ratingKinopoisk', 0)
                age_limit = details.get('ratingAgeLimits', 0)
                poster = details.get('posterUrl', 'Постер отсутствует')

                film_data = {
                    'filmId': film_id,
                    'nameRu': name_ru,
                    'description': description,
                    'year': year,
                    'rating': rating,
                    'age_limit': age_limit,
                    'poster': poster
                }
                films.append(film_data)
                save_to_db(film_data)
                time.sleep(0.1)
        except Exception as e:
            print(f"Ошибка при обработке фильма {film_id}: {e}")
            continue
    return films

if __name__ == "__main__":
    try:
        create_table()
        film_ids = list(range(13050, 160000))
        films_data = fetch_films_by_ids(film_ids)

        with open("films_db.json", "w", encoding="utf-8") as f:
            json.dump(films_data, f, ensure_ascii=False, indent=4)
    finally:
        conn.close()

    print("Данные успешно сохранены в базу данных и файл films_db.json.")
