import streamlit as st
import pandas as pd
import smtplib
import csv
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import os
import json
from PIL import Image
from supabase import create_client, Client
import matplotlib.pyplot as plt


# Konfiguracja strony
st.set_page_config(page_title="F1 Ankietka", page_icon="🏎️", layout="wide")

# Inicjalizacja klienta Supabase
try:
    supabase_url = st.secrets["supabase"]["url"]
    supabase_key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(supabase_url, supabase_key)
    supabase_connected = True
except Exception as e:
    st.warning(f"Nie udało się połączyć z Supabase: {e}")
    supabase_connected = False

# Funkcja do ładowania niestandardowego opisu
def load_app_description():
    try:
        # Próba załadowania opisu z secrets
        if "app_description" in st.secrets:
            return st.secrets["app_description"]
        
        # Alternatywnie, sprawdzenie czy istnieje plik app_settings.json
        if os.path.exists("app_settings.json"):
            with open("app_settings.json", "r", encoding="utf-8") as file:
                settings = json.load(file)
                return settings.get("app_description", "### Typuj wyniki wyścigów Formuły 1 i zdobywaj punkty!")
    except Exception as e:
        st.warning(f"Nie udało się załadować niestandardowego opisu: {e}")
    
    # Domyślny opis, jeśli nie można załadować
    return "### Typuj wyniki wyścigów Formuły 1 i zdobywaj punkty!"

# Tytuł i opis
st.title("🏁 F1 Ankietka 🏎️")
app_description = load_app_description()
st.markdown(app_description)

# Funkcja do pobierania aktywnych wyścigów z Supabase
def get_active_races():
    if not supabase_connected:
        return []
    
    try:
        response = supabase.table('races').select('*').eq('is_active', True).execute()
        return response.data
    except Exception as e:
        st.error(f"Błąd podczas pobierania wyścigów: {e}")
        return []

# Funkcja do zapisywania odpowiedzi do Supabase
def save_submission(predictions, user_name, race_id):
    if not supabase_connected:
        st.error("Brak połączenia z bazą danych Supabase")
        return False
    
    try:
        # Przygotuj dane do zapisania
        extra_answers = {}
        for key, value in predictions.items():
            if key.startswith("Pytanie dodatkowe"):
                extra_answers[key] = value
        
        # Zapisz główne dane odpowiedzi
        submission_data = {
            "user_name": user_name,
            "podium_1": predictions["Podium 1. miejsce"],
            "podium_2": predictions["Podium 2. miejsce"],
            "podium_3": predictions["Podium 3. miejsce"],
            "time_diff": predictions["Różnica czasowa"],
            "driver_of_day": predictions["Kierowca dnia"],
            "safety_car": predictions["Safety Car"] == "Tak",
            "red_flag": predictions["Czerwona flaga"] == "Tak",
            "classified_drivers": predictions["Liczba sklasyfikowanych kierowców"],
            "teams_with_points": predictions["Liczba zespołów z punktami"],
            "extra_answers": extra_answers,
            "race_id": race_id
        }
        
        # Dodaj rekord do tabeli submissions
        response = supabase.table('submissions').insert(submission_data).execute()
        
        # Sprawdź czy operacja się powiodła
        if len(response.data) > 0:
            return True
        else:
            st.error("Nie udało się zapisać odpowiedzi")
            return False
            
    except Exception as e:
        st.error(f"Błąd podczas zapisywania odpowiedzi: {e}")
        return False

# Funkcja ładująca pytania
def load_questions(race_id=None):
    # Jeśli mamy połączenie z Supabase i podane ID wyścigu
    if supabase_connected and race_id:
        try:
            response = supabase.table('custom_questions').select('*').eq('race_id', race_id).execute()
            
            if len(response.data) > 0:
                return [{
                    "question": item["question"],
                    "options": item["options"]
                } for item in response.data]
        except Exception as e:
            st.warning(f"Nie udało się załadować pytań z Supabase: {e}")
    
    # Jeśli nie możemy pobrać z Supabase, próbujemy z innych źródeł
    try:
        # Próba załadowania pytań z secrets
        if "custom_questions" in st.secrets:
            return st.secrets["custom_questions"]
        
        # Alternatywnie, sprawdzenie czy istnieje plik questions.json
        if os.path.exists("questions.json"):
            with open("questions.json", "r", encoding="utf-8") as file:
                return json.load(file)
    except Exception as e:
        st.warning(f"Nie udało się załadować niestandardowych pytań: {e}")
    
    # Domyślne pytania, jeśli nie można załadować
    return [
        {
            "question": "Czy będzie najszybsze okrążenie z punktem bonusowym dla kierowcy w TOP10?",
            "options": ["Tak", "Nie"]
        },
        {
            "question": "Który zespół zdobędzie więcej punktów?",
            "options": ["Red Bull", "Ferrari", "Mercedes", "McLaren", "Inny"]
        }
    ]

