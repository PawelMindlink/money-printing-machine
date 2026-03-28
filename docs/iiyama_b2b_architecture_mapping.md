# Iiyama Architektura: Katalog (MECE) vs Strategia Meta Ads B2B

Aby precyzyjnie operować na koncie Meta Ads bez "Ad Set Creative Bleed", algorytm Iiyamy został rozdzielony na dwie niezależnie funkcjonujące warstwy. Poniższe zestawienie stanowi twardą definicję struktury dla kampanii Advantage+ Catalog Ads.

---

## Filar 1: Kategorie Katalogu Reklamowego (Struktura Feedu / MECE)

Kategoryzacja MECE (Mutually Exclusive, Collectively Exhaustive) zapewnia, że w feedzie reklamowym dany fizyczny produkt pasuje **tylko do jednego wiadra**. Jest to krytyczne dla przypisywania prawidłowej grupy marżowej do wyliczeń ROAS-u. Zgodnie z cennikiem i opłacalnością sprzedaży, sprzęt Iiyama dzieli się na dwie główne grupy marżowe: **10%** oraz **15%**.

**Grupa Marżowa 10% (Wysoce konkurencyjny Czerwony Ocean lub sprzęt masowy z ustandaryzowaną ceną):**

* **01. Gaming (G-Master):** Typowy rynek B2C, mocna wojna cenowa i ciągłe promocje ("Gracz PC").
* **02. Office / Home (ProLite):** Standardowe proporcje biurowe B2B/B2C, monitory kupowane tysiącami do korporacji, gdzie marża ustępuje skali.
* **03. ProGraphic:** Monitory graficzne kierowane do purystów barwowych – sprzęt ustandaryzowany technicznie i cenowo, traktowany jako "Office dla specjalistów".
* **06. Signage (LFD):** Podstawowe ekrany do wyświetlania treści (często kupowane detalicznie jako "telewizory biznesowe") – bardzo konkurencyjna i popularna w internecie kategoria ekranów bezobsługowych, gdzie toczy się walka cenowa wielkich sklepów rtv/agd.

**Grupa Marżowa 15% (Specjalistyczny B2B Niebieski Ocean / Rozwiązania premium i wieloformatowe):**

* **04. Touch Biurkowy (POS):** Monitory dotykowe z podstawką pod ciężkie stanowiska kasowe (NISZA).
* **05. Touch Open-Frame:** Monitory dotykowe do zabudowy OEM, tzw. "golas", bez ramki zewnętrznej. Sprzęt czysto techniczny dla integratorów.
* **07. IFP / Tablice (Edukacja):** Modele interaktywne serii TE. Posiadają wbudowane aplikacje dla szkół (np. Note, paski narzędzi dla nauczycieli), są zoptymalizowane pod edukację i finansowane z projektów (Aktywna Tablica).
* **08. IFP / Tablice (Biznes & Konferencje):** Flagowe monitory (często z certyfikacją Google EDLA / linia PRO). Naszpikowane zabezpieczeniami (MDM), zintegrowane natywnie z Microsoft Teams / Zoom Rooms, posiadające optyczne klejenie szyb (zero parallax) oraz mikrofony kierunkowe do profesjonalnych wideokonferencji. To sprzęt premium "Enterprise".
* **09. Infokioski:** Stojące, kompletne bryły z wbudowanym komputerem do obudowy i ekranem. W pełni gotowy mebel interaktywny.
* **10. Wirtualna Gazetka (Retail HW+SW):** Specyficzna linia modeli WG (np. WG50, WG55). To ekrany sprzedawane *od razu w pre-konfigurowanym pakiecie z dedykowanym systemem CMS*, pozwalającym np. menadżerowi sieci aptek wpiąć je do gniazdka i natychmiast wrzucać z warszawy spoty promocyjne na ekrany w Gdańsku i Krakowie.
* **11. Montaż & Akcesoria AV oraz 12. Kable, Adaptery, Folie:** Marża potrafi tu wynosić powyżej 15%, traktujemy je w najbezpieczniejszym ujęciu.

---

## Filar 2: Kategorie Biznesowe (Persony docelowe w Meta)

Kluczem w B2B z użyciem Meta Ads jest odróżnienie decydenta w konkretnej branży. Tego samego urządzenia potrzebują kompletnie inni ludzie, motywowani zupełnie różnymi portfelami. Wyselekcjonowane przez nas branżowe Ad Sety:

