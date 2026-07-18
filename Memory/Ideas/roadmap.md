# Atlas Roadmap — Idei dlya razvitiya

## Princip
Kazhdaya ideya imeet:
- **Status**: [ ] zaplanirovano / [-] v rabote / [x] gotovo / [!] otlozheno
- **Prioritet**: high / medium / low
- **Otvetstvennyy**: kakoy agent / chelovek
- **Opisanie**: chto delat

---

## Aktivnye (v rabote ili na ochredi)

### 1. Brief Agent
- **Status**: [-]
- **Prioritet**: high
- **Otvetstvennyy**: Executive + Brief Agent
- **Opisanie**: Iz korotkogo zaprosa generirovat podrobnoe TZ (brief.md) s kontentom, kontaktami, uslugami. Developer dolzhen chitat brief pri zapolnenii shablona.

### 2. Uluchshennyy shablon s animatsiyami
- **Status**: [ ]
- **Prioritet**: high
- **Otvetstvennyy**: Developer
- **Opisanie**: Dobavit v modern_landing:
  - Animatsii poyavleniya pri skrolle (fade-up, fade-in)
  - Hover-effekty na knopki i kartochki
  - Parallaks na hero-sektsii
  - Galereya s laytboksom
  - Sektsiya "Menu" / "Tsennik"
  - Karta (iframe Google Maps)
  - Forma obratnoy svyazi

### 3. QA Agent
- **Status**: [ ]
- **Prioritet**: medium
- **Otvetstvennyy**: novyy agent QA
- **Opisanie**: Posle sozdaniya sayta otkryvat index.html v Playwright, delat skrinshot, proveryat:
  - Net li oshibok v konsole
  - Vse ssylki rabotayut
  - Adaptivnost (3 razmera ekrana)
  - Net pustykh placeholderov

### 4. Model Router
- **Status**: [-]
- **Prioritet**: medium
- **Otvetstvennyy**: Config/llm_client.py
- **Opisanie**: Avtomaticheski vybirat model:
  - 3B dlya bystrykh zadach (Developer)
  - 7B dlya slozhnykh (Executive, Self-Upgrade)
  - Oblochnyye modeli (Claude/GPT) pozdnee, kogda budet byudzhet

---

## Zaplanirovannoye (posle pervykh deneg)

### 5. Veb-interfeys (Dashboard)
- **Status**: [ ]
- **Prioritet**: low (do dokhoda)
- **Otvetstvennyy**: Developer + Designer
- **Opisanie**: HTML-stranitsa dlya upravleniya Atlas:
  - Pole vvoda zadachi
  - Spisok proektov
  - Knopka "Zapustit"
  - Prosmotr logov
  - Upravleniye skillami

### 6. Telegram Agent
- **Status**: [ ]
- **Prioritet**: low
- **Otvetstvennyy**: novyy agent
- **Opisanie**: Avtootvetchik v Telegram, priyom zayavok s sayta, rassylka novostey klientam.

### 7. Browser Agent (Lead Generation)
- **Status**: [ ]
- **Prioritet**: low
- **Otvetstvennyy**: novyy agent
- **Opisanie**: Iskat klientov v internete (avito, yandex, google), sobirat kontakty, otpravlyat predlozheniya.

### 8. Designer Agent
- **Status**: [ ]
- **Prioritet**: low
- **Otvetstvennyy**: novyy agent
- **Opisanie**: Ne prosto zapolnyat shablon, a sozadavat unikalnyy dizayn pod zadachu. Rabotat s tsvetami, shriftami, kompozitsiey.

---

## Gotovoye (realizovano)

### 9. Struktura proekta
- **Status**: [x]
- **Opisanie**: Atlas/, HQ/, Agents/, Projects/, Tools/, Memory/, Config/

### 10. Svяз s Ollama
- **Status**: [x]
- **Opisanie**: llm_client.py rabotayet s 3B i 7B

### 11. Executive Agent
- **Status**: [x]
- **Opisanie**: Planiruyet zadachi, vybirayet agentov

### 12. Developer Agent
- **Status**: [x]
- **Opisanie**: Sozdayet sayty po shablonu

### 13. Skills Manager
- **Status**: [x]
- **Opisanie**: Ustanovka skillov iz GitHub

### 14. Self-Upgrade
- **Status**: [x]
- **Opisanie**: Analiziruyet kod, sohranyayet predlozheniya

---

## Kak dobavit novuyu ideyu

1. Otkroy etot fayl
2. Dobavit razdel s statusom [ ]
3. Ukazhi prioritet i opisaniye
4. Pri realizatsii menyay status na [-], potom na [x]
5. Perenesi v razdel "Gotovoye"

**Pravilo**: ne bolshe 3 aktivnykh zadach odnovremenno. Fokus vazhney kolichestva.

---

## Pravilo sistemy: Ne izobretay velosiped

**Status**: [x] Aktivno
**Otvetstvennyy**: Vse agenty

### Soderzhanie
Pered sozdaniem novogo instrumenta, modulya ili funktsii:
1. Proverit, est li gotovoe bespaltnoe reshenie (open source, GitHub, npm, pip)
2. Esli est — ispolzovat. Esli net — sozdat svoe.
3. Predpochitat instrumenty s aktivnym soobshchestvom i dokumentatsiey.

### Primer
- Nuzhna baza dannykh? → SQLite (est), a ne svoy format
- Nuzhen veb-server? → GitHub Pages / Netlify (besplatno), a ne svoy hosting
- Nuzhny animatsii? → AOS.js / GSAP (est), a ne svoy CSS s nulya
- Nuzhen parsing? → Playwright / BeautifulSoup (est)
- Nuzhno planirovanie? → CrewAI / LangChain (est)

### Zapreshcheno
- Pisat svoy veb-server dlya staticheskikh saytov
- Pisat svoyu ORM vmesto SQLAlchemy
- Pisat svoy parsik vmesto Playwright
- Sozdavat svoy format konfigov vmesto JSON/YAML/TOML

### Isklyuchenie
Mozhno sozdavat svoy kod, esli:
- Gotovye resheniya ne pokryvayut zadachu
- Litsenziya zapreshchaet kommercheskoe ispolzovanie
- Resheniye slishkom tyazheloye dlya zadachi

