## Sklep internetowy (Flask)

Prosty sklep z podzespolami komputerowymi, koszykiem, zamowieniami i panelem admina.

### Uruchomienie

1. Utworz srodowisko i zainstaluj zaleznosci:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Uruchom aplikacje:

```bash
python main.py
```

3. Otworz w przegladarce: `http://127.0.0.1:5000`

### Loginy startowe

- Lokalnie: `admin@sklep.local` / `admin123` (jesli nie ustawisz `ADMIN_PASSWORD`).
- Uzytkownicy: rejestracja w UI.

### Dane i konfiguracja

- Baza danych SQLite jest zapisywana w `instance/shop.db`.
- Sekret ustawisz przez zmienna `SECRET_KEY` (w produkcji jest wymagany).
- Admin w produkcji: ustaw `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
- Jesli chcesz wymusic reset admina z env, ustaw `ADMIN_FORCE_RESET=1`.
- Usun plik bazy, aby zresetowac dane i ponownie zasianac produkty.

### Deploy na Render (darmowy plan)

1. Wrzuc projekt na GitHub.
2. Na Render: New -> Blueprint i wybierz repo (wykorzysta `render.yaml`).
3. Ustaw:

```
Build Command: pip install -r requirements.txt
Start Command: gunicorn main:app --bind 0.0.0.0:$PORT
```

4. Dodaj Postgres na Render i ustaw w Web Service:

```
DATABASE_URL=<Render Postgres URL>
SECRET_KEY=<losowy dlugi sekret>
ADMIN_EMAIL=<twoj email>
ADMIN_USERNAME=<twoj login>
ADMIN_PASSWORD=<twoje haslo>
ADMIN_FORCE_RESET=1
```

5. Po pierwszym starcie zaloguj sie do panelu admina i zmien haslo w:
	`/admin/password`.
6. Wejdz w ustawienia domeny w Render i podlacz swoja domene:
	- Render -> Settings -> Custom Domains -> Add.
	- Skopiuj rekordy DNS z Render i wklej u rejestratora domeny.
	- Po propagacji DNS Render sam wygeneruje SSL.
