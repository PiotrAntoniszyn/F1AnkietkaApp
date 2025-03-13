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

# Konfiguracja strony
st.set_page_config(page_title="F1 Ankietka", page_icon="🏎️", layout="wide")

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

# Funkcja ładująca pytania
def load_questions():
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

# Funkcja wysyłająca email
def send_email(predictions, user_name):
    try:
        # Konfiguracja emaila - te dane należy zastąpić własnymi
        email_sender = st.secrets.email.sender
        email_password = st.secrets.email.password
        admin_email = st.secrets.email.sender
        
        # Przygotowanie wiadomości
        subject = f"[F1 Quiz App] Nowe typy F1 od {user_name}"
        
        # Formatowanie przewidywań do emaila
        email_body = f"""
        Nowe typy F1 od {user_name} 
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

# Ładujemy dodatkowe pytania
custom_questions = load_questions()

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
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.text_input("Imię")
   
    
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
            
            # Wysyłamy email
            if send_email(predictions, user_name):
                st.success("Twoje typy zostały wysłane! Powodzenia! 🏆")
                
                # Pokazujemy podsumowanie
                st.subheader("Podsumowanie Twoich typów:")
                
                # Tworzymy tabelę z przewidywaniami
                df = pd.DataFrame(list(predictions.items()), columns=["Kategoria", "Twój typ"])
                st.table(df)
                img = Image.open("fernando.png")
                st.image(img, caption="Twoje zdjęcie", use_container_width=True)
            else:
                st.error("Wystąpił problem podczas wysyłania formularza. Spróbuj ponownie.")

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

st.markdown("🏎️ F1 Ankietka by Piotr Antoniszyn © 2025")

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
                        #st.rerun()
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
        
        # Sekcja z podstawowymi ustawieniami aplikacji
        st.subheader("Ogólne ustawienia aplikacji")
        
        # Edycja opisu aplikacji
        app_description = st.text_area(
            "Opis aplikacji (tekst pod tytułem)",
            value=app_description.replace("### ", ""),
            help="Zmień główny opis aplikacji wyświetlany pod tytułem. Domyślnie: 'Typuj wyniki wyścigów Formuły 1 i zdobywaj punkty!'"
        )
        
        # Aktualizacja opisu aplikacji w sesji
        st.session_state.app_settings["app_description"] = f"### {app_description}"
        
        # Przycisk do zapisywania ustawień ogólnych
        if st.button("Zapisz ustawienia ogólne"):
            if save_app_settings():
                st.success("Ustawienia zostały zapisane!")
                st.rerun()  # Odświeżenie aplikacji, aby pokazać zmiany
        
        st.markdown("---")
        
        st.subheader("Zarządzanie pytaniami dodatkowymi")
        
        # Edycja istniejących pytań
        for i, question in enumerate(custom_questions):
            st.subheader(f"Pytanie {i+1}")
            question_text = st.text_area(f"Treść pytania {i+1}", value=question["question"])
            options_text = st.text_area(f"Opcje (każda w nowej linii) {i+1}", 
                                     value="\n".join(question["options"]))
            
            # Aktualizuj pytanie
            custom_questions[i]["question"] = question_text
            custom_questions[i]["options"] = [opt.strip() for opt in options_text.split("\n") if opt.strip()]
        
        # Zapisz zmiany
        if st.button("Zapisz pytania"):
            try:
                # W praktyce tutaj dodaj kod do zapisania pytań
                # np. do pliku lub bazy danych
                with open("questions.json", "w", encoding="utf-8") as file:
                    json.dump(custom_questions, file, ensure_ascii=False, indent=2)
                st.success("Pytania zostały zaktualizowane!")
                st.rerun()  # Odświeżenie aplikacji, aby pokazać zmiany
            except Exception as e:
                st.error(f"Błąd podczas zapisywania pytań: {e}")
        
        # Przycisk do eksportu pliku JSON z pytaniami
        if st.button("Eksportuj pytania (JSON)"):
            json_str = json.dumps(custom_questions, ensure_ascii=False, indent=2)
            st.download_button(
                label="Pobierz plik JSON z pytaniami",
                data=json_str,
                file_name="questions.json",
                mime="application/json"
            )