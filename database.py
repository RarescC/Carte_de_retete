import sqlite3
import json
import os
import bcrypt
from email_validator import validate_email, EmailNotValidError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "recipes_app.db")
SEED_JSON_PATH = os.path.join(BASE_DIR, "recipes_seed.json")

class UserData(dict):
    def __iter__(self):
        yield self["id"]
        yield self["email"]
        yield self["onboarding_completed"]
        yield self["preferences_json"]

    def __getitem__(self, item):
        if isinstance(item, int):
            return [self["id"], self["email"], self["onboarding_completed"], self["preferences_json"]][item]
        return super().__getitem__(item)

    def __getattr__(self, item):
        if item in self:
            return self[item]
        raise AttributeError(f"'UserData' object has no attribute '{item}'")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def format_stars(rating):
    """Transformă o notă (1-5) în reprezentare vizuală cu stele (ex: ★★★★☆ (4.2))."""
    if not rating or rating <= 0:
        return "☆☆☆☆☆ (Fără recenzii)"
    full_stars = int(round(rating))
    empty_stars = 5 - full_stars
    return "★" * full_stars + "☆" * empty_stars + f" ({rating})"

def init_db():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "email TEXT UNIQUE NOT NULL, "
            "password_hash TEXT NOT NULL, "
            "onboarding_completed INTEGER DEFAULT 0, "
            "preferences_json TEXT DEFAULT '{}')"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS recipes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, "
            "ingredients TEXT NOT NULL, "
            "instructions TEXT NOT NULL, "
            "prep_time INTEGER, "
            "calories INTEGER, "
            "appliance TEXT, "
            "created_by_user_id INTEGER,"
            "is_public INTEGER DEFAULT 1)"
        )
        cursor.execute("PRAGMA table_info(recipes)")
        columns = [col[1] for col in cursor.fetchall()]
        if "is_public" not in columns:
            cursor.execute("ALTER TABLE recipes ADD COLUMN is_public INTEGER DEFAULT 1")
            cursor.execute("UPDATE recipes SET is_public = 1 WHERE is_public IS NULL")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS reviews ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, "
            "recipe_id INTEGER NOT NULL, "
            "rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5), "
            "comment TEXT, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE(user_id, recipe_id))"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS favorites ("
            "user_id INTEGER, "
            "recipe_id INTEGER, "
            "PRIMARY KEY (user_id, recipe_id))"
        )
        conn.commit()
    finally:
        conn.close()
    seed_default_recipes()

def import_recipes_from_json(json_path, user_id=None, default_is_public=1):
    """Importă rețete dintr-un fișier JSON extern în baza de date, ignorând titlurile deja existente."""
    if not os.path.exists(json_path):
        return 0, f"Fișierul nu a fost găsit: {json_path}"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            recipes_list = json.load(f)
    except Exception as e:
        return 0, f"Eroare la citirea JSON: {e}"

    if not isinstance(recipes_list, list):
        return 0, "Format invalid: fișierul JSON trebuie să conțină o listă de rețete."

    conn = get_db_connection()
    inserted_count = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT LOWER(title) FROM recipes WHERE is_public = 1 OR created_by_user_id = ?", (user_id,))
        existing_titles = {row[0] for row in cursor.fetchall()}

        to_insert = []
        for item in recipes_list:
            title = str(item.get("title", "")).strip()
            ingredients = str(item.get("ingredients", "")).strip()
            instructions = str(item.get("instructions", "")).strip()

            if not title or not ingredients or not instructions:
                continue
            if title.lower() in existing_titles:
                continue

            cleaned_ingr = ", ".join([i.strip().lower() for i in ingredients.split(",") if i.strip()])
            prep_time = int(item.get("prep_time", 0) or 0)
            calories = int(item.get("calories", 0) or 0)
            appliance = str(item.get("appliance", "Plită")).strip() or "Plită"
            is_public_val = int(item.get("is_public", default_is_public))

            to_insert.append((title, cleaned_ingr, instructions, prep_time, calories, appliance, user_id, is_public_val))
            existing_titles.add(title.lower())

        if to_insert:
            cursor.executemany(
                "INSERT INTO recipes (title, ingredients, instructions, prep_time, calories, appliance, created_by_user_id, is_public) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                to_insert
            )
            conn.commit()
            inserted_count = len(to_insert)

        return inserted_count, "Succes"
    finally:
        conn.close()


