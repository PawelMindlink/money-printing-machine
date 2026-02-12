# Instrukcja Setupu dla Zespołu - n8n & Antigravity

Witaj w zespole! Ta instrukcja pomoże Ci skonfigurować środowisko, abyś mógł/mogła tworzyć i synchronizować workflowy n8n bezpośrednio z VS Code przy użyciu Antigravity.

## 1. Wymagania

Upewnij się, że masz zainstalowanego Pythona oraz bibliotekę `requests`:

```bash
pip install requests python-dotenv
```

## 2. Konfiguracja kluczy (Security)

Używamy zmiennych środowiskowych, aby nie wysyłać kluczy do Git.

1. Skopiuj `.env.template` -> `.env`.
2. Wpisz swój `N8N_API_KEY` w pliku `.env`.

## 3. Toolset n8n (Twoje skrypty)

W repozytorium masz zestaw narzędzi do obsługi API:

| Skrypt | Opis |
| :--- | :--- |
| `create_workflow.py` | Tworzy nowy, pusty workflow w n8n i zwraca jego ID. |
| `live_sync.py` | Synchronizacja w czasie rzeczywistym (Zapis pliku -> Aktualizacja n8n). |
| `force_sync.py` | Jednorazowe wymuszenie wysłania pliku lokalnego do n8n. |
| `check_n8n_access.py` | Szybki test połączenia z API (wyświetla listę Twoich workflowów). |
| `check_server_creds.py` | Debugging: sprawdza jakie credentials są podpięte pod węzły na serwerze. |

## 4. Praca z Antigravity (AI)

Ponieważ pracujesz z Antigravity, możesz wykorzystać ten setup do automatyzacji budowania:

### Scenariusz: Tworzenie nowego workflow od zera

1. Uruchom `python create_workflow.py "Mój Nowy Test"`.
2. Skopiuj ID i wklej je do `live_sync.py` jako `WORKFLOW_ID`.
3. Uruchom `python live_sync.py`.
4. Powiedz do Antigravity:
   > "Antigravity, stwórz dla mnie w pliku JSON podstawową strukturę workflow n8n, który pobiera dane z Webhooka i zapisuje je do Google Sheets."
5. AI wygeneruje kod w pliku, a skrypt `live_sync.py` od razu wyśle go do n8n.

### Protip dla AI

Jeśli Antigravity nie wie jak zbudować dany węzeł, skieruj je na pliki w folderze `Workflows/` jako przykłady:
> "Użyj @[Workflows/MSC_ALGO_v4_Pipeline.json] jako wzoru dla połączeń między węzłami."

## 5. Security Checklist

- [ ] Czy `.env` jest w `.gitignore`? (Tak, powinien być).
- [ ] Czy nie zostawiłeś/łaś klucza w kodzie `live_sync.py`?
