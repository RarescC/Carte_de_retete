import json
import customtkinter as ctk
from database import (
    register_user,
    authenticate_user,
    save_preferences,
    get_user_by_id,
    get_recipes,
    add_custom_recipe,
    toggle_favorite
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AuthFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.master = master

        self.card = ctk.CTkFrame(self, width=420, corner_radius=16)
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = ctk.CTkLabel(
            self.card,
            text="Organizator de rețete",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(padx=30, pady=(32, 6))

        self.subtitle_label = ctk.CTkLabel(
            self.card,
            text="Etapa 1: Autentificare și Configurare",
            font=ctk.CTkFont(size=13),
            text_color="gray70"
        )
        self.subtitle_label.pack(padx=30, pady=(0, 20))

        self.mode_selector = ctk.CTkSegmentedButton(
            self.card,
            values=["Autentificare", "Înregistrare"],
            command=self.on_mode_change,
            height=36,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.mode_selector.set("Autentificare")
        self.mode_selector.pack(padx=30, pady=(0, 20), fill="x")

        self.email_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="Adresă de email",
            height=42,
            font=ctk.CTkFont(size=13)
        )
        self.email_entry.pack(padx=30, pady=(0, 12), fill="x")
        self.email_entry.bind("<Return>", lambda event: self.handle_submit())

        self.password_entry = ctk.CTkEntry(
            self.card,
            placeholder_text="Parolă",
            show="*",
            height=42,
            font=ctk.CTkFont(size=13)
        )
        self.password_entry.pack(padx=30, pady=(0, 12), fill="x")
        self.password_entry.bind("<Return>", lambda event: self.handle_submit())

        self.status_label = ctk.CTkLabel(
            self.card,
            text="",
            font=ctk.CTkFont(size=12),
            wraplength=340,
            justify="center"
        )
        self.status_label.pack(padx=30, pady=(0, 14))

        self.submit_btn = ctk.CTkButton(
            self.card,
            text="Conectare",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.handle_submit
        )
        self.submit_btn.pack(padx=30, pady=(0, 32), fill="x")

    def on_mode_change(self, mode):
        self.status_label.configure(text="")
        if mode == "Autentificare":
            self.submit_btn.configure(text="Conectare")
        else:
            self.submit_btn.configure(text="Creează cont")

    def handle_submit(self):
        email = self.email_entry.get().strip()
        password = self.password_entry.get()

        if not email or not password:
            self.status_label.configure(
                text="Te rugăm să introduci atât adresa de email, cât și parola.",
                text_color="#e74c3c"
            )
            return

        current_mode = self.mode_selector.get()
        if current_mode == "Autentificare":
            user = authenticate_user(email, password)
            if not user:
                self.status_label.configure(
                    text="Email sau parolă incorectă.",
                    text_color="#e74c3c"
                )
                return
            self.status_label.configure(
                text="Autentificare reușită!",
                text_color="#2ecc71"
            )
            if user["onboarding_completed"] == 0:
                self.master.show_questionnaire(user)
            else:
                self.master.show_dashboard(user)
        else:
            success, result = register_user(email, password)
            if not success:
                self.status_label.configure(
                    text=str(result),
                    text_color="#e74c3c"
                )
                return
            self.status_label.configure(
                text="Cont creat cu succes!",
                text_color="#2ecc71"
            )
            self.master.show_questionnaire(result)

class QuestionnaireFrame(ctk.CTkFrame):
    def __init__(self, master, user):
        super().__init__(master, fg_color="transparent")
        self.master = master
        self.user = user
        self.current_step = 1

        self.profile_data = {
            "gender": "Masculin",
            "age": "",
            "height": "",
            "weight": "",
            "activity_level": "Moderat activ (sport 3-4 ori/săptămână)",
            "nutritional_goal": "Menținere & Stil de viață sănătos",
            "diet_type": "Omnivor",
            "allergies": [],
            "disliked_ingredients": "",
            "cooking_time": "15-30 min",
            "skill_level": "Mediu",
            "appliances": []
        }

        try:
            saved_prefs = json.loads(self.user.get("preferences_json", "{}"))
            if isinstance(saved_prefs, dict):
                self.profile_data.update(saved_prefs)
        except Exception:
            pass

        self.card = ctk.CTkFrame(self, width=680, height=540, corner_radius=16)
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        self.header_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=28, pady=(20, 10))

        self.step_counter_label = ctk.CTkLabel(
            self.header_frame,
            text="Pasul 1 din 3",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3B8ED0"
        )
        self.step_counter_label.pack(anchor="w")

        self.step_title_label = ctk.CTkLabel(
            self.header_frame,
            text="Profil Fizic & Nivel de Activitate",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.step_title_label.pack(anchor="w", pady=(2, 2))

        self.step_subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Completează parametrii fizici pentru calculul necesarului caloric și de macronutrienți.",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        self.step_subtitle_label.pack(anchor="w")

        self.progress_bar = ctk.CTkProgressBar(self.card, width=624, height=8)
        self.progress_bar.pack(padx=28, pady=(0, 12), fill="x")
        self.progress_bar.set(1 / 3)

        self.content_scroll = ctk.CTkScrollableFrame(self.card, width=624, height=330, corner_radius=12)
        self.content_scroll.pack(padx=28, pady=(0, 12), fill="both", expand=True)

        self.status_label = ctk.CTkLabel(
            self.card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#e74c3c"
        )
        self.status_label.pack(padx=28, pady=(0, 8))

        self.footer_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.footer_frame.pack(fill="x", padx=28, pady=(0, 20))

        self.btn_back = ctk.CTkButton(
            self.footer_frame,
            text="Înapoi",
            width=130,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self.go_back
        )
        self.btn_back.pack(side="left")

        self.btn_next = ctk.CTkButton(
            self.footer_frame,
            text="Înainte",
            width=180,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.go_next
        )
        self.btn_next.pack(side="right")

        self.render_step()

    def clear_content(self):
        self.status_label.configure(text="")
        for widget in self.content_scroll.winfo_children():
            widget.destroy()

    def render_step(self):
        self.clear_content()

        if self.current_step == 1:
            self.step_counter_label.configure(text="Pasul 1 din 3")
            self.step_title_label.configure(text="Profil Fizic & Nivel de Activitate")
            self.step_subtitle_label.configure(text="Completează parametrii fizici pentru calculul necesarului caloric și de macronutrienți.")
            self.progress_bar.set(1 / 3)
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(text="Înainte")
            self.render_step_1()

        elif self.current_step == 2:
            self.step_counter_label.configure(text="Pasul 2 din 3")
            self.step_title_label.configure(text="Obiective Nutriționale & Restricții")
            self.step_subtitle_label.configure(text="Definește direcția nutrițională și restricțiile alimentare pentru rețete adaptate.")
            self.progress_bar.set(2 / 3)
            self.btn_back.configure(state="normal")
            self.btn_next.configure(text="Înainte")
            self.render_step_2()

        elif self.current_step == 3:
            self.step_counter_label.configure(text="Pasul 3 din 3")
            self.step_title_label.configure(text="Logistică Bucătărie & Electrocasnice")
            self.step_subtitle_label.configure(text="Indică timpul disponibil și dotările din bucătărie pentru sugestii fezabile.")
            self.progress_bar.set(3 / 3)
            self.btn_back.configure(state="normal")
            self.btn_next.configure(text="Salvează și finalizează")
            self.render_step_3()

    def render_step_1(self):
        lbl_gender = ctk.CTkLabel(self.content_scroll, text="Gen", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_gender.pack(anchor="w", padx=10, pady=(6, 4))

        self.gender_selector = ctk.CTkSegmentedButton(
            self.content_scroll,
            values=["Masculin", "Feminin", "Croissant 🥐"],
            height=36,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        current_gender = self.profile_data.get("gender", "Masculin")
        if current_gender not in ["Masculin", "Feminin", "Croissant 🥐"]:
            current_gender = "Masculin"
        self.gender_selector.set(current_gender)
        self.gender_selector.pack(fill="x", padx=10, pady=(0, 16))

        metrics_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=10, pady=(0, 16))
        metrics_frame.grid_columnconfigure((0, 1, 2), weight=1)

        lbl_age = ctk.CTkLabel(metrics_frame, text="Vârstă (ani)", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_age.grid(row=0, column=0, padx=6, pady=(0, 4), sticky="w")
        self.entry_age = ctk.CTkEntry(metrics_frame, placeholder_text="ex: 28", height=38)
        self.entry_age.grid(row=1, column=0, padx=6, sticky="ew")
        if self.profile_data.get("age"):
            self.entry_age.insert(0, str(self.profile_data["age"]))

        lbl_height = ctk.CTkLabel(metrics_frame, text="Înălțime (cm)", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_height.grid(row=0, column=1, padx=6, pady=(0, 4), sticky="w")
        self.entry_height = ctk.CTkEntry(metrics_frame, placeholder_text="ex: 175", height=38)
        self.entry_height.grid(row=1, column=1, padx=6, sticky="ew")
        if self.profile_data.get("height"):
            self.entry_height.insert(0, str(self.profile_data["height"]))

        lbl_weight = ctk.CTkLabel(metrics_frame, text="Greutate (kg)", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_weight.grid(row=0, column=2, padx=6, pady=(0, 4), sticky="w")
        self.entry_weight = ctk.CTkEntry(metrics_frame, placeholder_text="ex: 72", height=38)
        self.entry_weight.grid(row=1, column=2, padx=6, sticky="ew")
        if self.profile_data.get("weight"):
            self.entry_weight.insert(0, str(self.profile_data["weight"]))

        lbl_activity = ctk.CTkLabel(self.content_scroll, text="Nivel de activitate fizică / sport", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_activity.pack(anchor="w", padx=10, pady=(6, 4))

        activity_options = [
            "Sedentar (fără sport, muncă de birou)",
            "Ușor activ (sport 1-2 ori/săptămână)",
            "Moderat activ (sport 3-4 ori/săptămână)",
            "Foarte activ (sport 5-6 ori/săptămână)",
            "Performanță / Intens (antrenamente zilnice)"
        ]
        self.opt_activity = ctk.CTkOptionMenu(
            self.content_scroll,
            values=activity_options,
            height=38,
            font=ctk.CTkFont(size=13)
        )
        saved_activity = self.profile_data.get("activity_level", activity_options[2])
        if saved_activity in activity_options:
            self.opt_activity.set(saved_activity)
        else:
            self.opt_activity.set(activity_options[2])
        self.opt_activity.pack(fill="x", padx=10, pady=(0, 10))

    def render_step_2(self):
        lbl_goal = ctk.CTkLabel(self.content_scroll, text="Obiectiv nutrițional principal", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_goal.pack(anchor="w", padx=10, pady=(6, 4))

        goal_options = [
            "Slăbire / Deficit caloric",
            "Menținere & Stil de viață sănătos",
            "Masă musculară / Surplus caloric",
            "Energie & Performanță sportivă",
            "Buget redus / Studențesc"
        ]
        self.opt_goal = ctk.CTkOptionMenu(
            self.content_scroll,
            values=goal_options,
            height=38,
            font=ctk.CTkFont(size=13)
        )
        saved_goal = self.profile_data.get("nutritional_goal", goal_options[1])
        if saved_goal in goal_options:
            self.opt_goal.set(saved_goal)
        else:
            self.opt_goal.set(goal_options[1])
        self.opt_goal.pack(fill="x", padx=10, pady=(0, 16))

        lbl_diet = ctk.CTkLabel(self.content_scroll, text="Tip de dietă", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_diet.pack(anchor="w", padx=10, pady=(6, 4))

        diet_options = ["Omnivor", "Vegetarian", "Vegan", "Pescarian", "Keto", "High-Protein"]
        self.opt_diet = ctk.CTkOptionMenu(
            self.content_scroll,
            values=diet_options,
            height=38,
            font=ctk.CTkFont(size=13)
        )
        saved_diet = self.profile_data.get("diet_type", "Omnivor")
        if saved_diet in diet_options:
            self.opt_diet.set(saved_diet)
        else:
            self.opt_diet.set("Omnivor")
        self.opt_diet.pack(fill="x", padx=10, pady=(0, 16))

        lbl_allergies = ctk.CTkLabel(self.content_scroll, text="Alergii și intoleranțe alimentare", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_allergies.pack(anchor="w", padx=10, pady=(6, 6))

        allergies_box = ctk.CTkFrame(self.content_scroll, corner_radius=10)
        allergies_box.pack(fill="x", padx=10, pady=(0, 16))
        allergies_box.grid_columnconfigure((0, 1), weight=1)

        self.allergy_vars = {}
        allergy_list = ["Gluten", "Lactoză", "Nuci/Arahide", "Fructe de mare", "Ouă", "Soia"]
        saved_allergies = self.profile_data.get("allergies", [])

        for idx, item in enumerate(allergy_list):
            is_checked = item in saved_allergies
            var = ctk.BooleanVar(value=is_checked)
            self.allergy_vars[item] = var
            chk = ctk.CTkCheckBox(allergies_box, text=item, variable=var, font=ctk.CTkFont(size=13))
            row = idx // 2
            col = idx % 2
            chk.grid(row=row, column=col, padx=16, pady=10, sticky="w")

        lbl_disliked = ctk.CTkLabel(self.content_scroll, text="Ingrediente neplăcute / interzise", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_disliked.pack(anchor="w", padx=10, pady=(6, 4))

        self.entry_disliked = ctk.CTkEntry(
            self.content_scroll,
            placeholder_text="ex: ciuperci, coriandru, măsline, ceapă crudă",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.entry_disliked.pack(fill="x", padx=10, pady=(0, 10))
        if self.profile_data.get("disliked_ingredients"):
            self.entry_disliked.insert(0, str(self.profile_data["disliked_ingredients"]))

    def render_step_3(self):
        lbl_time = ctk.CTkLabel(self.content_scroll, text="Timp maxim de gătire per masă", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_time.pack(anchor="w", padx=10, pady=(6, 4))

        time_options = ["Sub 15 min", "15-30 min", "30-60 min", "Peste 60 min (Weekend chef)"]
        self.seg_cooking_time = ctk.CTkSegmentedButton(
            self.content_scroll,
            values=time_options,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        saved_time = self.profile_data.get("cooking_time", "15-30 min")
        if saved_time in time_options:
            self.seg_cooking_time.set(saved_time)
        else:
            self.seg_cooking_time.set("15-30 min")
        self.seg_cooking_time.pack(fill="x", padx=10, pady=(0, 16))

        lbl_skill = ctk.CTkLabel(self.content_scroll, text="Nivel de experiență în bucătărie", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_skill.pack(anchor="w", padx=10, pady=(6, 4))

        skill_options = ["Începător", "Mediu", "Avansat"]
        self.seg_skill = ctk.CTkSegmentedButton(
            self.content_scroll,
            values=skill_options,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        saved_skill = self.profile_data.get("skill_level", "Mediu")
        if saved_skill in skill_options:
            self.seg_skill.set(saved_skill)
        else:
            self.seg_skill.set("Mediu")
        self.seg_skill.pack(fill="x", padx=10, pady=(0, 16))

        lbl_appliances = ctk.CTkLabel(
            self.content_scroll,
            text="Electrocasnice disponibile & Model specific (opțional)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_appliances.pack(anchor="w", padx=10, pady=(6, 6))

        appliances_box = ctk.CTkFrame(self.content_scroll, corner_radius=10)
        appliances_box.pack(fill="x", padx=10, pady=(0, 10))
        appliances_box.grid_columnconfigure(0, weight=1)
        appliances_box.grid_columnconfigure(1, weight=1)

        available_appliances = [
            "Cuptor clasic",
            "Plită (Gaz / Inducție)",
            "Airfryer",
            "Cuptor cu microunde",
            "Blender / NutriBullet",
            "Robot de bucătărie",
            "Multicooker / Instant Pot",
            "Grill electric / Sandwich Maker"
        ]

        saved_appliances_map = {}
        raw_saved_appliances = self.profile_data.get("appliances", [])
        if isinstance(raw_saved_appliances, list):
            for item in raw_saved_appliances:
                if isinstance(item, dict) and "name" in item:
                    saved_appliances_map[item["name"]] = item.get("model", "")
                elif isinstance(item, str):
                    saved_appliances_map[item] = ""
        elif isinstance(raw_saved_appliances, dict):
            saved_appliances_map = raw_saved_appliances

        self.appliance_widgets = {}
        for idx, app_name in enumerate(available_appliances):
            is_checked = app_name in saved_appliances_map
            chk_var = ctk.BooleanVar(value=is_checked)
            chk = ctk.CTkCheckBox(
                appliances_box,
                text=app_name,
                variable=chk_var,
                font=ctk.CTkFont(size=13)
            )
            chk.grid(row=idx, column=0, padx=(14, 10), pady=7, sticky="w")

            entry = ctk.CTkEntry(
                appliances_box,
                placeholder_text="Model (ex: Philips XXL, Tefal, Bosch...)",
                height=32,
                font=ctk.CTkFont(size=12)
            )
            if is_checked and saved_appliances_map[app_name]:
                entry.insert(0, saved_appliances_map[app_name])
            entry.grid(row=idx, column=1, padx=(6, 14), pady=7, sticky="ew")

            self.appliance_widgets[app_name] = {
                "var": chk_var,
                "entry": entry
            }

    def save_current_inputs(self):
        if self.current_step == 1:
            self.profile_data["gender"] = self.gender_selector.get()
            self.profile_data["age"] = self.entry_age.get().strip()
            self.profile_data["height"] = self.entry_height.get().strip()
            self.profile_data["weight"] = self.entry_weight.get().strip()
            self.profile_data["activity_level"] = self.opt_activity.get()
        elif self.current_step == 2:
            self.profile_data["nutritional_goal"] = self.opt_goal.get()
            self.profile_data["diet_type"] = self.opt_diet.get()
            self.profile_data["allergies"] = [name for name, var in self.allergy_vars.items() if var.get()]
            self.profile_data["disliked_ingredients"] = self.entry_disliked.get().strip()
        elif self.current_step == 3:
            self.profile_data["cooking_time"] = self.seg_cooking_time.get()
            self.profile_data["skill_level"] = self.seg_skill.get()
            selected_appliances = []
            for name, controls in self.appliance_widgets.items():
                if controls["var"].get():
                    model_text = controls["entry"].get().strip()
                    selected_appliances.append({"name": name, "model": model_text})
            self.profile_data["appliances"] = selected_appliances

    def validate_step(self):
        if self.current_step == 1:
            age_str = self.entry_age.get().strip()
            height_str = self.entry_height.get().strip()
            weight_str = self.entry_weight.get().strip()

            if not age_str or not height_str or not weight_str:
                self.status_label.configure(text="Te rugăm să completezi vârsta, înălțimea și greutatea.")
                return False

            try:
                age_val = int(age_str)
                height_val = float(height_str)
                weight_val = float(weight_str)
            except ValueError:
                self.status_label.configure(text="Vârsta, înălțimea și greutatea trebuie să fie valori numerice valide.")
                return False

            if not (10 <= age_val <= 120):
                self.status_label.configure(text="Te rugăm să introduci o vârstă validă (între 10 și 120 ani).")
                return False

            if not (50 <= height_val <= 260):
                self.status_label.configure(text="Te rugăm să introduci o înălțime validă (între 50 și 260 cm).")
                return False

            if not (20 <= weight_val <= 350):
                self.status_label.configure(text="Te rugăm să introduci o greutate validă (între 20 și 350 kg).")
                return False

        return True

    def go_back(self):
        if self.current_step > 1:
            self.save_current_inputs()
            self.current_step -= 1
            self.render_step()

    def go_next(self):
        if not self.validate_step():
            return

        self.save_current_inputs()

        if self.current_step < 3:
            self.current_step += 1
            self.render_step()
        else:
            save_preferences(self.user["id"], self.profile_data)
            refreshed = get_user_by_id(self.user["id"])
            if refreshed:
                self.user = refreshed
            else:
                self.user["onboarding_completed"] = 1
                self.user["preferences_json"] = json.dumps(self.profile_data)
            self.master.show_dashboard(self.user)

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, user):
        super().__init__(master, fg_color="transparent")
        self.master = master
        self.user = user
        self.active_tab = "all"
        self.current_search_query = ""

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.brand_label = ctk.CTkLabel(
            self.sidebar,
            text="Organizator de rețete",
            font=ctk.CTkFont(size=17, weight="bold")
        )
        self.brand_label.pack(padx=20, pady=(20, 14), anchor="w")

        self.account_card = ctk.CTkFrame(self.sidebar, corner_radius=8, fg_color=("#e6e6e6", "#2a2d32"))
        self.account_card.pack(fill="x", padx=16, pady=(0, 16))

        self.account_tag = ctk.CTkLabel(
            self.account_card,
            text="Utilizator conectat",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="gray70"
        )
        self.account_tag.pack(padx=12, pady=(8, 2), anchor="w")

        self.email_display = ctk.CTkLabel(
            self.account_card,
            text=self.user["email"],
            font=ctk.CTkFont(size=12),
            wraplength=170,
            justify="left"
        )
        self.email_display.pack(padx=12, pady=(0, 8), anchor="w")

        self.nav_buttons = {}

        self.btn_all = ctk.CTkButton(
            self.sidebar,
            text="Toate Rețetele",
            height=36,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.switch_tab("all")
        )
        self.btn_all.pack(fill="x", padx=16, pady=4)
        self.nav_buttons["all"] = self.btn_all

        self.btn_fav = ctk.CTkButton(
            self.sidebar,
            text="Favorite ⭐",
            height=36,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.switch_tab("favorites")
        )
        self.btn_fav.pack(fill="x", padx=16, pady=4)
        self.nav_buttons["favorites"] = self.btn_fav

        self.btn_my = ctk.CTkButton(
            self.sidebar,
            text="Adăugate de mine ✍️",
            height=36,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.switch_tab("my_recipes")
        )
        self.btn_my.pack(fill="x", padx=16, pady=4)
        self.nav_buttons["my_recipes"] = self.btn_my

        self.btn_ai = ctk.CTkButton(
            self.sidebar,
            text="AI Chef 🤖",
            height=36,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.switch_tab("ai_chef")
        )
        self.btn_ai.pack(fill="x", padx=16, pady=4)
        self.nav_buttons["ai_chef"] = self.btn_ai

        self.btn_edit_profile = ctk.CTkButton(
            self.sidebar,
            text="Editează Chestionar",
            height=36,
            anchor="w",
            font=ctk.CTkFont(size=13),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=lambda: self.master.show_questionnaire(self.user)
        )
        self.btn_edit_profile.pack(fill="x", padx=16, pady=4)

        self.spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.spacer.pack(fill="both", expand=True)

        self.logout_btn = ctk.CTkButton(
            self.sidebar,
            text="Deconectare",
            height=36,
            fg_color="#c0392b",
            hover_color="#962d22",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.master.show_auth
        )
        self.logout_btn.pack(fill="x", padx=16, pady=20)

        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.pack(side="right", fill="both", expand=True, padx=22, pady=18)

        self.tdee_banner = ctk.CTkFrame(self.main_content, corner_radius=10, fg_color=("#3B8ED0", "#1f6aa5"), height=46)
        self.tdee_banner.pack(fill="x", pady=(0, 14))
        self.tdee_banner.pack_propagate(False)

        self.tdee_label = ctk.CTkLabel(
            self.tdee_banner,
            text=self.get_tdee_banner_text(),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white"
        )
        self.tdee_label.pack(expand=True)

        self.search_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.search_frame.pack(fill="x", pady=(0, 12))

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Caută după ingredient (ex: pui, usturoi, ouă)...",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<Return>", lambda event: self.handle_search())

        self.btn_search = ctk.CTkButton(
            self.search_frame,
            text="Caută",
            width=80,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.handle_search
        )
        self.btn_search.pack(side="left", padx=(0, 8))

        self.btn_reset = ctk.CTkButton(
            self.search_frame,
            text="Resetează",
            width=85,
            height=38,
            fg_color=("gray70", "gray35"),
            hover_color=("gray60", "gray45"),
            font=ctk.CTkFont(size=13),
            command=self.handle_reset_search
        )
        self.btn_reset.pack(side="left", padx=(0, 8))

        self.btn_add_recipe = ctk.CTkButton(
            self.search_frame,
            text="+ Rețetă Nouă",
            width=120,
            height=38,
            fg_color="#27ae60",
            hover_color="#219653",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.open_add_recipe_modal
        )
        self.btn_add_recipe.pack(side="right")

        self.cards_scroll = ctk.CTkScrollableFrame(self.main_content, corner_radius=12)
        self.cards_scroll.pack(fill="both", expand=True)

        self.update_tab_visuals()
        self.load_recipes()

    def get_tdee_banner_text(self):
        try:
            prefs = json.loads(self.user.get("preferences_json", "{}"))
            if not isinstance(prefs, dict):
                prefs = {}
        except Exception:
            prefs = {}

        gender = prefs.get("gender", "Masculin")

        try:
            weight = float(prefs.get("weight", 70))
        except (ValueError, TypeError):
            weight = 70.0

        try:
            height = float(prefs.get("height", 175))
        except (ValueError, TypeError):
            height = 175.0

        try:
            age = int(prefs.get("age", 25))
        except (ValueError, TypeError):
            age = 25

        if gender == "Feminin":
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age + 5

        activity_text = str(prefs.get("activity_level", ""))
        if "Sedentar" in activity_text:
            activity_mult = 1.2
        elif "Ușor" in activity_text:
            activity_mult = 1.375
        elif "Moderat" in activity_text:
            activity_mult = 1.55
        elif "Foarte" in activity_text:
            activity_mult = 1.725
        elif "Performanță" in activity_text or "Intens" in activity_text:
            activity_mult = 1.9
        else:
            activity_mult = 1.55

        tdee = bmr * activity_mult
        goal_text = str(prefs.get("nutritional_goal", ""))
        if "Slăbire" in goal_text or "Deficit" in goal_text:
            tdee -= 400
        elif "Masă musculară" in goal_text or "Surplus" in goal_text:
            tdee += 350
        elif "Energie" in goal_text:
            tdee += 200

        target_cals = max(1200, int(round(tdee)))
        protein_g = max(45, int(round(weight * 2.0)))
        fat_g = max(35, int(round(weight * 0.9)))
        remaining_cals = max(0, target_cals - (protein_g * 4 + fat_g * 9))
        carbs_g = max(40, int(round(remaining_cals / 4)))

        if gender == "Croissant 🥐":
            return f"Profil Metabolic: 80% Unt, 20% Fericire 🥐 | Target Zilnic: {target_cals} kcal | P: {protein_g}g | C: {carbs_g}g | F: {fat_g}g"
        return f"Target Zilnic: {target_cals} kcal | P: {protein_g}g | C: {carbs_g}g | F: {fat_g}g"

    def update_tab_visuals(self):
        for tab_key, btn in self.nav_buttons.items():
            if tab_key == self.active_tab:
                btn.configure(fg_color=("#3B8ED0", "#1f6aa5"))
            else:
                btn.configure(fg_color=("gray75", "gray25"))

    def switch_tab(self, tab_key):
        self.active_tab = tab_key
        self.update_tab_visuals()
        self.load_recipes()

    def handle_search(self):
        self.current_search_query = self.search_entry.get().strip()
        self.load_recipes()

    def handle_reset_search(self):
        self.search_entry.delete(0, "end")
        self.current_search_query = ""
        self.load_recipes()

    def load_recipes(self):
        for widget in self.cards_scroll.winfo_children():
            widget.destroy()

        if self.active_tab == "ai_chef":
            self.render_ai_chef_placeholder()
            return

        recipes = get_recipes(
            self.user["id"],
            ingredient_query=self.current_search_query,
            filter_mode=self.active_tab
        )

        if not recipes:
            if self.current_search_query:
                msg = f"Nicio rețetă găsită care să conțină ingredientul: '{self.current_search_query}'"
            elif self.active_tab == "favorites":
                msg = "Nu ai nicio rețetă favorită încă. Apasă pe '⭐ Adaugă favorit' pe orice rețetă!"
            elif self.active_tab == "my_recipes":
                msg = "Nu ai adăugat încă nicio rețetă proprie. Apasă pe '+ Rețetă Nouă' pentru a crea una!"
            else:
                msg = "Nu există rețete disponibile momentan."

            empty_card = ctk.CTkFrame(self.cards_scroll, corner_radius=12, height=180)
            empty_card.pack(fill="x", padx=10, pady=20)
            lbl = ctk.CTkLabel(
                empty_card,
                text=msg,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="gray60"
            )
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            return

        for recipe in recipes:
            self.render_recipe_card(recipe)

    def render_ai_chef_placeholder(self):
        card = ctk.CTkFrame(self.cards_scroll, corner_radius=12)
        card.pack(fill="both", expand=True, padx=20, pady=30)

        title = ctk.CTkLabel(
            card,
            text="Asistent Bucătar AI (Etapa 2) 🤖",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(40, 10))

        desc = ctk.CTkLabel(
            card,
            text="Modulul inteligent de generare a rețetelor bazat pe profilul tău metabolic,\n"
                 "alergiile raportate și electrocasnicele pe care le deții va fi disponibil în Etapa 2!",
            font=ctk.CTkFont(size=13),
            text_color="gray70",
            justify="center"
        )
        desc.pack(pady=(0, 40))

    def render_recipe_card(self, recipe):
        card = ctk.CTkFrame(self.cards_scroll, corner_radius=12)
        card.pack(fill="x", padx=6, pady=8)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 4))

        title_lbl = ctk.CTkLabel(
            top_row,
            text=recipe["title"],
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        title_lbl.pack(side="left")

        appliance_name = recipe.get("appliance") or "Plită"
        appliance_tag = ctk.CTkLabel(
            top_row,
            text=f"  {appliance_name}  ",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
            fg_color=("#d0e1fd", "#1f3a5f"),
            text_color=("#1a5276", "#aed6f1")
        )
        appliance_tag.pack(side="left", padx=12)

        fav_active = recipe.get("is_favorite", False)
        fav_btn = ctk.CTkButton(
            top_row,
            text="⭐ Favorit" if fav_active else "☆ Adaugă favorit",
            width=130,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#f39c12" if fav_active else ("gray75", "gray30"),
            hover_color="#d68910" if fav_active else ("gray65", "gray40"),
            command=lambda r=recipe: self.handle_toggle_fav(r)
        )
        fav_btn.pack(side="right")

        meta_row = ctk.CTkFrame(card, fg_color="transparent")
        meta_row.pack(fill="x", padx=16, pady=(2, 4))

        prep_time = recipe.get("prep_time", 0)
        calories = recipe.get("calories", 0)
        meta_lbl = ctk.CTkLabel(
            meta_row,
            text=f"⏱️ Timp: {prep_time} min   |   🔥 Calorii: {calories} kcal / porție",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        meta_lbl.pack(anchor="w")

        ingr_row = ctk.CTkFrame(card, fg_color="transparent")
        ingr_row.pack(fill="x", padx=16, pady=(2, 8))

        ingr_lbl = ctk.CTkLabel(
            ingr_row,
            text=f"🥗 Ingrediente: {recipe.get('ingredients', '')}",
            font=ctk.CTkFont(size=12),
            wraplength=480,
            justify="left",
            anchor="w"
        )
        ingr_lbl.pack(anchor="w")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        view_btn = ctk.CTkButton(
            btn_row,
            text="Vezi Rețeta",
            width=110,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda r=recipe: self.open_recipe_modal(r)
        )
        view_btn.pack(side="left")

    def handle_toggle_fav(self, recipe):
        new_state = toggle_favorite(self.user["id"], recipe["id"])
        recipe["is_favorite"] = new_state
        self.load_recipes()

    def open_recipe_modal(self, recipe):
        modal = ctk.CTkToplevel(self)
        modal.title(recipe["title"])
        modal.geometry("540x520")
        modal.minsize(480, 440)
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        content = ctk.CTkScrollableFrame(modal, corner_radius=12)
        content.pack(fill="both", expand=True, padx=20, pady=20)

        title = ctk.CTkLabel(
            content,
            text=recipe["title"],
            font=ctk.CTkFont(size=20, weight="bold"),
            wraplength=460,
            justify="left"
        )
        title.pack(anchor="w", pady=(4, 6))

        appliance = recipe.get("appliance") or "Plită"
        prep_time = recipe.get("prep_time", 0)
        calories = recipe.get("calories", 0)

        meta = ctk.CTkLabel(
            content,
            text=f"⚡ Aparat: {appliance}   |   ⏱️ Timp: {prep_time} min   |   🔥 Calorii: {calories} kcal",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#3B8ED0",
            anchor="w"
        )
        meta.pack(anchor="w", pady=(0, 14))

        ingr_title = ctk.CTkLabel(
            content,
            text="Ingrediente necesare:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        ingr_title.pack(anchor="w", pady=(0, 4))

        raw_ingr = recipe.get("ingredients", "")
        ingr_items = [i.strip() for i in raw_ingr.split(",") if i.strip()]
        ingr_text = "\n".join([f"• {item}" for item in ingr_items])
        ingr_lbl = ctk.CTkLabel(
            content,
            text=ingr_text,
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w"
        )
        ingr_lbl.pack(anchor="w", pady=(0, 16), padx=10)

        instr_title = ctk.CTkLabel(
            content,
            text="Mod de preparare:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        instr_title.pack(anchor="w", pady=(0, 4))

        instructions_box = ctk.CTkTextbox(content, height=160, font=ctk.CTkFont(size=13), wrap="word")
        instructions_box.insert("1.0", recipe.get("instructions", ""))
        instructions_box.configure(state="disabled")
        instructions_box.pack(fill="x", pady=(0, 16))

        btn_close = ctk.CTkButton(
            content,
            text="Închide",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=modal.destroy
        )
        btn_close.pack(fill="x", pady=(0, 8))

    def open_add_recipe_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Adaugă Rețetă Nouă")
        modal.geometry("540x560")
        modal.minsize(480, 500)
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        content = ctk.CTkScrollableFrame(modal, corner_radius=12)
        content.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkLabel(
            content,
            text="Creare Rețetă Personalizată",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header.pack(anchor="w", pady=(0, 14))

        lbl_title = ctk.CTkLabel(content, text="Titlu rețetă *", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_title.pack(anchor="w", pady=(0, 2))
        entry_title = ctk.CTkEntry(content, placeholder_text="ex: Paste cu ton și roșii cherry", height=38)
        entry_title.pack(fill="x", pady=(0, 10))

        lbl_ingr = ctk.CTkLabel(content, text="Ingrediente (separate prin virgulă) *", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_ingr.pack(anchor="w", pady=(0, 2))
        entry_ingr = ctk.CTkEntry(content, placeholder_text="ex: paste, ton, rosii cherry, usturoi, patrunjel", height=38)
        entry_ingr.pack(fill="x", pady=(0, 10))

        row_meta = ctk.CTkFrame(content, fg_color="transparent")
        row_meta.pack(fill="x", pady=(0, 10))
        row_meta.grid_columnconfigure((0, 1), weight=1)

        lbl_time = ctk.CTkLabel(row_meta, text="Timp gătire (min)", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_time.grid(row=0, column=0, padx=(0, 6), sticky="w")
        entry_time = ctk.CTkEntry(row_meta, placeholder_text="ex: 15", height=38)
        entry_time.grid(row=1, column=0, padx=(0, 6), sticky="ew")

        lbl_cals = ctk.CTkLabel(row_meta, text="Calorii (per porție)", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_cals.grid(row=0, column=1, padx=(6, 0), sticky="w")
        entry_cals = ctk.CTkEntry(row_meta, placeholder_text="ex: 420", height=38)
        entry_cals.grid(row=1, column=1, padx=(6, 0), sticky="ew")

        lbl_app = ctk.CTkLabel(content, text="Aparat principal folosit", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_app.pack(anchor="w", pady=(0, 2))
        opt_app = ctk.CTkOptionMenu(
            content,
            values=["Plită", "Cuptor", "Airfryer", "Cuptor cu microunde", "Multicooker", "Grill electric", "Fără gătire"],
            height=38,
            font=ctk.CTkFont(size=13)
        )
        opt_app.set("Plită")
        opt_app.pack(fill="x", pady=(0, 10))

        lbl_instr = ctk.CTkLabel(content, text="Instrucțiuni de preparare *", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_instr.pack(anchor="w", pady=(0, 2))
        box_instr = ctk.CTkTextbox(content, height=120, font=ctk.CTkFont(size=13), wrap="word")
        box_instr.pack(fill="x", pady=(0, 10))

        status_lbl = ctk.CTkLabel(content, text="", font=ctk.CTkFont(size=12), text_color="#e74c3c")
        status_lbl.pack(pady=(0, 8))

        def save_recipe_action():
            title_val = entry_title.get().strip()
            ingr_val = entry_ingr.get().strip()
            instr_val = box_instr.get("1.0", "end").strip()
            time_val = entry_time.get().strip()
            cals_val = entry_cals.get().strip()
            app_val = opt_app.get()

            if not title_val or not ingr_val or not instr_val:
                status_lbl.configure(text="Titlul, ingredientele și instrucțiunile sunt obligatorii.")
                return

            try:
                time_num = int(time_val) if time_val else 0
            except ValueError:
                status_lbl.configure(text="Timpul trebuie să fie un număr întreg.")
                return

            try:
                cals_num = int(cals_val) if cals_val else 0
            except ValueError:
                status_lbl.configure(text="Caloriile trebuie să fie un număr întreg.")
                return

            add_custom_recipe(
                self.user["id"],
                title_val,
                ingr_val,
                instr_val,
                time_num,
                cals_num,
                app_val
            )
            modal.destroy()
            self.load_recipes()

        btn_save = ctk.CTkButton(
            content,
            text="Salvează Rețeta",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#27ae60",
            hover_color="#219653",
            command=save_recipe_action
        )
        btn_save.pack(fill="x", pady=(0, 8))

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Organizator de retete")
        self.geometry("800x600")
        self.minsize(800, 600)
        self.current_user = None
        self.current_frame = None
        self.show_auth()

    def switch_frame(self, frame_class, *args, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self, *args, **kwargs)
        self.current_frame.pack(fill="both", expand=True)

    def show_auth(self):
        self.current_user = None
        self.switch_frame(AuthFrame)

    def show_questionnaire(self, user):
        self.current_user = user
        self.switch_frame(QuestionnaireFrame, user=user)

    def show_dashboard(self, user):
        self.current_user = user
        self.switch_frame(DashboardFrame, user=user)

if __name__ == "__main__":
    app = App()
    app.mainloop()

    #git test fix
