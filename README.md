# F1 Quiz App

Aplikacja Streamlit do typowania wyników wyścigów Formuły 1 z systemem punktowym i klasyfikacją generalną.

## Funkcje

- Formularz typowania wyników (podium, Safety Car, czerwona flaga i więcej)
- Pytania dodatkowe konfigurowane przez administratora osobno dla każdego wyścigu
- Automatyczne obliczanie punktów po wprowadzeniu wyników przez admina
- Klasyfikacja generalna z podsumowaniem wszystkich wyścigów
- Panel administratora do zarządzania wyścigami, pytaniami i wynikami
- Baza danych Supabase jako backend

## Wymagania

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Konto Supabase

## Instalacja i uruchomienie

```bash
git clone https://github.com/PiotrAntoniszyn/f1-quiz-app.git
cd f1-quiz-app

uv sync

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# uzupełnij secrets.toml swoimi danymi

uv run streamlit run F1-quiz-app_v2.py
```

## Konfiguracja secrets.toml

```toml
[email]
sender = "twoj_email@gmail.com"
password = "haslo_do_aplikacji"  # hasło aplikacji Gmail

[admin]
password = "twoje_haslo_admina"

[supabase]
url = "https://xxx.supabase.co"
key = "twoj_anon_key"
```

## Panel administratora

Dostępny po kliknięciu ikony 👤 w prawym dolnym rogu. Wymaga hasła z `secrets.toml`.

Zakładki panelu:
1. **Ustawienia** — zmiana opisu aplikacji
2. **Wyścigi** — dodawanie/deaktywowanie wyścigów i terminów typowania
3. **Pytania** — zarządzanie pytaniami dodatkowymi dla każdego wyścigu
4. **Wyniki** — wprowadzanie rzeczywistych wyników wyścigu
5. **Statystyki** — tabela punktów, rozkład typowań, eksport CSV

## System punktacji

| Kategoria | Punkty |
|-----------|--------|
| Kierowca na właściwej pozycji podium | 1 pkt × 3 |
| Bonus za idealne podium (wszystkie 3) | +1 pkt |
| Różnica czasowa, DOTD, Safety Car, czerwona flaga, liczba kierowców, liczba zespołów | 1 pkt każde |
| Pytania dodatkowe | 1 pkt każde |

Maksimum z pytań stałych: **11 punktów** (bez pytań dodatkowych).

## Tabele Supabase

- `races` — wyścigi (nazwa, data, termin typowania, is_active)
- `submissions` — typy użytkowników
- `results` — rzeczywiste wyniki wprowadzone przez admina
- `custom_questions` — pytania dodatkowe przypisane do wyścigu
- `app_settings` — opis aplikacji

## Licencja

© 2025 Piotr Antoniszyn
