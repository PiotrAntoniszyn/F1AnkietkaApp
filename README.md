# F1 Quiz App

Aplikacja Streamlit do przeprowadzania typowania wyników wyścigów Formuły 1.

## Funkcje

- Formularz do typowania wyników wyścigów F1
- System punktowy oparty na trafności przewidywań
- Dynamicznie aktualizowane pytania dodatkowe
- Powiadomienia e-mail z wynikami typowania w formacie CSV
- Panel administratora do zarządzania pytaniami i ustawieniami

## Wymagania

- Python 3.7+
- Streamlit
- Pandas
- Pillow (PIL)

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/twojnazwauzytkownika/f1-quiz-app.git
cd f1-quiz-app
```

2. Zainstaluj wymagane pakiety:
```bash
pip install -r requirements.txt
```

3. Skonfiguruj dane dostępowe do konta e-mail:
   - Utwórz plik `.streamlit/secrets.toml`
   - Dodaj dane dostępowe do e-maila i hasło administratora:
```toml
[email]
sender = "twoj_email@gmail.com"
password = "haslo_do_aplikacji"  # dla Gmail użyj hasła aplikacji

[admin]
password = "twoje_haslo_admina"
```

4. Dodaj obrazek `fernando.png` do katalogu głównego aplikacji (lub zaktualizuj kod, aby używał innego obrazka)

## Uruchomienie

```bash
streamlit run F1-quiz-app.py
```

## Panel administratora

Aplikacja zawiera ukryty panel administratora, dostępny po kliknięciu ikony 👤 w prawym dolnym rogu strony.

### Funkcje panelu administratora:

1. **Zmiana opisu aplikacji** - aktualizacja tekstu wyświetlanego pod tytułem
2. **Zarządzanie pytaniami dodatkowymi** - edycja treści pytań i dostępnych opcji odpowiedzi
3. **Eksport konfiguracji** - możliwość pobrania pytań w formacie JSON

### Dostęp do panelu administratora:

1. Kliknij ikonę 👤 w prawym dolnym rogu aplikacji
2. Wprowadź hasło administratora skonfigurowane w pliku `secrets.toml`
3. Po zalogowaniu panel administratora pojawi się w bocznym menu

## Struktura pytań

Quiz składa się z następujących sekcji:
1. Podium wyścigu (3 kierowców)
2. Różnica czasowa między 1. a 2. miejscem
3. Kierowca dnia (Driver of The Day)
4. Obecność Safety Car podczas wyścigu
5. Obecność czerwonej flagi podczas wyścigu
6. Liczba sklasyfikowanych kierowców
7. Liczba zespołów z punktami
8. Pytania dodatkowe (konfigurowalne przez administratora)

## System punktacji

- Podium: 1 punkt za każdego prawidłowo wytypowanego kierowcę + 1 dodatkowy punkt za idealne podium (maks. 4 punkty)
- Pozostałe kategorie: 1 punkt za prawidłową odpowiedź

## Pliki konfiguracyjne

Aplikacja wykorzystuje dwa pliki JSON do przechowywania konfiguracji:

1. **questions.json** - zawiera pytania dodatkowe i ich opcje:
```json
[
  {
    "question": "Czy będzie najszybsze okrążenie z punktem bonusowym dla kierowcy w TOP10?",
    "options": ["Tak", "Nie"]
  },
  {
    "question": "Który zespół zdobędzie więcej punktów?",
    "options": ["Red Bull", "Ferrari", "Mercedes", "McLaren", "Inny"]
  }
]
```

2. **app_settings.json** - zawiera ogólne ustawienia aplikacji:
```json
{
  "app_description": "### Typuj wyniki wyścigów Formuły 1 i zdobywaj punkty!"
}
```

## Uwagi

- Pliki konfiguracyjne są tworzone automatycznie przez panel administratora
- Aplikacja jest przystosowana do wdrożenia na Streamlit Cloud
- Aby używać funkcji e-mail z Gmail, należy użyć hasła aplikacji, a nie głównego hasła konta

## Licencja

© 2025 Piotr Antoniszyn
