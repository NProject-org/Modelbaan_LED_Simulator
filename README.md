Project van NProject.org

Welkom bij de Arduino LED Simulatie Tool!

Het tot leven brengen van je modelbaan met realistische verlichting is de droom van elke modelbouwer. Maar laten we eerlijk zijn: het constant testen van LED-patronen en het finetunen van je Arduino-code kan een behoorlijke uitdaging zijn, vooral met complexe opstellingen. Hoe vaak heb je niet gefrustreerd draden losgekoppeld of code geüpload, alleen om te ontdekken dat het effect nét niet klopt?

Goed nieuws! We hebben een slimme oplossing ontwikkeld die je veel tijd en hoofdpijn gaat besparen: de Python-gebaseerde Arduino LED Simulatie Tool. Deze handige applicatie, gebouwd met tkinter, laat je alle denkbare LED-patronen simuleren en configureren, nog voordat je ook maar één draad aan je fysieke Arduino hoeft te verbinden. Zo zie je direct het resultaat en perfectioneer je je verlichting zonder gedoe.

Wat kan deze tool?
-------------------

De tool biedt een intuïtieve grafische interface waarin je alle functionaliteiten direct tot je beschikking hebt. Alles is overzichtelijk gerangschikt, zodat je snel aan de slag kunt met je LED-projecten:

* Realtime Simulatie Overzicht: Je krijgt direct een helder overzicht van de gesimuleerde LEDs. Zie in één oogopslag welke LEDs actief zijn, wat hun helderheid is (gesimuleerd via PWM, van 0 tot 255), en welk globaal patroon op dat moment actief is. Ook handige timers voor de actieve patronen zijn direct zichtbaar.

* Diverse LED Patronen: Dit is het hart van de patroongenerator. Je kiest eenvoudig uit verschillende ingebouwde patronen om je verlichting dynamisch te maken:
    * Fade In/Out: Alle LEDs kunnen langzaam faden naar een te kiezen maximale helderheid.
    * Knipperen (TV-simulatie): Een slim patroon dat het onregelmatige, flikkerende licht van een televisiescherm nabootst – een fantastisch detail voor huisjes op je modelbaan.

* Individuele LED Controle: Wil je precieze controle over elke afzonderlijke LED? Geen probleem! Je kunt de helderheid (PWM-waarde) van elke gesimuleerde LED afzonderlijk instellen door de gewenste waarde in te vullen in een tekstveld. Dit is ideaal voor het finetunen van specifieke lichtpunten zoals straatlantaarns of interieurverlichting.

* Opslaan en Laden van Instellingen: Om je workflow nog efficiënter te maken, sla je je configuraties eenvoudig op en laad je ze later weer in. Dit betekent dat je complexe patronen of individuele instellingen kunt bewaren en later weer kunt oproepen, zonder elke keer opnieuw te hoeven beginnen.

Hoe gebruik je dit script voor je modelbaan?
------------------------------------------

De kracht van deze simulatie ligt in de mogelijkheid om te experimenteren.

* Download de applicatie: De tool is beschikbaar als een Python-script (.py) en voor Windows-gebruikers ook als een uitvoerbaar bestand (.exe), zodat je direct aan de slag kunt zonder Python te hoeven installeren.
    * Download de bestanden hier: https://www.nproject.org/nl/elektronica/modelbaan-verlichting-simuleer-leds-met-de-arduino-python-tool/

* Start de applicatie:
    * Voor het .py script: Zorg dat je Python geïnstalleerd hebt op je computer (versie 3.x wordt aanbevolen). Voer het script uit via een terminal/command prompt: "Modelbaan_LED_Simulator.py".
    * Voor de windows .exe versie: Dubbelklik simpelweg op het uitvoerbare bestand.

* Experimenteer met patronen: Speel met de verschillende patroon-modi en de snelheidsinstellingen via de sliders. Zie hoe je LEDs reageren en welke effecten je kunt creëren.

* Fine-tune individuele LEDs: Vul de gewenste waarden in om de perfecte helderheid te vinden voor elk lichtpunt.

* Sla je configuratie op: Zodra je tevreden bent met een patroon of een set instellingen, sla je deze op. Dit JSON-bestand bevat alle details van je simulatie.

* Exporteer je arduino sketch die je kunt inlezen in je Arduino. (.ino bestand)

Deze simulatie tool fungeert als een digitale werkbank voor je LED-projecten. Je kunt urenlang experimenteren en optimaliseren zonder de frustratie van constant bedraden, uploaden en debuggen op je fysieke Arduino. De tool is primair gebouwd en geoptimaliseerd voor de Arduino Mega, maar de geëxporteerde configuratiebestanden zijn eenvoudig aan te passen. Dit betekent dat je de gesimuleerde PWM-waarden en timings gemakkelijk kunt vertalen naar de code voor je Arduino UNO of een andere versie van het Arduino-bord.

Over dit project en ondersteuning
---------------------------------

Deze tool is een open-source project en de code is beschikbaar op GitHub. Dit betekent dat je niet alleen kunt experimenteren met de tool, maar ook kunt bijdragen aan de ontwikkeling. We nodigen je uit om mee te denken, de code te verbeteren, of suggesties te doen voor een eventuele volgende versie.

De code is beschikbaar op GitHub: https://github.com/NProject-org/Modelbaan_LED_Simulator

Gebruik van deze tool is volledig voor eigen risico en er wordt geen ondersteuning voor geboden.

Begin vandaag nog met experimenteren!

Met vriendelijke groet,
Het team van www.NProject.org