def get_recipes(user_id, ingredient_query="", filter_mode="all"):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Regula de bază de vizibilitate: vezi doar rețetele publice (is_public = 1)
        # SAU rețetele private create chiar de tine (created_by_user_id = user_id)
        params = [user_id, user_id]
        where_clauses = ["(r.is_public = 1 OR r.created_by_user_id = ?)"]

        if filter_mode == "favorites":
            where_clauses.append("f_check.recipe_id IS NOT NULL")
        elif filter_mode == "my_recipes":
            where_clauses.append("r.created_by_user_id = ?")
            params.append(user_id)
        elif filter_mode == "private_only":
            where_clauses.append("r.created_by_user_id = ? AND r.is_public = 0")
            params.append(user_id)
        elif filter_mode == "public_only":
            where_clauses.append("r.is_public = 1")

        if ingredient_query and ingredient_query.strip():
            clean_query = f"%{ingredient_query.strip().lower()}%"
            where_clauses.append("LOWER(r.ingredients) LIKE ?")
            params.append(clean_query)

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        sql = f"""
            SELECT 
                r.id, 
                r.title, 
                r.ingredients, 
                r.instructions, 
                r.prep_time, 
                r.calories, 
                r.appliance, 
                r.created_by_user_id,
                r.is_public,
                CASE WHEN f_check.recipe_id IS NOT NULL THEN 1 ELSE 0 END AS is_favorite
            FROM recipes r
            LEFT JOIN favorites f_check ON r.id = f_check.recipe_id AND f_check.user_id = ?
            {where_sql}
            ORDER BY r.id DESC
        """
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        recipes = []
        for row in rows:
            recipes.append({
                "id": row[0],
                "title": row[1],
                "ingredients": row[2],
                "instructions": row[3],
                "prep_time": row[4],
                "calories": row[5],
                "appliance": row[6],
                "created_by_user_id": row[7],
                "is_public": bool(row[8]),
                "is_favorite": bool(row[9])
            })
        return recipes
    finally:
        conn.close()