# Funkcja do generowania pliku CSV z odpowiedziami
def generate_csv(predictions, user_name):
    # Utwórz bufor pamięci dla pliku CSV
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    
    # Nagłówki
    csv_writer.writerow(['Kategoria', 'Odpowiedź'])
    
    # Dodaj imię użytkownika
    csv_writer.writerow(['Imię', user_name])
    
    # Dodaj datę i czas
    csv_writer.writerow(['Data wysłania', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    
    # Dodaj pusty wiersz
    csv_writer.writerow([])
    
    # Dodaj wszystkie przewidywania
    for key, value in predictions.items():
        csv_writer.writerow([key, value])
    
    # Zwróć zawartość bufora jako string
    return csv_buffer.getvalue()

# Funkcja wysyłająca email potwierdzający
def send_email_confirmation(predictions, user_name):
    try:
        # Konfiguracja emaila - te dane należy zastąpić własnymi
        email_sender = st.secrets.email.sender
        email_password = st.secrets.email.password
        admin_email = st.secrets.email.sender
        
        # Przygotowanie wiadomości
        subject = f"[F1 Quiz App] Potwierdzenie typów od {user_name}"
        
        # Formatowanie przewidywań do emaila
        email_body = f"""
        Potwierdzenie typów F1 od {user_name} 
        Data wysłania: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Przewidywania:
        """
        
        for key, value in predictions.items():
            email_body += f"\n{key}: {value}"
        
        # Konfiguracja wiadomości
        msg = MIMEMultipart()
        msg['From'] = email_sender
        msg['To'] = email_sender
        msg['Subject'] = subject
        
        # Dodaj tekst wiadomości
        msg.attach(MIMEText(email_body, 'plain'))
        
        # Generuj i załącz plik CSV
        csv_content = generate_csv(predictions, user_name)
        csv_attachment = MIMEApplication(csv_content.encode('utf-8'))
        csv_attachment.add_header('Content-Disposition', 'attachment', 
                                  filename=f'f1_typy_{user_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        msg.attach(csv_attachment)
        
        # Wysłanie emaila
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_sender, email_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        st.error(f"Błąd podczas wysyłania emaila: {e}")
        return False

# Funkcja do generowania listy kierowców F1
def get_f1_drivers():
    # Aktualna lista kierowców F1 2025 zgodnie z dostarczonym obrazem
    teams_drivers = {
        'Red Bull Racing': ['Max Verstappen', 'Liam Lawson'],
        'Ferrari': ['Charles Leclerc', 'Lewis Hamilton'],
        'Mercedes': ['Andrea Kimi Antonelli', 'George Russell'],
        'McLaren': ['Lando Norris', 'Oscar Piastri'],
        'Aston Martin': ['Fernando Alonso', 'Lance Stroll'],
        'Alpine': ['Jack Doohan', 'Pierre Gasly'],
        'Williams': ['Alexander Albon', 'Carlos Sainz Jr.'],
        'Racing Bulls': ['Isack Hadjar', 'Yuki Tsunoda'],
        'Kick Sauber': ['Gabriel Bortoleto', 'Nico Hülkenberg'],
        'Haas': ['Esteban Ocon', 'Oliver Bearman']
    }
    
    drivers = []
    for team, team_drivers in teams_drivers.items():
        for driver in team_drivers:
            drivers.append(driver)
    
    return drivers

# Pobranie aktywnych wyścigów
active_races = get_active_races()

# Wybór wyścigu (jeśli są dostępne)
selected_race = None
race_id = None

if active_races:
    if len(active_races) > 1:
        st.write("### Wybierz wyścig do typowania")
        race_options = [f"{race['race_name']} ({race['race_date']})" for race in active_races]
        race_ids = [race['id'] for race in active_races]
        
        selected_race_index = st.selectbox(
            "Dostępne wyścigi", 
            range(len(active_races)), 
            format_func=lambda x: race_options[x]
        )
        
        selected_race = active_races[selected_race_index]
        race_id = race_ids[selected_race_index]
        
        st.success(f"Wybrano wyścig: {selected_race['race_name']}")
    else:
        selected_race = active_races[0]
        race_id = selected_race['id']
        st.info(f"Aktualny wyścig: {selected_race['race_name']} ({selected_race['race_date']})")
    
    # Sprawdź termin nadsyłania typów, jeśli jest dostępny
    if 'submission_deadline' in selected_race:
        deadline_str = selected_race['submission_deadline']
        try:
            # Konwersja stringa ISO do obiektu datetime
            if 'Z' in deadline_str:
                deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            else:
                deadline = datetime.fromisoformat(deadline_str)
                
            now = datetime.now(deadline.tzinfo if deadline.tzinfo else None)
            
            if now > deadline:
                st.error(f"Termin nadsyłania typów upłynął! Deadline był: {deadline.strftime('%Y-%m-%d %H:%M')}")
            else:
                st.success(f"Możesz nadsyłać typy do: {deadline.strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            st.warning(f"Nie udało się sprawdzić terminu: {e}")

# Ładujemy dodatkowe pytania dla wybranego wyścigu (jeśli istnieje)
custom_questions = load_questions(race_id)

# Inicjalizacja stanu sesji dla logowania administratora
if 'show_admin' not in st.session_state:
    st.session_state.show_admin = False

# Inicjalizacja stanu sesji dla pokazywania formularza logowania administratora
if 'show_admin_login' not in st.session_state:
    st.session_state.show_admin_login = False

# Funkcja do pokazywania/ukrywania formularza logowania
def toggle_admin_login():
    st.session_state.show_admin_login = not st.session_state.show_admin_login

# Funkcja do wylogowania z panelu admina
def logout_admin():
    st.session_state.show_admin = False
    st.session_state.show_admin_login = False
    st.rerun()

# Formularz główny
with st.form("f1_prediction_form"):
    # Dane osobowe
    st.subheader("Twoje dane")
    
    user_names = ["Agatka", "Iza", "Kinga","Paweł","Piotrek","Seweryn"]

    
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.selectbox("Imię",user_names)
   
    st.markdown("---")
    
    # Lista kierowców
    drivers = get_f1_drivers()
    # Sekcja 1: Podium wyścigu
    st.subheader("1. Podium wyścigu (1 punkt za każdego kierowcę, +1 za całe podium)")
    col1, col2, col3 = st.columns(3)
    with col1:
        podium_1 = st.selectbox("Pierwsze miejsce", drivers)
    with col2:
        # Filtrujemy listę, aby usunąć już wybranego kierowcę
        podium_2_options = [d for d in drivers if d != podium_1]
        podium_2 = st.selectbox("Drugie miejsce", podium_2_options)
    with col3:
        # Filtrujemy listę, aby usunąć już wybranych kierowców
        podium_3_options = [d for d in drivers if d not in [podium_1, podium_2]]
        podium_3 = st.selectbox("Trzecie miejsce", podium_3_options)
    
    # Sekcja 2: Różnica czasowa
    st.subheader("2. Różnica w sekundach między 1. a 2. miejscem (1 punkt)")
    time_diff = st.radio(
        "Wybierz przedział",
        ["Mniej niż 2 sekundy", "2.001-5 sekund", "5.001-10 sekund", 
         "10.001-20 sekund", "Więcej niż 20 sekund"]
    )
    
    # Sekcja 3: Driver of The Day
    st.subheader("3. Kierowca dnia (1 punkt)")
    dotd = st.selectbox("Driver of The Day", drivers)
    
    # Sekcja 4: Safety Car
    st.subheader("4. Safety Car (1 punkt)")
    safety_car = st.radio(
        "Czy podczas wyścigu wyjedzie Safety Car?",
        ["Tak", "Nie"]
    )
    
    # Sekcja 5: Czerwona flaga
    st.subheader("5. Czerwona flaga (1 punkt)")
    red_flag = st.radio(
        "Czy podczas wyścigu będzie czerwona flaga?",
        ["Tak", "Nie"]
    )
    
    # Sekcja 6: Liczba sklasyfikowanych kierowców
    st.subheader("6. Ilu kierowców zostanie sklasyfikowanych? (1 punkt)")
    classified_drivers = st.radio(
        "Wybierz przedział",
        ["20", "19-18", "17-16", "15-14", "Mniej niż 14"]
    )
    
    # Sekcja 7: Liczba zespołów z punktami
    st.subheader("7. Ile zespołów zdobędzie punkty? (1 punkt)")
    teams_with_points = st.select_slider(
        "Wybierz liczbę zespołów",
        options=[5, 6, 7, 8, 9, 10]
    )
    
    # Sekcja 8: Dodatkowe pytania (zmienne)
    st.subheader("8. Dodatkowe pytania (1 punkt za każde)")
    
    # Dynamiczne dodatkowe pytania
    extra_answers = {}
    for i, question_data in enumerate(custom_questions):
        question_key = f"Pytanie dodatkowe {i+1}"
        extra_answers[question_key] = st.radio(
            question_data["question"],
            options=question_data["options"]
        )
    
    # Przycisk wysłania formularza
    submitted = st.form_submit_button("Wyślij typy")
    
    if submitted:
        if not user_name:
            st.error("Wypełnij imię!")
        elif not race_id and supabase_connected:
            st.error("Brak aktywnego wyścigu do typowania!")
        else:
            # Zbieramy wszystkie przewidywania
            predictions = {
                "Podium 1. miejsce": podium_1,
                "Podium 2. miejsce": podium_2,
                "Podium 3. miejsce": podium_3,
                "Różnica czasowa": time_diff,
                "Kierowca dnia": dotd,
                "Safety Car": safety_car,
                "Czerwona flaga": red_flag,
                "Liczba sklasyfikowanych kierowców": classified_drivers,
                "Liczba zespołów z punktami": teams_with_points,
            }
            
            # Dodajemy odpowiedzi na pytania dodatkowe
            predictions.update(extra_answers)
            
            # Zapisujemy dane - albo do Supabase, albo wysyłamy email
            success = False
            
            if supabase_connected and race_id:
                # Zapisz do Supabase
                success = save_submission(predictions, user_name, race_id)
            else:
                # Użyj metody wysyłania emaila jako fallback
                success = send_email_confirmation(predictions, user_name)
            
            if success:
                st.success("Chill, koniec męczarni! Twoje typy zostały zapisane! Powodzenia! 🏆")
                
                # Pokazujemy podsumowanie
                st.subheader("Podsumowanie Twoich typów:")
                
                # Tworzymy tabelę z przewidywaniami
                df = pd.DataFrame(list(predictions.items()), columns=["Kategoria", "Twój typ"])
                st.table(df)
                
                # Wyświetl obrazek, jeśli istnieje
                try:
                    img = Image.open("fernando.png")
                    st.image(img, caption="Powodzenia!", use_container_width=True)
                except Exception as e:
                    st.warning(f"Nie udało się wyświetlić obrazka: {e}")
            else:
                st.error("Wystąpił problem podczas zapisywania formularza. Spróbuj ponownie.")

# Dodanie instrukcji punktacji
with st.expander("Zasady punktacji"):
    st.markdown("""
    ### Zasady przyznawania punktów:
    1. **Podium** - 1 punkt za każdego prawidłowo wytypowanego kierowcę + 1 dodatkowy punkt za idealne podium (łącznie max. 4 punkty)
    2. **Różnica czasowa** - 1 punkt za prawidłowy przedział
    3. **Kierowca dnia** - 1 punkt za trafienie
    4. **Safety Car** - 1 punkt za prawidłową odpowiedź
    5. **Czerwona flaga** - 1 punkt za prawidłową odpowiedź
    6. **Liczba sklasyfikowanych kierowców** - 1 punkt za prawidłowy przedział
    7. **Liczba zespołów z punktami** - 1 punkt za trafienie
    8. **Pytania dodatkowe** - po 1 punkcie za każdą prawidłową odpowiedź
    
    **Maksymalna liczba punktów do zdobycia: 11**
    """)

# Zmienne do przechowywania ustawień aplikacji
if 'app_settings' not in st.session_state:
    st.session_state.app_settings = {
        "app_description": "### Typuj wyniki wyścigów Formuły 1 i zdobywaj punkty!"
    }

# Funkcja do zapisywania ustawień aplikacji
def save_app_settings():
    try:
        # W praktycznej implementacji tutaj zapisujemy do pliku lub bazy danych
        with open("app_settings.json", "w", encoding="utf-8") as file:
            json.dump(st.session_state.app_settings, file, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.sidebar.error(f"Błąd podczas zapisywania ustawień: {e}")
        return False

# Ukryty przycisk do pokazania formularza logowania
# Umieszczamy go w stopce, gdzie jest mniej zauważalny
st.markdown("---")
cols = st.columns([10, 1])
with cols[1]:
    if st.button("👤", help="Panel administratora", key="admin_button"):
        toggle_admin_login()


# Panel logowania administratora - pokazywany tylko po kliknięciu ukrytego przycisku
if st.session_state.show_admin_login and not st.session_state.show_admin:
    with st.sidebar:
        st.sidebar.header("Panel administratora")
        admin_password = st.text_input("Hasło administratora", type="password")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if st.button("Anuluj"):
                st.session_state.show_admin_login = False
                st.rerun()
        with col2:
            if st.button("Zaloguj"):
                # Sprawdź hasło z secrets
                try:
                    if admin_password == st.secrets.admin.password:
                        st.session_state.show_admin = True
                        #st.rerun()
                    else:
                        st.error("Nieprawidłowe hasło!")
                except:
                    # Awaryjne hasło jeśli secrets nie jest skonfigurowane
                    if admin_password == "admin123":
                        st.session_state.show_admin = True
                        st.rerun()
                    else:
                        st.error("Nieprawidłowe hasło!")

# Panel administratora (gdy zalogowany)
if st.session_state.show_admin:
    with st.sidebar:
        st.header("Panel Administratora")
        
        # Przycisk wylogowania na górze panelu
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("Wyloguj", key="logout_button"):
                logout_admin()
        
        # Zakładki panelu administratora
        admin_tabs = st.tabs(["Ustawienia", "Wyścigi", "Pytania", "Wyniki", "Statystyki"])
        
        # Zakładka z ustawieniami aplikacji
        with admin_tabs[0]:
            st.subheader("Ogólne ustawienia aplikacji")
            
            # Edycja opisu aplikacji
            app_description_input = st.text_area(
                "Opis aplikacji (tekst pod tytułem)",
                value=app_description.replace("### ", ""),
                help="Zmień główny opis aplikacji wyświetlany pod tytułem."
            )
            
            # Aktualizacja opisu aplikacji w sesji
            st.session_state.app_settings["app_description"] = f"### {app_description_input}"
            
            # Przyciski do zapisywania ustawień
            if st.button("Zapisz ustawienia ogólne"):
                # Zapisz do bazy danych jeśli połączenie z Supabase jest aktywne
                if supabase_connected:
                    try:
                        # Sprawdź czy tabela app_settings istnieje i dodaj/zaktualizuj rekord
                        settings_data = {"app_description": f"### {app_description_input}"}
                        
                        # Próba aktualizacji, jeśli nie istnieje, to dodanie nowego rekordu
                        response = supabase.table('app_settings').upsert(settings_data).execute()
                        
                        if len(response.data) > 0:
                            st.success("Ustawienia zostały zapisane w bazie danych!")
                        else:
                            # Fallback do zapisywania w pliku
                            if save_app_settings():
                                st.success("Ustawienia zostały zapisane w pliku!")
                    except Exception as e:
                        st.error(f"Błąd podczas zapisywania ustawień w bazie: {e}")
                        # Próba zapisania do pliku jako fallback
                        if save_app_settings():
                            st.success("Ustawienia zostały zapisane w pliku!")
                else:
                    # Zapisz do pliku jeśli brak połączenia z Supabase
                    if save_app_settings():
                        st.success("Ustawienia zostały zapisane w pliku!")
                
                st.rerun()  # Odświeżenie aplikacji, aby pokazać zmiany
        
        # Zakładka zarządzania wyścigami
        with admin_tabs[1]:
            st.subheader("Zarządzanie wyścigami")
            
            if not supabase_connected:
                st.error("Brak połączenia z bazą danych. Zarządzanie wyścigami wymaga połączenia z Supabase.")
            else:
                # Formularz dodawania nowego wyścigu
                with st.form("add_race_form"):
                    st.write("#### Dodaj nowy wyścig")
                    race_name = st.text_input("Nazwa wyścigu (np. GP Hiszpanii)")
                    race_date = st.date_input("Data wyścigu")
                    submission_date = st.date_input("Data terminu nadsyłania typów")
                    submission_time = st.time_input("Czas terminu nadsyłania typów")

                    # Combine date and time into a datetime object
                    submission_deadline = datetime.combine(submission_date, submission_time)
                                        
                    submit_race = st.form_submit_button("Dodaj wyścig")
                    
                    if submit_race:
                        try:
                            race_data = {
                                "race_name": race_name,
                                "race_date": race_date.isoformat(),
                                "submission_deadline": submission_deadline.isoformat(),
                                "is_active": True
                            }
                            
                            response = supabase.table('races').insert(race_data).execute()
                            
                            if len(response.data) > 0:
                                st.success(f"Dodano wyścig: {race_name}")
                                st.rerun()
                            else:
                                st.error("Nie udało się dodać wyścigu")
                        except Exception as e:
                            st.error(f"Błąd: {e}")
                
                # Lista aktywnych wyścigów
                st.subheader("Aktywne wyścigi")
                active_races = get_active_races()
                
                if active_races:
                    for race in active_races:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{race['race_name']}** - {race['race_date']}")
                            st.write(f"Termin typowania: {race['submission_deadline']}")
                        with col2:
                            if st.button("Deaktywuj", key=f"deactivate_{race['id']}"):
                                supabase.table('races').update({"is_active": False}).eq("id", race['id']).execute()
                                st.success(f"Deaktywowano wyścig: {race['race_name']}")
                                st.rerun()
                else:
                    st.info("Brak aktywnych wyścigów.")
                
                # Lista wszystkich wyścigów (w tym nieaktywnych)
                st.subheader("Wszystkie wyścigi")
                try:
                    all_races_response = supabase.table('races').select('*').order('race_date', desc=True).execute()
                    all_races = all_races_response.data
                    
                    if all_races:
                        races_df = pd.DataFrame(all_races)
                        races_df['status'] = races_df['is_active'].apply(lambda x: "Aktywny" if x else "Nieaktywny")
                        races_df = races_df[['race_name', 'race_date', 'submission_deadline', 'status']]
                        races_df.columns = ['Nazwa wyścigu', 'Data wyścigu', 'Termin typowania', 'Status']
                        st.dataframe(races_df)
                    else:
                        st.info("Brak wyścigów w bazie.")
                except Exception as e:
                    st.error(f"Błąd podczas pobierania listy wyścigów: {e}")
                    
# Zakładka zarządzania pytaniami dodatkowymi
        with admin_tabs[2]:
            st.subheader("Zarządzanie pytaniami dodatkowymi")
            
            if not supabase_connected:
                st.error("Brak połączenia z bazą danych. Zarządzanie pytaniami wymaga połączenia z Supabase.")
            else:
                # Wybór wyścigu do edycji pytań
                races_response = supabase.table('races').select('*').execute()
                races = races_response.data
                
                if races:
                    race_options = [f"{race['race_name']} ({race['race_date']})" for race in races]
                    race_ids = [race['id'] for race in races]
                    
                    selected_race_index = st.selectbox(
                        "Wybierz wyścig do edycji pytań", 
                        range(len(races)), 
                        format_func=lambda x: race_options[x],
                        key="questions_race_select"
                    )
                    
                    selected_race_id = race_ids[selected_race_index]
                    
                    # Pobranie aktualnych pytań dla wybranego wyścigu
                    questions_response = supabase.table('custom_questions').select('*').eq('race_id', selected_race_id).execute()
                    race_questions = questions_response.data
                    
                    if not race_questions:
                        st.info(f"Brak pytań dla wyścigu {race_options[selected_race_index]}. Dodaj nowe pytania.")
                        
                        # Formularze do dodawania nowych pytań
                        with st.form("add_question_form"):
                            st.write("#### Dodaj nowe pytanie")
                            question_text = st.text_input("Treść pytania")
                            options_text = st.text_area("Opcje odpowiedzi (każda w nowej linii)")
                            
                            submit_question = st.form_submit_button("Dodaj pytanie")
                            
                            if submit_question:
                                if not question_text or not options_text:
                                    st.error("Treść pytania i opcje odpowiedzi są wymagane.")
                                else:
                                    try:
                                        options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
                                        
                                        if len(options) < 2:
                                            st.error("Dodaj co najmniej dwie opcje odpowiedzi.")
                                        else:
                                            question_data = {
                                                "question": question_text,
                                                "options": options,
                                                "race_id": selected_race_id
                                            }
                                            
                                            response = supabase.table('custom_questions').insert(question_data).execute()
                                            
                                            if len(response.data) > 0:
                                                st.success(f"Dodano pytanie dla wyścigu {race_options[selected_race_index]}")
                                                st.rerun()
                                            else:
                                                st.error("Nie udało się dodać pytania")
                                    except Exception as e:
                                        st.error(f"Błąd: {e}")
                    else:
                        # Edycja istniejących pytań
                        st.write(f"#### Edycja pytań dla wyścigu {race_options[selected_race_index]}")
                        
                        for i, question in enumerate(race_questions):
                            with st.expander(f"Pytanie {i+1}: {question['question'][:50]}..."):
                                with st.form(f"edit_question_{question['id']}"):
                                    q_text = st.text_input("Treść pytania", value=question['question'], key=f"q_text_{question['id']}")
                                    
                                    options_str = "\n".join(question['options']) if isinstance(question['options'], list) else "\n".join(question['options'].keys())
                                    q_options = st.text_area("Opcje odpowiedzi (każda w nowej linii)", value=options_str, key=f"q_options_{question['id']}")
                                    
                                    col1, col2 = st.columns([1, 1])
                                    with col1:
                                        update_btn = st.form_submit_button("Aktualizuj")
                                    with col2:
                                        delete_btn = st.form_submit_button("Usuń", type="primary")
                                    
                                    if update_btn:
                                        try:
                                            options = [opt.strip() for opt in q_options.split('\n') if opt.strip()]
                                            
                                            if len(options) < 2:
                                                st.error("Dodaj co najmniej dwie opcje odpowiedzi.")
                                            else:
                                                question_data = {
                                                    "question": q_text,
                                                    "options": options
                                                }
                                                
                                                response = supabase.table('custom_questions').update(question_data).eq('id', question['id']).execute()
                                                
                                                if len(response.data) > 0:
                                                    st.success("Pytanie zostało zaktualizowane")
                                                    st.rerun()
                                                else:
                                                    st.error("Nie udało się zaktualizować pytania")
                                        except Exception as e:
                                            st.error(f"Błąd podczas aktualizacji: {e}")
                                    
                                    if delete_btn:
                                        try:
                                            response = supabase.table('custom_questions').delete().eq('id', question['id']).execute()
                                            
                                            if len(response.data) > 0:
                                                st.success("Pytanie zostało usunięte")
                                                st.rerun()
                                            else:
                                                st.error("Nie udało się usunąć pytania")
                                        except Exception as e:
                                            st.error(f"Błąd podczas usuwania: {e}")
                        
                        # Formularz dodawania nowego pytania dla istniejącego wyścigu
                        with st.form("add_new_question_form"):
                            st.write("#### Dodaj nowe pytanie")
                            new_question_text = st.text_input("Treść pytania", key="new_q_text")
                            new_options_text = st.text_area("Opcje odpowiedzi (każda w nowej linii)", key="new_q_options")
                            
                            submit_new_question = st.form_submit_button("Dodaj pytanie")
                            
                            if submit_new_question:
                                if not new_question_text or not new_options_text:
                                    st.error("Treść pytania i opcje odpowiedzi są wymagane.")
                                else:
                                    try:
                                        options = [opt.strip() for opt in new_options_text.split('\n') if opt.strip()]
                                        
                                        if len(options) < 2:
                                            st.error("Dodaj co najmniej dwie opcje odpowiedzi.")
                                        else:
                                            question_data = {
                                                "question": new_question_text,
                                                "options": options,
                                                "race_id": selected_race_id
                                            }
                                            
                                            response = supabase.table('custom_questions').insert(question_data).execute()
                                            
                                            if len(response.data) > 0:
                                                st.success(f"Dodano nowe pytanie dla wyścigu {race_options[selected_race_index]}")
                                                st.rerun()
                                            else:
                                                st.error("Nie udało się dodać pytania")
                                    except Exception as e:
                                        st.error(f"Błąd: {e}")
                else:
                    st.info("Brak wyścigów. Najpierw dodaj wyścig w zakładce 'Wyścigi'.")
                    
        # Zakładka zarządzania wynikami
        with admin_tabs[3]:
            st.subheader("Wprowadzanie wyników wyścigów")
            
            if not supabase_connected:
                st.error("Brak połączenia z bazą danych. Wprowadzanie wyników wymaga połączenia z Supabase.")
            else:
                # Wybór wyścigu do wprowadzenia wyników
                races_response = supabase.table('races').select('*').execute()
                races = races_response.data
                
                if races:
                    race_options = [f"{race['race_name']} ({race['race_date']})" for race in races]
                    race_ids = [race['id'] for race in races]
                    
                    selected_race_index = st.selectbox(
                        "Wybierz wyścig do wprowadzenia wyników", 
                        range(len(races)), 
                        format_func=lambda x: race_options[x],
                        key="results_race_select"
                    )
                    
                    selected_race_id = race_ids[selected_race_index]
                    
                    # Sprawdź czy już wprowadzono wyniki
                    results_response = supabase.table('results').select('*').eq('race_id', selected_race_id).execute()
                    existing_results = results_response.data
                    
                    # Lista kierowców
                    drivers = get_f1_drivers()
                    
                    # Pobranie pytań dodatkowych dla tego wyścigu
                    questions_response = supabase.table('custom_questions').select('*').eq('race_id', selected_race_id).execute()
                    race_questions = questions_response.data
                    
                    if existing_results:
                        st.info(f"Wyniki dla wyścigu {race_options[selected_race_index]} zostały już wprowadzone. Możesz je edytować poniżej.")
                        
                        with st.form("edit_results_form"):
                            st.write("#### Edycja wyników wyścigu")
                            
                            result = existing_results[0]
                            
                            # Podium
                            st.subheader("Podium wyścigu")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                podium_1 = st.selectbox("Pierwsze miejsce", drivers, index=drivers.index(result['podium_1']) if result['podium_1'] in drivers else 0)
                            with col2:
                                podium_2_options = [d for d in drivers if d != podium_1]
                                podium_2 = st.selectbox("Drugie miejsce", podium_2_options, index=podium_2_options.index(result['podium_2']) if result['podium_2'] in podium_2_options else 0)
                            with col3:
                                podium_3_options = [d for d in drivers if d not in [podium_1, podium_2]]
                                podium_3 = st.selectbox("Trzecie miejsce", podium_3_options, index=podium_3_options.index(result['podium_3']) if result['podium_3'] in podium_3_options else 0)
                            
                            # Pozostałe wyniki
                            time_diff = st.radio(
                                "Różnica czasowa między 1. a 2. miejscem",
                                ["Mniej niż 2 sekundy", "2.001-5 sekund", "5.001-10 sekund", 
                                "10.001-20 sekund", "Więcej niż 20 sekund"],
                                index=["Mniej niż 2 sekundy", "2.001-5 sekund", "5.001-10 sekund", 
                                "10.001-20 sekund", "Więcej niż 20 sekund"].index(result['time_diff'])
                            )
                            
                            dotd = st.selectbox("Kierowca dnia (DOTD)", drivers, index=drivers.index(result['driver_of_day']) if result['driver_of_day'] in drivers else 0)
                            
                            safety_car = st.radio(
                                "Wyjazd Safety Car",
                                ["Tak", "Nie"],
                                index=0 if result['safety_car'] else 1
                            )
                            
                            red_flag = st.radio(
                                "Czerwona flaga",
                                ["Tak", "Nie"],
                                index=0 if result['red_flag'] else 1
                            )
                            
                            classified_drivers = st.radio(
                                "Liczba sklasyfikowanych kierowców",
                                ["20", "19-18", "17-16", "15-14", "Mniej niż 14"],
                                index=["20", "19-18", "17-16", "15-14", "Mniej niż 14"].index(result['classified_drivers'])
                            )
                            
                            teams_with_points = st.select_slider(
                                "Liczba zespołów z punktami",
                                options=[5, 6, 7, 8, 9, 10],
                                value=result['teams_with_points']
                            )
                            
                            # Odpowiedzi na pytania dodatkowe
                            extra_answers = {}
                            if race_questions:
                                st.subheader("Odpowiedzi na pytania dodatkowe")
                                
                                for i, question in enumerate(race_questions):
                                    question_key = f"Pytanie dodatkowe {i+1}"
                                    
                                    # Pobierz poprzednią odpowiedź, jeśli istnieje
                                    previous_answer = None
                                    if 'extra_answers' in result and question_key in result['extra_answers']:
                                        previous_answer = result['extra_answers'][question_key]
                                    
                                    options = question['options']
                                    default_index = options.index(previous_answer) if previous_answer in options else 0
                                    
                                    extra_answers[question_key] = st.radio(
                                        question['question'],
                                        options=options,
                                        index=default_index,
                                        key=f"result_q_{question['id']}"
                                    )
                            
                            update_results = st.form_submit_button("Zaktualizuj wyniki")
                            
                            if update_results:
                                try:
                                    results_data = {
                                        "podium_1": podium_1,
                                        "podium_2": podium_2,
                                        "podium_3": podium_3,
                                        "time_diff": time_diff,
                                        "driver_of_day": dotd,
                                        "safety_car": safety_car == "Tak",
                                        "red_flag": red_flag == "Tak",
                                        "classified_drivers": classified_drivers,
                                        "teams_with_points": teams_with_points,
                                        "extra_answers": extra_answers,
                                        "updated_at": datetime.now().isoformat()
                                    }
                                    
                                    response = supabase.table('results').update(results_data).eq('race_id', selected_race_id).execute()
                                    
                                    if len(response.data) > 0:
                                        st.success(f"Wyniki dla wyścigu {race_options[selected_race_index]} zostały zaktualizowane")
                                        st.rerun()
                                    else:
                                        st.error("Nie udało się zaktualizować wyników")
                                except Exception as e:
                                    st.error(f"Błąd podczas aktualizacji wyników: {e}")
                    else:
                        with st.form("add_results_form"):
                            st.write("#### Wprowadzanie wyników wyścigu")
                            
                            # Podium
                            st.subheader("Podium wyścigu")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                podium_1 = st.selectbox("Pierwsze miejsce", drivers)
                            with col2:
                                podium_2_options = [d for d in drivers if d != podium_1]
                                podium_2 = st.selectbox("Drugie miejsce", podium_2_options)
                            with col3:
                                podium_3_options = [d for d in drivers if d not in [podium_1, podium_2]]
                                podium_3 = st.selectbox("Trzecie miejsce", podium_3_options)
                            
                            # Pozostałe wyniki
                            time_diff = st.radio(
                                "Różnica czasowa między 1. a 2. miejscem",
                                ["Mniej niż 2 sekundy", "2.001-5 sekund", "5.001-10 sekund", 
                                "10.001-20 sekund", "Więcej niż 20 sekund"]
                            )
                            
                            dotd = st.selectbox("Kierowca dnia (DOTD)", drivers)
                            
                            safety_car = st.radio(
                                "Wyjazd Safety Car",
                                ["Tak", "Nie"]
                            )
                            
                            red_flag = st.radio(
                                "Czerwona flaga",
                                ["Tak", "Nie"]
                            )
                            
                            classified_drivers = st.radio(
                                "Liczba sklasyfikowanych kierowców",
                                ["20", "19-18", "17-16", "15-14", "Mniej niż 14"]
                            )
                            
                            teams_with_points = st.select_slider(
                                "Liczba zespołów z punktami",
                                options=[5, 6, 7, 8, 9, 10]
                            )
                            
                            # Odpowiedzi na pytania dodatkowe
                            extra_answers = {}
                            if race_questions:
                                st.subheader("Odpowiedzi na pytania dodatkowe")
                                
                                for i, question in enumerate(race_questions):
                                    question_key = f"Pytanie dodatkowe {i+1}"
                                    extra_answers[question_key] = st.radio(
                                        question['question'],
                                        options=question['options'],
                                        key=f"result_q_{question['id']}"
                                    )
                            
                            submit_results = st.form_submit_button("Zapisz wyniki")
                            
                            if submit_results:
                                try:
                                    results_data = {
                                        "race_id": selected_race_id,
                                        "podium_1": podium_1,
                                        "podium_2": podium_2,
                                        "podium_3": podium_3,
                                        "time_diff": time_diff,
                                        "driver_of_day": dotd,
                                        "safety_car": safety_car == "Tak",
                                        "red_flag": red_flag == "Tak",
                                        "classified_drivers": classified_drivers,
                                        "teams_with_points": teams_with_points,
                                        "extra_answers": extra_answers
                                    }
                                    
                                    response = supabase.table('results').insert(results_data).execute()
                                    
                                    if len(response.data) > 0:
                                        st.success(f"Wyniki dla wyścigu {race_options[selected_race_index]} zostały zapisane")
                                        
                                        # Automatyczne obliczanie punktów
                                        if st.button("Oblicz punkty użytkowników na podstawie dodanych wyników"):
                                            st.info("Funkcja w przygotowaniu...")
                                            
                                        st.rerun()
                                    else:
                                        st.error("Nie udało się zapisać wyników")
                                except Exception as e:
                                    st.error(f"Błąd podczas zapisywania wyników: {e}")
                else:
                    st.info("Brak wyścigów. Najpierw dodaj wyścig w zakładce 'Wyścigi'.")

        # Zakładka ze statystykami
        with admin_tabs[4]:
            st.subheader("Statystyki i odpowiedzi użytkowników")
            
            if not supabase_connected:
                st.error("Brak połączenia z bazą danych. Wyświetlanie statystyk wymaga połączenia z Supabase.")
            else:
                # Wybór wyścigu do analizy
                races_response = supabase.table('races').select('*').execute()
                races = races_response.data
                
                if races:
                    race_options = [f"{race['race_name']} ({race['race_date']})" for race in races]
                    race_ids = [race['id'] for race in races]
                    
                    selected_race_index = st.selectbox(
                        "Wybierz wyścig do analizy", 
                        range(len(races)), 
                        format_func=lambda x: race_options[x],
                        key="stats_race_select"
                    )
                    
                    selected_race_id = race_ids[selected_race_index]
                    
                    # Pobranie odpowiedzi użytkowników
                    submissions_response = supabase.table('submissions').select('*').eq('race_id', selected_race_id).execute()
                    submissions = submissions_response.data
                    
                    if submissions:
                        st.write(f"Liczba odpowiedzi: **{len(submissions)}**")
                        
                        # Pobranie wyników wyścigu
                        results_response = supabase.table('results').select('*').eq('race_id', selected_race_id).execute()
                        race_results = results_response.data
                        
                        if race_results:
                            result = race_results[0]
                            
                            # Obliczanie punktów użytkowników
                            st.subheader("Tabela wyników")
                            
                            user_points = []
                            
                            for submission in submissions:
                                points = 0
                                point_details = []
                                
                                # Podium - do 4 punktów
                                podium_points = 0
                                if submission['podium_1'] == result['podium_1']:
                                    podium_points += 1
                                    point_details.append("1 pkt za 1. miejsce")
                                
                                if submission['podium_2'] == result['podium_2']:
                                    podium_points += 1
                                    point_details.append("1 pkt za 2. miejsce")
                                
                                if submission['podium_3'] == result['podium_3']:
                                    podium_points += 1
                                    point_details.append("1 pkt za 3. miejsce")
                                
                                # Bonus za idealne podium
                                if podium_points == 3:
                                    podium_points += 1
                                    point_details.append("1 pkt bonus za pełne podium")
                                
                                points += podium_points
                                
                                # Pozostałe kategorie - po 1 punkcie
                                if submission['time_diff'] == result['time_diff']:
                                    points += 1
                                    point_details.append("1 pkt za różnicę czasową")
                                
                                if submission['driver_of_day'] == result['driver_of_day']:
                                    points += 1
                                    point_details.append("1 pkt za DOTD")
                                
                                if submission['safety_car'] == result['safety_car']:
                                    points += 1
                                    point_details.append("1 pkt za Safety Car")
                                
                                if submission['red_flag'] == result['red_flag']:
                                    points += 1
                                    point_details.append("1 pkt za czerwoną flagę")
                                
                                if submission['classified_drivers'] == result['classified_drivers']:
                                    points += 1
                                    point_details.append("1 pkt za liczbę kierowców")
                                
                                if submission['teams_with_points'] == result['teams_with_points']:
                                    points += 1
                                    point_details.append("1 pkt za zespoły z punktami")
                                
                                # Pytania dodatkowe
                                for key, value in submission['extra_answers'].items():
                                    if key in result['extra_answers'] and value == result['extra_answers'][key]:
                                        points += 1
                                        point_details.append(f"1 pkt za {key}")
                                
                                user_points.append({
                                    "user_name": submission['user_name'],
                                    "points": points,
                                    "point_details": ", ".join(point_details),
                                    "submission_date": submission['submission_date']
                                })
                            
                            # Tabela z punktami
                            points_df = pd.DataFrame(user_points)
                            points_df = points_df.sort_values('points', ascending=False)
                            
                            # Dodaj pozycję (miejsce)
                            points_df['pozycja'] = points_df['points'].rank(method='min', ascending=False).astype(int)
                            points_df = points_df[['pozycja', 'user_name', 'points', 'point_details', 'submission_date']]
                            points_df.columns = ['Pozycja', 'Imię', 'Punkty', 'Szczegóły punktacji', 'Data wysłania']
                            
                            st.dataframe(points_df)
                            
                            # Wykres z rozkładem punktów
                            st.subheader("Rozkład punktów")
                            
                            points_counts = points_df['Punkty'].value_counts().sort_index()
                            st.bar_chart(points_counts)
                            
                            # Statystyki typowań
                            st.subheader("Statystyki typowań")
                            
                            stats_tabs = st.tabs(["Podium", "Inne statystyki"])
                            
                            with stats_tabs[0]:
                                # Podium statystyki
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.write("#### 1. miejsce")
                                    p1_counts = {}
                                    for sub in submissions:
                                        driver = sub['podium_1']
                                        p1_counts[driver] = p1_counts.get(driver, 0) + 1
                                    
                                    p1_df = pd.DataFrame(list(p1_counts.items()), columns=['Kierowca', 'Liczba typowań'])
                                    p1_df = p1_df.sort_values('Liczba typowań', ascending=False)
                                    
                                    # Dodaj zaznaczenie dla faktycznego zwycięzcy
                                    p1_df['Faktyczny zwycięzca'] = p1_df['Kierowca'] == result['podium_1']
                                    
                                    st.dataframe(p1_df)
                                
                                with col2:
                                    st.write("#### 2. miejsce")
                                    p2_counts = {}
                                    for sub in submissions:
                                        driver = sub['podium_2']
                                        p2_counts[driver] = p2_counts.get(driver, 0) + 1
                                    
                                    p2_df = pd.DataFrame(list(p2_counts.items()), columns=['Kierowca', 'Liczba typowań'])
                                    p2_df = p2_df.sort_values('Liczba typowań', ascending=False)
                                    
                                    # Dodaj zaznaczenie dla faktycznego zwycięzcy
                                    p2_df['Faktyczny wynik'] = p2_df['Kierowca'] == result['podium_2']
                                    
                                    st.dataframe(p2_df)
                                
                                with col3:
                                    st.write("#### 3. miejsce")
                                    p3_counts = {}
                                    for sub in submissions:
                                        driver = sub['podium_3']
                                        p3_counts[driver] = p3_counts.get(driver, 0) + 1
                                    
                                    p3_df = pd.DataFrame(list(p3_counts.items()), columns=['Kierowca', 'Liczba typowań'])
                                    p3_df = p3_df.sort_values('Liczba typowań', ascending=False)
                                    
                                    # Dodaj zaznaczenie dla faktycznego zwycięzcy
                                    p3_df['Faktyczny wynik'] = p3_df['Kierowca'] == result['podium_3']
                                    
                                    st.dataframe(p3_df)
                            
                            with stats_tabs[1]:
                                # Inne statystyki
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write("#### Różnica czasowa")
                                    time_counts = {}
                                    for sub in submissions:
                                        time = sub['time_diff']
                                        time_counts[time] = time_counts.get(time, 0) + 1
                                    
                                    time_df = pd.DataFrame(list(time_counts.items()), columns=['Przedział', 'Liczba typowań'])
                                    time_df = time_df.sort_values('Liczba typowań', ascending=False)
                                    
                                    # Dodaj zaznaczenie dla faktycznego wyniku
                                    time_df['Faktyczny wynik'] = time_df['Przedział'] == result['time_diff']
                                    
                                    st.dataframe(time_df)
                                
                                with col2:
                                    st.write("#### Safety Car")
                                    sc_counts = {"Tak": 0, "Nie": 0}
                                    for sub in submissions:
                                        if sub['safety_car']:
                                            sc_counts["Tak"] += 1
                                        else:
                                            sc_counts["Nie"] += 1
                                    
                                    sc_df = pd.DataFrame(list(sc_counts.items()), columns=['Opcja', 'Liczba typowań'])
                                    
                                    # Dodaj zaznaczenie dla faktycznego wyniku
                                    sc_df['Faktyczny wynik'] = sc_df['Opcja'] == ("Tak" if result['safety_car'] else "Nie")
                                    
                                    st.dataframe(sc_df)
                                    
                                    # Pokaż wyniki w postaci wykresu kołowego
                                    st.write("Rozkład typowań (Safety Car):")
                                    fig, ax = plt.subplots()
                                    ax.pie(sc_df['Liczba typowań'], labels=sc_df['Opcja'], autopct='%1.1f%%')
                                    st.pyplot(fig)
                            
                            # Możliwość eksportu danych
                            st.subheader("Eksport danych")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button("Eksportuj tabelę wyników do CSV"):
                                    csv = points_df.to_csv(index=False)
                                    st.download_button(
                                        label="Pobierz plik CSV z wynikami",
                                        data=csv,
                                        file_name=f"wyniki_{race_options[selected_race_index].replace(' ', '_')}.csv",
                                        mime="text/csv"
                                    )
                            
                            with col2:
                                if st.button("Eksportuj wszystkie odpowiedzi do CSV"):
                                    subs_df = pd.DataFrame(submissions)
                                    # Uproszczenie danych JSON do eksportu
                                    subs_df['extra_answers'] = subs_df['extra_answers'].apply(lambda x: str(x))
                                    csv = subs_df.to_csv(index=False)
                                    st.download_button(
                                        label="Pobierz plik CSV z odpowiedziami",
                                        data=csv,
                                        file_name=f"odpowiedzi_{race_options[selected_race_index].replace(' ', '_')}.csv",
                                        mime="text/csv"
                                    )
                        else:
                            st.warning(f"Brak wprowadzonych wyników dla wyścigu {race_options[selected_race_index]}. Najpierw wprowadź wyniki w zakładce 'Wyniki'.")
                    else:
                        st.info(f"Brak odpowiedzi dla wyścigu {race_options[selected_race_index]}.")
                else:
                    st.info("Brak wyścigów. Najpierw dodaj wyścig w zakładce 'Wyścigi'.")

# Ogłoszenia dotyczące najnowszego wyścigu i aktualnej klasyfikacji
if active_races:
    with st.expander("Aktualna klasyfikacja"):
        if not supabase_connected:
            st.warning("Brak połączenia z bazą danych. Nie można wyświetlić klasyfikacji.")
        else:
            try:
                # Pobieranie wszystkich wyścigów z wprowadzonymi wynikami
                results_response = supabase.table('results').select('race_id').execute()
                race_ids_with_results = [r['race_id'] for r in results_response.data]
                
                if race_ids_with_results:
                    # Pobieranie wszystkich odpowiedzi dla wyścigów z wynikami
                    all_submissions = []
                    
                    for race_id in race_ids_with_results:
                        # Pobierz wyniki wyścigu
                        race_result = supabase.table('results').select('*').eq('race_id', race_id).single().execute().data
                        
                        # Pobierz dane wyścigu
                        race_data = supabase.table('races').select('*').eq('id', race_id).single().execute().data
                        
                        # Pobierz wszystkie typy dla tego wyścigu
                        race_submissions = supabase.table('submissions').select('*').eq('race_id', race_id).execute().data
                        
                        # Oblicz punkty dla każdego użytkownika
                        for submission in race_submissions:
                            points = 0
                            print(submission['user_name'])
                            # Podium - do 4 punktów
                            podium_points = 0
                            if submission['podium_1'] == race_result['podium_1']:
                                podium_points += 1
                            
                            if submission['podium_2'] == race_result['podium_2']:
                                podium_points += 1
                            
                            if submission['podium_3'] == race_result['podium_3']:
                                podium_points += 1
                            
                            # Bonus za idealne podium
                            if podium_points == 3:
                                podium_points += 1
                            
                            points += podium_points
                            
                            # Pozostałe kategorie - po 1 punkcie
                            if submission['time_diff'] == race_result['time_diff']:
                                points += 1
                            
                            if submission['driver_of_day'] == race_result['driver_of_day']:
                                points += 1
                            
                            if submission['safety_car'] == race_result['safety_car']:
                                points += 1
                            
                            if submission['red_flag'] == race_result['red_flag']:
                                points += 1
                            
                            if submission['classified_drivers'] == race_result['classified_drivers']:
                                points += 1
                            
                            if submission['teams_with_points'] == race_result['teams_with_points']:
                                points += 1
                            
                            # Pytania dodatkowe
                            for key, value in submission['extra_answers'].items():
                                if key in race_result['extra_answers'] and value == race_result['extra_answers'][key]:
                                    points += 1
                            
                            all_submissions.append({
                                "user_name": submission['user_name'],
                                "race_name": race_data['race_name'],
                                "race_date": race_data['race_date'],
                                "points": points
                            })
                    
                    if all_submissions:
                        # Stwórz DataFrame z wszystkimi typami
                        all_subs_df = pd.DataFrame(all_submissions)
                        
                        # Grupuj po użytkowniku i sumuj punkty
                        user_points = all_subs_df.groupby('user_name')['points'].sum().reset_index()
                        user_points = user_points.sort_values('points', ascending=False)
                        
                        # Dodaj ranking
                        user_points['pozycja'] = user_points['points'].rank(method='min', ascending=False).astype(int)
                        user_points = user_points[['pozycja', 'user_name', 'points']]
                        user_points.columns = ['Pozycja', 'Imię', 'Suma punktów']
                        
                        # Dodaj liczbę wyścigów
                        races_count = all_subs_df.groupby('user_name').size().reset_index()
                        races_count.columns = ['Imię', 'races_count']
                        

                        user_points = user_points.merge(races_count, on='Imię')
                        
                        user_points['Liczba wyścigów'] = user_points['races_count']
                        user_points['Średnio na wyścig'] = (user_points['Suma punktów'] / user_points['Liczba wyścigów']).round(1)
                        
                        # Wyświetl finałową tabelę
                        final_table = user_points[['Pozycja', 'Imię', 'Suma punktów', 'Liczba wyścigów', 'Średnio na wyścig']]
                        st.table(final_table)
                        
                        # Wykres z top 3 użytkownikami
                        st.subheader("Najlepsi typujący")
                        top3 = user_points.head(3)
                        fig, ax = plt.subplots()
                        ax.bar(top3['Imię'], top3['Suma punktów'])
                        st.pyplot(fig)
                    else:
                        st.info("Brak danych do wyświetlenia. Wprowadź wyniki wyścigów i odpowiedzi użytkowników.")
                else:
                    st.info("Brak wyścigów z wprowadzonymi wynikami.")
            except Exception as e:
                st.error(f"Błąd podczas pobierania klasyfikacji: {e}")
st.markdown("🏎️ F1 Ankietka by Piotr Antoniszyn © 2025")
