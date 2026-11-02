import sqlite3
import json
import os
import bcrypt
from email_validator import validate_email, EmailNotValidError

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipes_app.db")

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
            "created_by_user_id INTEGER)"
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

def seed_default_recipes():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM recipes")
        count = cursor.fetchone()[0]
        if count == 0:
            default_recipes = [
                (
                    "Paste Carbonara",
                    "paste, oua, bacon, parmezan, piper negru, sare",
                    "1. Pune pastele la fiert în apă cu sare conform instrucțiunilor de pe ambalaj.\n"
                    "2. Rumenește baconul tăiat cubulețe într-o tigaie încăpătoare până devine crocant.\n"
                    "3. Într-un bol, bate ouăle cu parmezanul ras și mult piper măcinat proaspăt.\n"
                    "4. Scurge pastele păstrând o cană mică de apă de la fiert, amestecă-le cu baconul și oprește focul.\n"
                    "5. Toarnă compoziția de ou și parmezan, amestecând energic pentru a obține un sos cremos catifelat.",
                    20,
                    650,
                    "Plită",
                    None
                ),
                (
                    "Pui la Airfryer cu cartofi",
                    "piept de pui, cartofi, ulei de masline, boia dulce, usturoi pudra, rozmarin, sare, piper",
                    "1. Taie pieptul de pui și cartofii în cuburi potrivite.\n"
                    "2. Condimentează totul cu ulei de măsline, boia dulce, usturoi pudră, rozmarin, sare și piper.\n"
                    "3. Preîncălzește Airfryer-ul la 190°C.\n"
                    "4. Pune ingredientele în coș și gătește timp de 20-25 de minute, agitând coșul la jumătatea timpului.",
                    25,
                    480,
                    "Airfryer",
                    None
                ),
                (
                    "Omletă proteică cu spanac și feta",
                    "oua, albus de ou, spanac, branza feta, rosii cherry, ulei de masline, sare, piper",
                    "1. Bate ouăle și albușurile într-un bol cu puțină sare și piper măcinat.\n"
                    "2. Călește spanacul proaspăt și roșiile cherry tăiate în două într-o tigaie cu ulei de măsline.\n"
                    "3. Toarnă compoziția de ou și lasă să se gătească la foc mediu timp de 3-4 minute.\n"
                    "4. Presară brânza feta mărunțită deasupra și împăturește omleta înainte de servire.",
                    12,
                    340,
                    "Plită",
                    None
                ),
                (
                    "Supă cremă de linte roșie",
                    "linte rosie, morcovi, ceapa, usturoi, cartofi, chimen, lamaie, ulei de masline, sare",
                    "1. Spală bine lintea roșie sub jet de apă rece.\n"
                    "2. Călește ceapa, morcovul și usturoiul tocate mărunt într-o oală cu o lingură de ulei.\n"
                    "3. Adaugă cartoful tăiat cuburi, lintea și apă cât să le acopere cu două degete.\n"
                    "4. Fierbe 20 de minute până când legumele sunt moi, apoi pasează cu blenderul vertical.\n"
                    "5. Asezonează cu chimen măcinat și servește cu zeamă proaspătă de lămâie.",
                    30,
                    290,
                    "Plită",
                    None
                ),
                (
                    "Somon la cuptor cu broccoli",
                    "file de somon, broccoli, lamaie, usturoi, ulei de masline, sare, piper, marar",
                    "1. Preîncălzește cuptorul la 200°C și pregătește o tavă tapetată cu hârtie de copt.\n"
                    "2. Așază fileul de somon și buchețelele de broccoli pe tavă.\n"
                    "3. Stropește cu ulei de măsline, suc proaspăt de lămâie, usturoi pisat, sare și piper.\n"
                    "4. Coace timp de 15-18 minute până când somonul este fraged și suculent.",
                    25,
                    520,
                    "Cuptor",
                    None
                ),
                (
                    "Clătite cu ovăz și banană",
                    "fulgi de ovaz, banana, oua, lapte, praf de copt, scortisoara, miere, fructe de padure",
                    "1. Pune fulgii de ovăz, banana bine coaptă, ouăle, laptele și praful de copt într-un blender.\n"
                    "2. Mixează la viteză mare până obții un aluat fin și dens.\n"
                    "3. Încinge o tigaie antiaderentă la foc mediu și coace mici clătite câte 2 minute pe fiecare parte.\n"
                    "4. Servește calde cu miere naturală și fructe de pădure proaspete.",
                    15,
                    380,
                    "Plită",
                    None
                )
            ]
            cursor.executemany(
                "INSERT INTO recipes (title, ingredients, instructions, prep_time, calories, appliance, created_by_user_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                default_recipes
            )
            conn.commit()
    finally:
        conn.close()

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
        params = [user_id]
        where_clauses = []

        if filter_mode == "favorites":
            where_clauses.append("f_check.recipe_id IS NOT NULL")
        elif filter_mode == "my_recipes":
            where_clauses.append("r.created_by_user_id = ?")
            params.append(user_id)

        if ingredient_query and ingredient_query.strip():
            clean_query = f"%{ingredient_query.strip().lower()}%"
            where_clauses.append("LOWER(r.ingredients) LIKE ?")
            params.append(clean_query)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

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
                "is_favorite": bool(row[8])
            })
        return recipes
    finally:
        conn.close()

def add_custom_recipe(user_id, title, ingredients, instructions, prep_time, calories, appliance):
    cleaned_ingredients = ", ".join([item.strip().lower() for item in ingredients.split(",") if item.strip()])
    try:
        prep_time_int = int(prep_time)
    except (ValueError, TypeError):
        prep_time_int = 0

    try:
        calories_int = int(calories)
    except (ValueError, TypeError):
        calories_int = 0

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recipes (title, ingredients, instructions, prep_time, calories, appliance, created_by_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                title.strip(),
                cleaned_ingredients,
                instructions.strip(),
                prep_time_int,
                calories_int,
                appliance.strip() if appliance else "Plită",
                user_id
            )
        )
        conn.commit()
        return cursor.lastrowid
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

init_db()