* **Sklepy Retail** - Celowanie w sieci, małą i średnią sprzedaż półkową. Decydent: Właściciel, Manager sieci (rozwiązania na witrynę, digitalizacje metek, digital shelving).
* **Gastronomia (QSR - Kebaby, Fast Foody, Kawiarnie)** - Celowanie w prywatnych małych przedsiębiorców. Decydent: Właściciel budki, właściciel kawiarni, gdzie cel to "zmniejsz kolejkę" wprowadzając self-service lub cyfrowe menu na ścianie.
* **Prywatne Kliniki Medyczne & Apteki** - Redukcja niepokoju czekającego pacjenta, zdigitalizowane cenniki Medycyny Estetycznej.
* **Nieruchomości & Deweloperzy** - Narzędzie obracania wielkim kapitałem B2C (cyfrowe rzuty deweloperskie w oknach prestiżowych biur).
* **Hotele & Lobby** - Prestiż placówki i nawigacja gości, digital concierge (CX i standard hotelu jako najwyższa wartość).
* **Korporacje (HR & Komunikacja)** - Rezerwacja sal, "Room booking", wewnętrzne KPI dla pracowników (decudent to IT lub Head of HR).
* **Kluby Fitness** - Cenniki, grafik zajęć, puszczanie Spotify i reklam białka. Decydent: Manager klubu (optymalizacja przestrzeni).
* **Salony Beauty & SPA** - Prestiż poczekalni, interaktywne portfolio usług oraz pętle reklamowe przed/po, skierowane do zamożnego klienta VIP przebywającego w salonie przez 2 godziny.

---

## Filar 3: Matryca Mapowania (Jak układać kampanie?)

Takie mapowanie zaszyte jest w kolumnach `ad_set_N`, dając wgląd analityczny pod budowę Zestawów Reklamowych (tworzonych z unikalnym Copy, doczepianych w Menedżerze Reklam do Katalogów MECE).

| Kategoria Katalogowa (MECE) | Rekomendowane Ad Sety (Cele targetowania) | Przypisana Marża Do Wyliczeń Algorytmu |
| :--- | :--- | :--- |
| **01. Gaming** | Gracze PC (B2C). *Brak sensu profilowania do biznesów.* | 10% |
| **02. Office / Home** | Praca Zdalna (WFH), MSP & Czyste Biura B2B (Menedżerowi IT zakupujący sprzęt operacyjny). | 10% |
| **03. ProGraphic** | Studia Graficzne, Agencje Reklamowe (B2B), Niezależni Architekci/Projektanci DTP (B2B/B2C). | 10% |
| **04. Touch Biurkowy** | **Gastronomia (QSR)** (stanowisko kelnerskie), **Sklepy Retail** (Kasa sklepowa), **Prywatne Kliniki & Apteki** (obsługa NFZ), **Hotele** (Recepcje). | 15% |
| **05. Touch Open-Frame** | Baza do dalszej produkcji: **Producent Maszyn (OEM)**, **Integratorzy IT**, **Muzea & Wystawy publiczne** (do mebli wystawienniczych). | 15% |
| **06. Signage** | Najszerszy lejek: **Sklepy Retail**, **Gastronomia (QSR)**, **Nieruchomości & Deweloperzy**, **Hotele & Lobby**, **Kluby Fitness**, **Salony Beauty & SPA**, **Korporacje (Komunikacja)**. | 10% |
| **07. IFP / Tablice (Edukacja)** | Cel twardo dydaktyczny: **Szkoły Publiczne**, **Uczelnie Wyższe**, oraz prywatny biznes edukacyjny: **Szkoły Prywatne**. | 15% |
| **08. IFP / Tablice (Biznes)** | Wyższa półka współpracy: **Korporacje & Sale Konferencyjne**, **Hotele (Centra Konferencyjne pod wynajem)**, wyspecjalizowane **Szkoły Językowe & Szkoleniowcy B2B**. | 15% |
| **09. Infokioski** | **Prywatne Kliniki & Przychodnie** (Terminal Rejestracji), **Galerie Handlowe** (Mapy centrum dla zarządców), **Salony Beauty & SPA** (Cyfrowy katalog zabiegów), **Muzea** (Interaktywne ekspozytory przestrzenne). | 15% |
| **10. Wirtualna Gazetka** | Narzędzia masowej zmiany wyświetlania cen / promocji: **Sklepy Retail** oraz **Gastronomia (QSR)**. | 15% |

### Zasada Akcesoriów i Drobnej Elektroniki

Produkty z kategorii **Montaż & Akcesoria AV** oraz **Kable, Adaptery, Folie** to tzw. *Commodity* i sprzęt up-sellowy. W kampaniach Prospecting (wychodzących na zimny ruch na B2B u Mety) ich reklamowanie nie spina się finansowo (CPA zje całą marżę uchwytu). Produkty te są celowo **wyłączone** ze sztywnego targetowania person w B2B. Wykorzystujemy je tylko w najczystszym, bardzo tanim Retargetingu (np. dodaj do koszyka i nie kupił) jako uzupełniacz pełnej wartości zamówienia (AOV).