def add_custom_recipe(user_id, title, ingredients, instructions, prep_time, calories, appliance, is_public=0):
    cleaned_ingredients = ", ".join([item.strip().lower() for item in ingredients.split(",") if item.strip()])
    try:
        prep_time_int = int(prep_time)
    except (ValueError, TypeError):
        prep_time_int = 0

    try:
        calories_int = int(calories)
    except (ValueError, TypeError):
        calories_int = 0

    is_public_int = 1 if is_public else 0

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recipes (title, ingredients, instructions, prep_time, calories, appliance, created_by_user_id, is_public) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                title.strip(),
                cleaned_ingredients,
                instructions.strip(),
                prep_time_int,
                calories_int,
                appliance.strip() if appliance else "Plită",
                user_id,
                is_public_int
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def delete_private_recipe(user_id, recipe_id):
    """Șterge o rețetă DOAR dacă este privată (is_public = 0) și aparține utilizatorului curent."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM recipes WHERE id = ? AND created_by_user_id = ? AND is_public = 0",
            (recipe_id, user_id)
        )
        deleted = cursor.rowcount > 0
        if deleted:
            cursor.execute("DELETE FROM favorites WHERE recipe_id = ?", (recipe_id,))
        conn.commit()
        return deleted
    finally:
        conn.close()

def seed_default_recipes():
    """Sincronizează baza de date cu fișierul extern recipes_seed.json."""
    if os.path.exists(SEED_JSON_PATH):
        import_recipes_from_json(SEED_JSON_PATH, user_id=None)

def validate_user_email(email):
    if not email or not isinstance(email, str):
        return False, "Adresa de email este obligatorie."
    try:
        info = validate_email(email.strip(), check_deliverability=True)
        return True, info.normalized
    except EmailNotValidError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def register_user(email, password):
    if not password:
        return False, "Parola nu poate fi goală."
    is_valid, email_or_error = validate_user_email(email)
    if not is_valid:
        return False, email_or_error
    normalized_email = email_or_error
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, onboarding_completed, preferences_json) VALUES (?, ?, 0, '{}')",
            (normalized_email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        user_data = UserData({
            "id": user_id,
            "email": normalized_email,
            "onboarding_completed": 0,
            "preferences_json": "{}"
        })
        return True, user_data
    except sqlite3.IntegrityError:
        return False, "Un cont cu această adresă de email există deja."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def authenticate_user(email, password):
    if not email or not password:
        return None
    normalized_input = email.strip().lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, password_hash, onboarding_completed, preferences_json FROM users WHERE LOWER(email) = ?",
            (normalized_input,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        user_id, stored_email, stored_hash, onboarding_completed, preferences_json = row
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return UserData({
                "id": user_id,
                "email": stored_email,
                "onboarding_completed": onboarding_completed,
                "preferences_json": preferences_json
            })
        return None
    finally:
        conn.close()

def save_preferences(user_id, preferences_dict):
    preferences_json = json.dumps(preferences_dict)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET preferences_json = ?, onboarding_completed = 1 WHERE id = ?",
            (preferences_json, user_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, onboarding_completed, preferences_json FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return UserData({
            "id": row[0],
            "email": row[1],
            "onboarding_completed": row[2],
            "preferences_json": row[3]
        })
    finally:
        conn.close()

def get_recipes(user_id, ingredient_query="", filter_mode="all"):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        params = [user_id, user_id]
        where_clauses = ["(r.is_public = 1 OR (r.is_public = 0 AND r.created_by_user_id = ?))"]

        if filter_mode == "favorites":
            where_clauses.append("f_check.recipe_id IS NOT NULL")
        elif filter_mode == "my_recipes":
            where_clauses.append("r.created_by_user_id = ?")
            params.append(user_id)

        if ingredient_query and ingredient_query.strip():
            clean_query = f"%{ingredient_query.strip().lower()}%"
            where_clauses.append("LOWER(r.ingredients) LIKE ?")
            params.append(clean_query)

        where_sql = f"WHERE {' AND '.join(where_clauses)}"

        sql = f"""
            SELECT 
                r.id, 
                r.title, 
                r.ingredients, 
                r.instructions, 
                r.prep_time, 
                r.calories, 
                r.appliance, 
                r.created_by_user_id,
                r.is_public,
                CASE WHEN f_check.recipe_id IS NOT NULL THEN 1 ELSE 0 END AS is_favorite,
                COALESCE(ROUND(AVG(rev.rating), 1), 0) AS avg_rating,
                COUNT(DISTINCT rev.id) AS review_count
            FROM recipes r
            LEFT JOIN favorites f_check ON r.id = f_check.recipe_id AND f_check.user_id = ?
            LEFT JOIN reviews rev ON r.id = rev.recipe_id
            {where_sql}
            GROUP BY r.id
            ORDER BY r.id DESC
        """
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        recipes = []
        for row in rows:
            avg_rating = row[10]
            recipes.append({
                "id": row[0],
                "title": row[1],
                "ingredients": row[2],
                "instructions": row[3],
                "prep_time": row[4],
                "calories": row[5],
                "appliance": row[6],
                "created_by_user_id": row[7],
                "is_public": bool(row[8]),
                "is_favorite": bool(row[9]),
                "avg_rating": avg_rating,
                "review_count": row[11],
                "stars": format_stars(avg_rating)
            })
        return recipes
    finally:
        conn.close()

def is_favorite(user_id, recipe_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND recipe_id = ?",
            (user_id, recipe_id)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()

def toggle_favorite(user_id, recipe_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND recipe_id = ?",
            (user_id, recipe_id)
        )
        if cursor.fetchone():
            cursor.execute(
                "DELETE FROM favorites WHERE user_id = ? AND recipe_id = ?",
                (user_id, recipe_id)
            )
            conn.commit()
            return False
        else:
            cursor.execute(
                "INSERT INTO favorites (user_id, recipe_id) VALUES (?, ?)",
                (user_id, recipe_id)
            )
            conn.commit()
            return True
    finally:
        conn.close()
def add_or_update_review(user_id, recipe_id, rating, comment=""):
    """Salvează sau actualizează review-ul cu stele (1-5) al unui utilizator."""
    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            return False, "Alege între 1 și 5 stele."
    except (ValueError, TypeError):
        return False, "Număr de stele invalid."

    clean_comment = comment.strip() if comment else ""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reviews (user_id, recipe_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, recipe_id) DO UPDATE SET
                rating = excluded.rating,
                comment = excluded.comment,
                created_at = CURRENT_TIMESTAMP
            """,
            (user_id, recipe_id, rating_int, clean_comment)
        )
        conn.commit()
        return True, "Review salvat cu succes!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_recipe_reviews(recipe_id):
    """Returnează toate review-urile unei rețete, cu stelele formatate (ex: ★★★★☆)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT rev.id, u.email, rev.rating, rev.comment, rev.created_at, rev.user_id
            FROM reviews rev
            JOIN users u ON rev.user_id = u.id
            WHERE rev.recipe_id = ?
            ORDER BY rev.created_at DESC
            """,
            (recipe_id,)
        )
        rows = cursor.fetchall()
        reviews = []
        for row in rows:
            author_name = row[1].split("@")[0]
            rating_val = row[2]
            reviews.append({
                "id": row[0],
                "author": author_name,
                "rating": rating_val,
                "stars": "★" * rating_val + "☆" * (5 - rating_val),
                "comment": row[3],
                "created_at": row[4],
                "user_id": row[5]
            })
        return reviews
    finally:
        conn.close()

def get_recipe_rating_stats(recipe_id):
    """Returnează media stelelor și numărul total de review-uri pentru o rețetă."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ROUND(AVG(rating), 1), COUNT(*) FROM reviews WHERE recipe_id = ?",
            (recipe_id,)
        )
        avg_rating, total_reviews = cursor.fetchone()
        avg_val = avg_rating if avg_rating is not None else 0.0
        return {
            "average": avg_val,
            "stars": format_stars(avg_val),
            "count": total_reviews
        }
    finally:
        conn.close()
init_db()
