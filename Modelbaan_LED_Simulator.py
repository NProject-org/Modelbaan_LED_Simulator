import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import time
import random
import webbrowser

# --- ToolTip Class ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = 0
        self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.show_tip) # Show after 500ms

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show_tip(self):
        if self.tip_window or not self.text:
            return

        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 20 # Offset to the right
        y += self.widget.winfo_rooty() + self.widget.winfo_height() + 5 # Offset below

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True) # No window decorations
        self.tip_window.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(self.tip_window, text=self.text, background="#ffffe0", relief="solid", borderwidth=1,
                          font=("tahoma", "8", "normal"))
        label.pack(padx=1, pady=1)

    def hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# --- Vooraf gedefinieerde Lichtprofielen ---
# Deze dict bevat de complete configuratie voor elk lichttype.
# Let op: Alle tijden zijn hier in SECONDEN (behalpje blink_on_ms/blink_off_ms).
# De Python code converteert dit naar MILLISECONDEN voor de Arduino output.
LIGHT_PROFILES = {
    "Uitgeschakeld": {
        'min_on_s': '0', 'max_on_s': '0',
        'min_off_s': '31536000', 'max_off_s': '31536000', # 1 jaar in seconden, voorkomt 'dol' knipperen
        'fade_in': False, 'min_fade_in_s': '0', 'max_fade_in_s': '0',
        'fade_out': False, 'min_fade_out_s': '0', 'max_fade_out_s': '0',
        'var_bright': False, 'min_bright': '0', 'max_bright': '0', 'bright_interval_s': '0',
        'blinking': False, 'blink_on_ms': '0', 'blink_off_ms': '0'
    },
    "Woonkamer Licht": {
        'min_on_s': '10', 'max_on_s': '30',
        'min_off_s': '5', 'max_off_s': '15',
        'fade_in': True, 'min_fade_in_s': '1', 'max_fade_in_s': '5',
        'fade_out': True, 'min_fade_out_s': '1', 'max_fade_out_s': '4',
        'var_bright': True, 'min_bright': '100', 'max_bright': '255', 'bright_interval_s': '0', # Interval is nu 0, want helderheid verandert niet meer tijdens ON
        'blinking': False, 'blink_on_ms': '0', 'blink_off_ms': '0'
    },
    "Hal Licht": {
        'min_on_s': '3', 'max_on_s': '10',
        'min_off_s': '2', 'max_off_s': '8',
        'fade_in': False, 'min_fade_in_s': '0', 'max_fade_in_s': '0',
        'fade_out': False, 'min_fade_out_s': '0', 'max_fade_out_s': '0',
        'var_bright': False, 'min_bright': '255', 'max_bright': '255', 'bright_interval_s': '0',
        'blinking': False, 'blink_on_ms': '0', 'blink_off_ms': '0'
    },
    "TV Simulatie": {
        'min_on_s': '20', 'max_on_s': '40', # Totale 'TV aan' periode
        'min_off_s': '10', 'max_off_s': '20', # Totale 'TV uit' periode
        'fade_in': False, 'min_fade_in_s': '0', 'max_fade_in_s': '0',
        'fade_out': False, 'min_fade_out_s': '0', 'max_fade_out_s': '0',
        'var_bright': True, 'min_bright': '50', 'max_bright': '200', 'bright_interval_s': '0', # Interval niet gebruikt
        'blinking': True, 'blink_on_ms': '50', 'blink_off_ms': '150'
    },
    "Willekeurig Aan/Uit": { # Zonder fading of variabele helderheid
        'min_on_s': '5', 'max_on_s': '20',
        'min_off_s': '10', 'max_off_s': '40',
        'fade_in': False, 'min_fade_in_s': '0', 'max_fade_in_s': '0',
        'fade_out': False, 'min_fade_out_s': '0', 'max_fade_out_s': '0',
        'var_bright': False, 'min_bright': '255', 'max_bright': '255', 'bright_interval_s': '0',
        'blinking': False, 'blink_on_ms': '0', 'blink_off_ms': '0'
    },
    # Hier kun je meer profielen toevoegen, bijv. "Laslicht", "Kantoorlicht", etc.
}

# Geldige PWM-pinnen voor Arduino Mega 2560 (15 in totaal)
# Digitale pinnen met PWM-functionaliteit: 2-13, 44-46
PWM_PINS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 44, 45, 46]
# Alle digitale pinnen voor Arduino Mega 2560 (0-53) - Ter referentie
ALL_DIGITAL_PINS = list(range(0, 54))

# --- Arduino Code Generatie Functie (aangepast voor variabele helderheid) ---
def generate_arduino_code(led_configs):
    """Genereert de Arduino C++ code op basis van de opgegeven LED-configuraties."""
    arduino_code = """
// --- Configuratieparameters voor elke LED ---
// Pas deze waarden aan naar wens. Tijden zijn in milliseconden.

// Definities voor LED-modi
#define MODE_OFF          0
#define MODE_ON           1
#define MODE_FADE_IN      2
#define MODE_FADE_OUT     3
#define MODE_BLINKING     4 // Nieuwe modus: knipperen/stroboscoop

struct LedConfig {
  int pin;
  // Algemene timings
  unsigned long minOnDurationMillis;
  unsigned long maxOnDurationMillis;
  unsigned long minOffDurationMillis;
  unsigned long maxOffDurationMillis;

  // Fading instellingen
  bool fadeInEnabled;
  unsigned long minFadeInDurationMillis;
  unsigned long maxFadeInDurationMillis;
  bool fadeOutEnabled;
  unsigned long minFadeOutDurationMillis;
  unsigned long maxFadeOutDurationMillis;

  // Variabele intensiteit tijdens AAN-fase (optioneel)
  // Let op: Bij variableBrightnessEnabled wordt helderheid eenmalig gekozen bij overgang naar AAN-fase.
  // brightnessChangeIntervalMillis heeft geen effect in deze implementatie voor variabele helderheid.
  bool variableBrightnessEnabled;
  int minBrightnessDuringOn; // Tussen 0 en 255
  int maxBrightnessDuringOn; // Tussen 0 en 255
  unsigned long brightnessChangeIntervalMillis; // Deze wordt genegeerd voor variabele helderheid in de huidige implementatie

  // Knipperen/Stroboscoop instellingen (alleen voor MODE_BLINKING)
  bool blinkingEnabled;
  unsigned long blinkOnDurationMillis;  // Hoe lang de LED aan is tijdens knipperen
  unsigned long blinkOffDurationMillis; // Hoe lang de LED uit is tijdens knipperen
};

// Array van LED configuraties
LedConfig ledConfigs[] = {
"""

    for i, config in enumerate(led_configs):
        # Let op: tijden in config zijn strings (vanwege entry velden). Converteer naar float en dan naar int ms.
        arduino_code += f"""  // LED {i + 1}
  {{
    {config['pin']},                       // Pin
    {int(float(config['min_on_s']) * 1000)}, {int(float(config['max_on_s']) * 1000)},            // minOnDurationMillis, maxOnDurationMillis
    {int(float(config['min_off_s']) * 1000)}, {int(float(config['max_off_s']) * 1000)},            // minOffDurationMillis, maxOffDurationMillis
    {str(config['fade_in']).lower()}, {int(float(config['min_fade_in_s']) * 1000)}, {int(float(config['max_fade_in_s']) * 1000)},        // fadeInEnabled, minFadeInDurationMillis, maxFadeInDurationMillis
    {str(config['fade_out']).lower()}, {int(float(config['min_fade_out_s']) * 1000)}, {int(float(config['max_fade_out_s']) * 1000)},        // fadeOutEnabled, minFadeOutDurationMillis, maxFadeOutDurationMillis
    {str(config['var_bright']).lower()}, {config['min_bright']}, {config['max_bright']},          // variableBrightnessEnabled, minBrightnessDuringOn, maxBrightnessDuringOn
    {int(float(config['bright_interval_s']) * 1000)},                    // brightnessChangeIntervalMillis (deze wordt genegeerd voor var_bright)
    {str(config['blinking']).lower()}, {int(config['blink_on_ms'])}, {int(config['blink_off_ms'])}              // blinkingEnabled, blinkOnDurationMillis, blinkOffDurationMillis
  }},
"""
    # Verwijder de laatste komma en voeg de afsluitende accolades toe
    arduino_code = arduino_code.rstrip(',\n') + "\n};"

    arduino_code += f"""

const int NUM_LEDS = sizeof(ledConfigs) / sizeof(ledConfigs[0]);

// --- Variabelen voor elke LED (worden door het programma gebruikt) ---
struct LedState {{
  unsigned long lastToggleTime;       // Tijd van laatste aan/uit schakeling of moduswissel
  unsigned long currentDuration;      // De willekeurig bepaalde duur voor de huidige fase (aan/uit/fade)
  int currentMode;                    // Huidige modus van de LED (OFF, ON, FADE_IN, FADE_OUT, BLINKING)
  int currentBrightness;              // Huidige helderheid voor PWM (0-255)
  unsigned long fadeStartTime;        // Starttijd van de fade-animatie
  unsigned long fadeDuration;         // Willekeurig bepaalde duur van de fade
  int fadeTargetBrightness;           // De doelhelderheid voor een fade-in animatie (eenmalig gekozen)
  unsigned long lastBrightnessChangeTime; // Voor variabele helderheid (nu alleen bij overgang naar AAN)
  unsigned long lastBlinkToggleTime;  // Voor knipperende modus
  bool blinkState;                    // Huidige knipperstatus (aan/uit)
}};

LedState ledStates[NUM_LEDS];

// --- Setup functie (eenmalig uitgevoerd bij opstarten) ---
void setup() {{
  Serial.begin(9600); // Start seriële communicatie voor debugging

  // Gebruik een analoge pin (A0) om een willekeurige seed te genereren voor random functies.
  // Zorg dat A0 niet is aangesloten, anders is de willekeurigheid minder.
  randomSeed(analogRead(A0));

  for (int i = 0; i < NUM_LEDS; i++) {{
    pinMode(ledConfigs[i].pin, OUTPUT);
    analogWrite(ledConfigs[i].pin, 0); // Begin met alle LED's uit
    ledStates[i].lastToggleTime = millis();
    ledStates[i].currentMode = MODE_OFF; // Begin in UIT-stand
    ledStates[i].currentBrightness = 0;
    ledStates[i].currentDuration = random(ledConfigs[i].minOffDurationMillis, ledConfigs[i].maxOffDurationMillis + 1); // Eerste off duration
    ledStates[i].blinkState = false; // Begin knipperen in uit-stand
    ledStates[i].fadeTargetBrightness = 0; // Initialize
  }}
}}

// --- Loop functie (continu uitgevoerd) ---
void loop() {{
  unsigned long currentTime = millis(); // Haal de huidige tijd op in milliseconden

  for (int i = 0; i < NUM_LEDS; i++) {{
    switch (ledStates[i].currentMode) {{
      case MODE_OFF:
        if (currentTime - ledStates[i].lastToggleTime >= ledStates[i].currentDuration) {{
          if (ledConfigs[i].fadeInEnabled) {{
            ledStates[i].currentMode = MODE_FADE_IN;
            ledStates[i].fadeStartTime = currentTime;
            ledStates[i].fadeDuration = random(ledConfigs[i].minFadeInDurationMillis, ledConfigs[i].maxFadeInDurationMillis + 1);
            // Bepaal de eenmalige doelhelderheid voor fade-in
            ledStates[i].fadeTargetBrightness = ledConfigs[i].variableBrightnessEnabled ? \
                                                random(ledConfigs[i].minBrightnessDuringOn, ledConfigs[i].maxBrightnessDuringOn + 1) : 255;
            // Begin de fade vanaf 0 helderheid
            ledStates[i].currentBrightness = 0; 
            analogWrite(ledConfigs[i].pin, ledStates[i].currentBrightness);
            Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.print(" start FADE_IN naar "); Serial.println(ledStates[i].fadeTargetBrightness);
          }} else {{
            if (ledConfigs[i].blinkingEnabled) {{
              ledStates[i].currentMode = MODE_BLINKING;
              ledStates[i].lastToggleTime = currentTime;
              ledStates[i].blinkState = true; // Begin met aan
              // Set initial brightness for blinking (using variable brightness range)
              ledStates[i].currentBrightness = random(ledConfigs[i].minBrightnessDuringOn, ledConfigs[i].maxBrightnessDuringOn + 1);
              analogWrite(ledConfigs[i].pin, ledStates[i].currentBrightness);
              Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.println(" start BLINKING");
            }} else {{
              ledStates[i].currentMode = MODE_ON;
              ledStates[i].lastToggleTime = currentTime;
              // Stel de helderheid in als variabele helderheid is ingeschakeld, anders gewoon 255
              ledStates[i].currentBrightness = ledConfigs[i].variableBrightnessEnabled ? \
                                                random(ledConfigs[i].minBrightnessDuringOn, ledConfigs[i].maxBrightnessDuringOn + 1) : 255;
              analogWrite(ledConfigs[i].pin, ledStates[i].currentBrightness);
              ledStates[i].currentDuration = random(ledConfigs[i].minOnDurationMillis, ledConfigs[i].maxOnDurationMillis + 1);
              Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.println(" DIRECT AAN");
            }}
          }}
        }}
        break;

      case MODE_ON:
        if (currentTime - ledStates[i].lastToggleTime >= ledStates[i].currentDuration) {{
          if (ledConfigs[i].fadeOutEnabled) {{
            ledStates[i].currentMode = MODE_FADE_OUT;
            ledStates[i].fadeStartTime = currentTime;
            ledStates[i].fadeDuration = random(ledConfigs[i].minFadeOutDurationMillis, ledConfigs[i].maxFadeOutDurationMillis + 1);
            Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.println(" start FADE_OUT");
          }} else {{
            ledStates[i].currentMode = MODE_OFF;
            ledStates[i].lastToggleTime = currentTime;
            analogWrite(ledConfigs[i].pin, 0); // Zorg dat de LED uit is
            ledStates[i].currentDuration = random(ledConfigs[i].minOffDurationMillis, ledConfigs[i].maxOffDurationMillis + 1);
            Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.println(" DIRECT UIT");
          }}
        }}
        break;

      case MODE_FADE_IN:
        if (currentTime - ledStates[i].fadeStartTime < ledStates[i].fadeDuration) {{
          unsigned long elapsedTime = currentTime - ledStates[i].fadeStartTime;
          // Map current brightness based on elapsed time to the target brightness (eenmalig gekozen)
          // Fade van 0 naar fadeTargetBrightness
          ledStates[i].currentBrightness = map(elapsedTime, 0, ledStates[i].fadeDuration, 0, ledStates[i].fadeTargetBrightness);
          analogWrite(ledConfigs[i].pin, ledStates[i].currentBrightness);
        }} else {{
          ledStates[i].currentMode = MODE_ON;
          ledStates[i].lastToggleTime = currentTime;
          // Zorg dat de LED op de definitieve helderheid staat (gelijk aan fadeTargetBrightness)
          ledStates[i].currentBrightness = ledStates[i].fadeTargetBrightness; 
          analogWrite(ledConfigs[i].pin, ledStates[i].currentBrightness); 
          ledStates[i].currentDuration = random(ledConfigs[i].minOnDurationMillis, ledConfigs[i].maxOnDurationMillis + 1);
          Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.print(" einde FADE_IN, nu AAN op helderheid "); Serial.println(ledStates[i].currentBrightness);
        }}
        break;

      case MODE_FADE_OUT:
        if (currentTime - ledStates[i].fadeStartTime < ledStates[i].fadeDuration) {{
          unsigned long elapsedTime = currentTime - ledStates[i].fadeStartTime;
          // Fade from current brightness (or 255 if not variable) down to 0
          int startBrightness = ledStates[i].currentBrightness; // Use current brightness as starting point
          ledStates[i].currentBrightness = map(elapsedTime, 0, ledStates[i].fadeDuration, startBrightness, 0);
          analogWrite(ledConfigs[i].pin, ledStates[i].currentBrightness);
        }} else {{
          ledStates[i].currentMode = MODE_OFF;
          ledStates[i].lastToggleTime = currentTime;
          analogWrite(ledConfigs[i].pin, 0); // Zorg dat de LED volledig uit is
          ledStates[i].currentDuration = random(ledConfigs[i].minOffDurationMillis, ledConfigs[i].maxOffDurationMillis + 1);
          Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.println(" einde FADE_OUT, nu UIT");
        }}
        break;

      case MODE_BLINKING:
        // Als de hoofdtijd voor 'TV aan' is verstreken, ga dan naar de uit-stand
        if (currentTime - ledStates[i].lastToggleTime >= ledStates[i].currentDuration) {{
            ledStates[i].currentMode = MODE_OFF;
            ledStates[i].lastToggleTime = currentTime;
            analogWrite(ledConfigs[i].pin, 0); // Zet LED uit
            ledStates[i].currentDuration = random(ledConfigs[i].minOffDurationMillis, ledConfigs[i].maxOffDurationMillis + 1);
            Serial.print("LED "); Serial.print(ledConfigs[i].pin); Serial.println(" einde BLINKING periode, nu UIT");
            break; // Spring uit deze case om direct naar de volgende status te gaan
        }}

        // Knipperlogica binnen de BLINKING periode
        if (ledStates[i].blinkState == true) {{ // LED is momenteel aan in knipper-modus
          if (currentTime - ledStates[i].lastBlinkToggleTime >= ledConfigs[i].blinkOnDurationMillis) {{
            analogWrite(ledConfigs[i].pin, 0); // Zet LED uit
            ledStates[i].blinkState = false;
            ledStates[i].lastBlinkToggleTime = currentTime;
          }}
        }} else {{ // LED is momenteel uit in knipper-modus
          if (currentTime - ledStates[i].lastBlinkToggleTime >= ledConfigs[i].blinkOffDurationMillis) {{
            // Zet LED aan met een willekeurige helderheid voor een realistischer TV-effect
            analogWrite(ledConfigs[i].pin, random(ledConfigs[i].minBrightnessDuringOn, ledConfigs[i].maxBrightnessDuringOn + 1));
            ledStates[i].blinkState = true;
            ledStates[i].lastBlinkToggleTime = currentTime;
          }}
        }}
        break;
    }}
  }}
}}
"""
    return arduino_code

# --- Simulatie Logica ---
class LedSimulator:
    MODE_OFF = 0
    MODE_ON = 1
    MODE_FADE_IN = 2
    MODE_FADE_OUT = 3
    MODE_BLINKING = 4

    MODE_NAMES = { # Mapping van modus-constanten naar leesbare namen
        0: "UIT",
        1: "AAN",
        2: "FADE IN",
        3: "FADE UIT",
        4: "KNIPPERT"
    }

    def __init__(self, config):
        self.config = config # Dit is de gevalideerde config dict
        
        # Initialiseer random_state hier, voordat het wordt gebruikt
        self.random_state = {'seed': time.time()} # Simpele manier om random te initialiseren

        # Simulatie status variabelen
        self.current_brightness = 0
        self.current_mode = self.MODE_OFF
        self.last_toggle_time = 0
        # Nieuwe variabele voor de starttijd van de huidige aan/uit/fade/blink-fase
        self.last_phase_start_time = 0 
        
        # Gebruik de correcte sleutels en zorg dat ze naar int worden omgezet
        # Zorg dat de standaard waarden van config.get() numeriek zijn (0)
        # Gebruik float() voor conversie naar milliseconden
        # Belangrijk: Voor "Uitgeschakeld" is min_off_s/max_off_s nu een groot getal
        self.current_duration = self._get_random_duration(float(self.config.get('min_off_s', '0')) * 1000, float(self.config.get('max_off_s', '0')) * 1000) # Initial off duration
        self.fade_start_time = 0
        self.fade_duration = 0
        self.fade_in_target_brightness = 0 # Nieuw: Doelhelderheid voor fade-in
        # self.last_brightness_change_time = 0 # Niet meer nodig voor variabele helderheid
        self.last_blink_toggle_time = 0
        self.blink_state = False # True = AAN, False = UIT tijdens knipperen

    
    def _get_random_duration(self, min_ms, max_ms):
        """Simuleert Arduino's random()."""
        # Python's random is anders dan Arduino's, maar voor simulatie voldoet dit.
        # We gebruiken een pseudo-random seed om de sequentie te herhalen voor debugging.
        
        # Gebruik self.random_state['seed'] voor de seed
        random.seed(self.random_state['seed'] + time.time()) # Beetje extra randomheid per oproep
        # Zorg ervoor dat min_ms <= max_ms, anders kan random.randint falen
        if min_ms > max_ms:
            # Als min_ms groter is dan max_ms, geeft dit een probleem.
            # We kunnen ervoor kiezen om de waarden om te draaien of een default te geven.
            # Voor nu geven we min_ms terug als de enige optie
            return int(min_ms) 
        return random.randint(int(min_ms), int(max_ms))

    def _map_range(self, x, in_min, in_max, out_min, out_max):
        """Simuleert de Arduino map() functie."""
        if in_min == in_max: # Voorkom delen door nul
            return out_min 
        return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    def update(self, current_time_ms):
        # Converteer seconden van config naar milliseconden voor simulatie
        # Zorg ervoor dat alle numerieke waarden integers zijn en booleans booleans
        # Gebruik .get(key, '0') om lege strings te vermijden die ValueError geven bij int()
        cfg = {}
        for k, v in self.config.items():
            if '_s' in k and not isinstance(v, bool):
                # Speciaal geval voor '0' string: converteer naar 0.0, anders float
                cfg[k] = float(v) * 1000 if str(v).replace('.', '', 1).isdigit() else 0 # Converteer naar float, dan milliseconden, default 0
            elif k.endswith('_ms') or k.endswith('_bright'):
                cfg[k] = int(v) if str(v).isdigit() else 0 # Converteer naar int, default 0
            else:
                cfg[k] = v
        
        # Converteer booleaanse waarden die mogelijk als strings zijn opgeslagen naar echte booleans
        cfg['fadeInEnabled'] = bool(self.config.get('fade_in', False))
        cfg['fadeOutEnabled'] = bool(self.config.get('fade_out', False))
        cfg['variableBrightnessEnabled'] = bool(self.config.get('var_bright', False))
        cfg['blinkingEnabled'] = bool(self.config.get('blinking', False))

        # Helderheid min/max zijn al nummers na de eerste conversie, geen verdere conversie nodig
        cfg['minBrightnessDuringOn'] = int(self.config.get('min_bright', 0))
        cfg['maxBrightnessDuringOn'] = int(self.config.get('max_bright', 255))
        
        # Timings voor knipperen, moeten als ms worden doorgegeven (al omgezet via de loop hierboven)
        # Gebruik .get(key, 0) voor de zekerheid als de config geen string heeft
        cfg['blinkOnDurationMillis'] = int(self.config.get('blink_on_ms', 0))
        cfg['blinkOffDurationMillis'] = int(self.config.get('blink_off_ms', 0))

        # Logic from Arduino's loop() function
        previous_mode = self.current_mode # Sla de vorige modus op voor detectie van verandering

        if self.current_mode == self.MODE_OFF:
            if current_time_ms - self.last_toggle_time >= self.current_duration:
                # Als het "Uitgeschakeld" profiel is gekozen, moet de LED uit blijven.
                if (float(self.config.get('min_on_s', '0')) == 0 and float(self.config.get('max_on_s', '0')) == 0) and \
                   (float(self.config.get('min_off_s', '0')) > 0 or float(self.config.get('max_off_s', '0')) > 0): 
                    self.current_mode = self.MODE_OFF
                    self.last_toggle_time = current_time_ms
                    self.current_brightness = 0
                    self.current_duration = self._get_random_duration(cfg['min_off_s'], cfg['max_off_s'])
                    self.last_phase_start_time = self.last_toggle_time # Update phase start time
                    return self.current_brightness, self.current_mode, self.current_duration, self.last_phase_start_time

                if cfg['fadeInEnabled']:
                    self.current_mode = self.MODE_FADE_IN
                    self.last_phase_start_time = current_time_ms # Start nieuwe fase
                    self.fade_start_time = current_time_ms
                    self.fade_duration = self._get_random_duration(cfg['min_fade_in_s'], cfg['max_fade_in_s'])
                    self.current_brightness = 0 # Start fading from off
                    # NIEUW: Bepaal de eenmalige doelhelderheid voor de fade-in
                    self.fade_in_target_brightness = self._get_random_duration(cfg['minBrightnessDuringOn'], cfg['maxBrightnessDuringOn']) if cfg['variableBrightnessEnabled'] else 255
                else:
                    if cfg['blinkingEnabled']:
                        self.current_mode = self.MODE_BLINKING
                        self.last_phase_start_time = current_time_ms # Start nieuwe fase
                        self.last_toggle_time = current_time_ms # Start de hoofdtimer voor blinking
                        # min_on_s/max_on_s bepalen de totale duur van de BLINKING periode
                        self.current_duration = self._get_random_duration(cfg['min_on_s'], cfg['max_on_s']) 
                        self.last_blink_toggle_time = current_time_ms
                        self.blink_state = True # Begin met aan
                        self.current_brightness = self._get_random_duration(cfg['minBrightnessDuringOn'], cfg['maxBrightnessDuringOn'])
                    else:
                        self.current_mode = self.MODE_ON
                        self.last_phase_start_time = current_time_ms # Start nieuwe fase
                        self.last_toggle_time = current_time_ms
                        # Stel de helderheid in als variabele helderheid is ingeschakeld, anders gewoon 255
                        self.current_brightness = self._get_random_duration(cfg['minBrightnessDuringOn'], cfg['maxBrightnessDuringOn']) if cfg['variableBrightnessEnabled'] else 255
                        self.current_duration = self._get_random_duration(cfg['min_on_s'], cfg['max_on_s'])

        elif self.current_mode == self.MODE_ON:
            if current_time_ms - self.last_toggle_time >= self.current_duration:
                if cfg['fadeOutEnabled']:
                    self.current_mode = self.MODE_FADE_OUT
                    self.last_phase_start_time = current_time_ms # Start nieuwe fase
                    self.fade_start_time = current_time_ms
                    self.fade_duration = self._get_random_duration(cfg['min_fade_out_s'], cfg['max_fade_out_s'])
                else:
                    self.current_mode = self.MODE_OFF
                    self.last_phase_start_time = current_time_ms # Start nieuwe fase
                    self.last_toggle_time = current_time_ms
                    self.current_brightness = 0
                    self.current_duration = self._get_random_duration(cfg['min_off_s'], cfg['max_off_s'])

        elif self.current_mode == self.MODE_FADE_IN:
            if current_time_ms - self.fade_start_time < self.fade_duration:
                elapsed_time = current_time_ms - self.fade_start_time
                
                # Gebruik de _map_range functie die de Arduino map() nabootst
                self.current_brightness = self._map_range(elapsed_time, 0, self.fade_duration, 0, self.fade_in_target_brightness)
                
            else:
                self.current_mode = self.MODE_ON
                self.last_phase_start_time = current_time_ms # Start nieuwe fase
                self.last_toggle_time = current_time_ms
                # Zorg dat de LED op de definitieve helderheid staat (gelijk aan fade_in_target_brightness)
                self.current_brightness = self.fade_in_target_brightness
                self.current_duration = self._get_random_duration(cfg['min_on_s'], cfg['max_on_s'])

        elif self.current_mode == self.MODE_FADE_OUT:
            if current_time_ms - self.fade_start_time < self.fade_duration:
                elapsed_time = current_time_ms - self.fade_start_time
                # Fade from the brightness the LED was at when fade_out started
                start_brightness_for_fade_out = self.current_brightness # Use the current brightness
                # Gebruik de _map_range functie die de Arduino map() nabootst
                self.current_brightness = self._map_range(elapsed_time, 0, self.fade_duration, start_brightness_for_fade_out, 0)
            else:
                self.current_mode = self.MODE_OFF
                self.last_phase_start_time = current_time_ms # Start nieuwe fase
                self.last_toggle_time = current_time_ms
                self.current_brightness = 0
                self.current_duration = self._get_random_duration(cfg['min_off_s'], cfg['max_off_s'])
        
        elif self.current_mode == self.MODE_BLINKING:
            # Als de hoofdtijd voor 'TV aan' is verstreken, ga dan naar de uit-stand
            if current_time_ms - self.last_toggle_time >= self.current_duration:
                self.current_mode = self.MODE_OFF
                self.last_phase_start_time = current_time_ms # Start nieuwe fase
                self.last_toggle_time = current_time_ms
                # analogWrite(self.config['pin'], 0); # Zet LED uit (Simulatie, geen echte schrijf)
                self.current_brightness = 0
                self.current_duration = self._get_random_duration(cfg['min_off_s'], cfg['max_off_s'])
                self.blink_state = False # Reset knipperstatus
            else:
                # Knipperlogica binnen de BLINKING periode
                if self.blink_state: # LED is momenteel aan
                    if current_time_ms - self.last_blink_toggle_time >= cfg['blinkOnDurationMillis']:
                        self.current_brightness = 0 # Zet LED uit
                        self.blink_state = False
                        self.last_blink_toggle_time = current_time_ms
                else: # LED is momenteel uit
                    if current_time_ms - self.last_blink_toggle_time >= cfg['blinkOffDurationMillis']:
                        # Zet LED aan met een willekeurige helderheid voor een realistischer TV-effect
                        self.current_brightness = self._get_random_duration(cfg['minBrightnessDuringOn'], cfg['maxBrightnessDuringOn'])
                        self.blink_state = True
                        self.last_blink_toggle_time = current_time_ms

        # Zorg dat helderheid binnen de grenzen blijft
        self.current_brightness = max(0, min(255, self.current_brightness))

        # Update last_phase_start_time als de modus is veranderd
        if self.current_mode != previous_mode:
            self.last_phase_start_time = current_time_ms

        # Voor BLINKING, current_duration is de totale duur van de BLINKING-fase,
        # en last_toggle_time is de starttijd van die fase. Dit is consistent.
        # De interne blink_on_ms en blink_off_ms worden alleen gebruikt binnen de BLINKING modus zelf.

        return self.current_brightness, self.current_mode, self.current_duration, self.last_phase_start_time # Return mode and current_duration


    def reset(self):
        self.current_brightness = 0
        self.current_mode = self.MODE_OFF
        self.last_toggle_time = 0
        self.last_phase_start_time = 0 # Reset ook deze bij een volledige reset
        # Genereer een nieuwe initiële duur voor de off-periode bij reset
        self.current_duration = self._get_random_duration(
            float(self.config.get('min_off_s', '0')) * 1000, # Gebruik '0' als default
            float(self.config.get('max_off_s', '0')) * 1000
        )
        self.fade_start_time = 0
        self.fade_duration = 0
        self.fade_in_target_brightness = 0 # Reset ook deze
        # self.last_brightness_change_time = 0 # Niet meer nodig voor variabele helderheid
        self.last_blink_toggle_time = 0
        self.blink_state = False
        self.random_state['seed'] = time.time() # Nieuwe seed voor nieuwe random reeks


class LedConfiguratorApp:

    # --- PLAATS DE open_nproject_url FUNCTIE HIER, VOOR DE __init__ METHODE ---
    def open_nproject_url(self, event): # 'event' is nodig voor bind
        """Opent de NProject.org website in de standaard webbrowser."""
        webbrowser.open_new("https://www.nproject.org") # Zorg voor 'https://'
    # --- EINDE open_nproject_url FUNCTIE ---

    def __init__(self, master):
        # Maximum aantal LEDs is nu gebaseerd op het aantal PWM-pinnen voor de Mega
        self.master = master
        master.title("Arduino LED Configuratie Generator (Modelspoor)")
        self.num_leds = len(PWM_PINS) # Maximaal 15 LEDs

# --- AANGEPASTE CODE HIER: tk.Text widget voor aanklikbare link ---
        # Gebruik een tk.Text widget in plaats van ttk.Label
        self.website_text_widget = tk.Text(master, height=1, borderwidth=0, relief="flat", wrap="none",
                                           bg=master.cget('bg'),  # Pas de achtergrond aan het venster
                                           font=('Arial', 9, 'italic'),
                                           state="disabled") # Standaard disabled zodat gebruiker niet kan typen
        self.website_text_widget.pack(pady=(5, 0))

        # Voeg de tekst in
        self.website_text_widget.config(state="normal") # Maak tijdelijk enable om tekst in te voegen
        self.website_text_widget.insert(tk.END, "Deze tool is met passie ontwikkeld door ")

        # Voeg de aanklikbare URL in met een tag
        self.website_text_widget.insert(tk.END, "www.NProject.org", "nproject_link")
        self.website_text_widget.config(state="disabled") # Zet weer op disabled

        # Configureer de 'nproject_link' tag
        self.website_text_widget.tag_config("nproject_link",
                                             foreground="blue",
                                             underline=True)

        # Bind de tag aan het klik-event
        self.website_text_widget.tag_bind("nproject_link", "<Button-1>", self.open_nproject_url)
        self.website_text_widget.tag_bind("nproject_link", "<Enter>", lambda e: self.website_text_widget.config(cursor="hand2"))
        self.website_text_widget.tag_bind("nproject_link", "<Leave>", lambda e: self.website_text_widget.config(cursor=""))
        # --- EINDE AANGEPASTE CODE ---



        self.led_data = []  # Lijst van dictionaries, elk met 'vars_snapshot' voor een LED
        self.current_led_index = None # Houdt bij welke LED momenteel geselecteerd is

        self.simulator = None # Instance van LedSimulator voor de geselecteerde LED
        self.simulation_running = False
        self.simulation_start_time = 0
        self.simulation_speed_factor = 1.0 # 1.0 = real-time, 10.0 = 10x sneller
        self.simulation_update_interval_ms = 50 # Update canvas elke 50ms (simulatie stappen zijn kleiner)

        # Initialiseer deze attributen naar None VOORDAT create_main_layout wordt aangeroepen
        self.speed_label = None
        self.on_timer_label = None
        self.off_timer_label = None
        self.mode_label = None # NIEUW: label voor de modus
        self._simulation_job = None # Initialize to None for the after_cancel check

        self.create_main_layout()
        self.load_default_configs() # Laad initiële data en vul de LED-lijst

    def create_main_layout(self,):
        # Hoofdframe met drie kolommen: LED-lijst, Bewerken, Visualisatie
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Linkerkant: Lijst van LEDs
        left_frame = ttk.Frame(main_frame, width=150)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False) # Voorkom dat dit frame krimpt

        ttk.Label(left_frame, text="Selecteer LED:", font=('Arial', 10, 'bold')).pack(pady=5)

        # Scrollbare lijstbox voor LEDs
        self.led_list_frame = ttk.Frame(left_frame)
        self.led_list_frame.pack(fill="both", expand=True)

        self.led_list_canvas = tk.Canvas(self.led_list_frame)
        self.led_list_canvas.pack(side="left", fill="both", expand=True)

        self.led_list_scrollbar = ttk.Scrollbar(self.led_list_frame, orient="vertical", command=self.led_list_canvas.yview)
        self.led_list_scrollbar.pack(side="right", fill="y")

        self.led_list_canvas.configure(yscrollcommand=self.led_list_scrollbar.set)
        self.led_list_canvas.bind('<Configure>', lambda e: self.led_list_canvas.configure(scrollregion=self.led_list_canvas.bbox("all")))

        self.led_list_inner_frame = ttk.Frame(self.led_list_canvas)
        self.led_list_canvas.create_window((0, 0), window=self.led_list_inner_frame, anchor="nw")

        self.led_buttons = [] # Lijst om knoppen voor elke LED bij te houden
        for i in range(self.num_leds):
            btn = ttk.Button(self.led_list_inner_frame, text=f"LED {i+1}", command=lambda idx=i: self.select_led(idx))
            btn.pack(fill="x", pady=1)
            self.led_buttons.append(btn)

        # Midden: Bewerking van geselecteerde LED
        self.edit_frame = ttk.Frame(main_frame)
        self.edit_frame.pack(side="left", fill="both", expand=True)

        self.create_edit_panel(self.edit_frame) # Maak het bewerkingspaneel aan
        
        # Rechterkant: Visualisatie
        self.visual_frame = ttk.Frame(main_frame, width=250)
        self.visual_frame.pack(side="left", fill="both", expand=False, padx=(10, 0)) # Fixed width for visualization
        self.visual_frame.pack_propagate(False) # Voorkom dat dit frame krimpt

        ttk.Label(self.visual_frame, text="LED Simulatie:", font=('Arial', 10, 'bold')).pack(pady=5)
        
        self.sim_canvas = tk.Canvas(self.visual_frame, width=200, height=200, bg="darkgray", relief="sunken", borderwidth=2)
        self.sim_canvas.pack(pady=5)
        
        # LED visualisatie cirkel
        self.sim_led_circle = self.sim_canvas.create_oval(50, 50, 150, 150, fill="black", outline="gray", width=2)
        self.sim_led_label = self.sim_canvas.create_text(100, 10, text="LED X", fill="white")

        # NIEUW: Modus weergave
        self.mode_label = ttk.Label(self.visual_frame, text="Modus: UIT", font=('Arial', 10, 'bold'))
        self.mode_label.pack(pady=(5, 2))

        # Nieuwe labels voor de timers onder de simulatie-LED
        self.on_timer_label = ttk.Label(self.visual_frame, text="Aan: 0.0s / 0.0s", font=('Arial', 9))
        self.on_timer_label.pack(pady=(0, 2))
        self.off_timer_label = ttk.Label(self.visual_frame, text="Uit: 0.0s / 0.0s", font=('Arial', 9))
        self.off_timer_label.pack(pady=(0, 5))

        # Simulatie controles
        sim_controls_frame = ttk.Frame(self.visual_frame)
        sim_controls_frame.pack(pady=5)

        self.start_sim_button = ttk.Button(sim_controls_frame, text="Start Simulatie", command=self.start_simulation)
        self.start_sim_button.pack(side=tk.LEFT, padx=2)
        self.pause_sim_button = ttk.Button(sim_controls_frame, text="Pauzeer", command=self.pause_simulation, state="disabled")
        self.pause_sim_button.pack(side=tk.LEFT, padx=2)
        self.reset_sim_button = ttk.Button(sim_controls_frame, text="Reset", command=self.reset_simulation, state="disabled")
        self.reset_sim_button.pack(side=tk.LEFT, padx=2)

        ttk.Label(sim_controls_frame, text="Snelheid (x):").pack(side=tk.LEFT, padx=(10,2))
        
        # Nu is speed_label hier geïnitialiseerd VOORDAT de slider wordt aangemaakt
        self.speed_label = ttk.Label(sim_controls_frame, text=f"{self.simulation_speed_factor:.1f}x")
        self.speed_label.pack(side=tk.LEFT, padx=2)

        self.speed_slider = ttk.Scale(sim_controls_frame, from_=0.1, to_=10.0, orient="horizontal", command=self.set_simulation_speed)
        self.speed_slider.set(self.simulation_speed_factor)
        self.speed_slider.pack(side=tk.LEFT, padx=2)
        

        # Knoppen onderaan (blijven onderaan het hoofdscherm)
        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10)

        generate_button = ttk.Button(button_frame, text="Genereer Arduino Code", command=self.generate_code_action)
        generate_button.pack(side=tk.LEFT, padx=5)

        save_button = ttk.Button(button_frame, text="Sla Configuraties Op", command=self.save_configs)
        save_button.pack(side=tk.LEFT, padx=5)

        load_button = ttk.Button(button_frame, text="Laad Configuraties", command=self.load_configs)
        load_button.pack(side=tk.LEFT, padx=5)

    def create_edit_panel(self, parent_frame):
        """Maakt de invoervelden en labels voor één LED-configuratie aan."""
        # We maken de widgets hier eenmalig aan, en vullen ze later met data
        self.current_led_vars = {}
        self.current_led_controls = {}
        
        # De layout voor het bewerkingspaneel met helpteksten
        layout = [
            ("LED Nummer:", None, 'label', 1, "Het nummer van de LED die wordt geconfigureerd."), 
            ("Pin:", 'pin', 'entry', 1, "De Arduino PWM pin waar de LED op is aangesloten. Geldige pinnen zijn: 2-13, 44-46."),
            ("Licht Type:", 'light_type', 'dropdown', 1, "Kies een vooraf gedefinieerd lichtprofiel om snel instellingen toe te passen."),
            
            ("Algemene Tijden:", None, 'header', 4, None),
            ("Min Aan (s):", 'min_on_s', 'entry', 1, "De minimale duur dat de LED aan is (in seconden)."),
            ("Max Aan (s):", 'max_on_s', 'entry', 1, "De maximale duur dat de LED aan is (in seconden). Een willekeurige duur binnen deze range wordt gekozen."),
            ("Min Uit (s):", 'min_off_s', 'entry', 1, "De minimale duur dat de LED uit is (in seconden)."),
            ("Max Uit (s):", 'max_off_s', 'entry', 1, "De maximale duur dat de LED uit is (in seconden). Een willekeurige duur binnen deze range wordt gekozen."),

            ("Fading Instellingen:", None, 'header', 6, None),
            ("Fade In?", 'fade_in', 'checkbox', 1, "Schakel fading in bij het aangaan van de LED."),
            ("Min FI (s):", 'min_fade_in_s', 'entry', 1, "De minimale duur van de 'fade-in' animatie (in seconden)."),
            ("Max FI (s):", 'max_fade_in_s', 'entry', 1, "De maximale duur van de 'fade-in' animatie (in seconden)."),
            ("Fade Out?", 'fade_out', 'checkbox', 1, "Schakel fading in bij het uitgaan van de LED."),
            ("Min FO (s):", 'min_fade_out_s', 'entry', 1, "De minimale duur van de 'fade-out' animatie (in seconden)."),
            ("Max FO (s):", 'max_fade_out_s', 'entry', 1, "De maximale duur van de 'fade-out' animatie (in seconden)."),

            ("Variabele Helderheid:", None, 'header', 4, None),
            ("Var Helder?", 'var_bright', 'checkbox', 1, "Schakel variabele helderheid in. De LED kiest een helderheid binnen de opgegeven min/max bij het aangaan."),
            ("Min H:", 'min_bright', 'entry', 1, "De minimale helderheid van de LED (0-255)."),
            ("Max H:", 'max_bright', 'entry', 1, "De maximale helderheid van de LED (0-255)."),
            ("Interval (s):", 'bright_interval_s', 'entry', 1, "Deze instelling heeft **geen effect** meer op variabele helderheid; de helderheid wordt eenmalig bepaald bij de overgang naar de AAN-fase."), # Updated helptext
            
            ("Knipperen / Stroboscoop:", None, 'header', 3, None),
            ("Knipperen?", 'blinking', 'checkbox', 1, "Schakel knipperen/stroboscoop-effect in (zoals bij een TV-simulatie)."),
            ("Knipper Aan (ms):", 'blink_on_ms', 'entry', 1, "De duur dat de LED aan is tijdens een knippercyclus (in milliseconden)."),
            ("Knipper Uit (ms):", 'blink_off_ms', 'entry', 1, "De duur dat de LED uit is tijdens een knippercyclus (in milliseconden)."),
        ]
        
        row_idx = 0
        self.led_number_label = ttk.Label(parent_frame, text="Geen LED Geselecteerd", font=('Arial', 12, 'bold'))
        self.led_number_label.grid(row=row_idx, column=0, columnspan=5, padx=5, pady=10, sticky="w")
        ToolTip(self.led_number_label, "Selecteer een LED uit de lijst aan de linkerkant om deze te configureren.")
        row_idx += 1

        for label_text, var_key, widget_type, span, help_text in layout[1:]: # Skip the first LED Number label from layout as it's handled above
            if widget_type == 'header':
                ttk.Separator(parent_frame, orient="horizontal").grid(row=row_idx, column=0, columnspan=5, sticky="ew", pady=5)
                row_idx += 1
                header_label = ttk.Label(parent_frame, text=label_text, font=('Arial', 10, 'bold'))
                header_label.grid(row=row_idx, column=0, columnspan=5, padx=5, pady=2, sticky="w")
                # Geen tooltip op headers, want die zijn vaak al duidelijk
                row_idx += 1
            else:
                label = ttk.Label(parent_frame, text=label_text)
                label.grid(row=row_idx, column=0, padx=5, pady=2, sticky="w")
                
                widget = None
                if widget_type == 'entry':
                    var = tk.StringVar()
                    entry = ttk.Entry(parent_frame, textvariable=var, width=10)
                    entry.grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
                    widget = entry
                elif widget_type == 'dropdown':
                    var = tk.StringVar()
                    dropdown = ttk.Combobox(parent_frame, textvariable=var,
                                            values=list(LIGHT_PROFILES.keys()), state="readonly", width=18)
                    dropdown.grid(row=row_idx, column=1, padx=5, pady=2, sticky="ew")
                    widget = dropdown
                elif widget_type == 'checkbox':
                    var = tk.BooleanVar()
                    checkbox = ttk.Checkbutton(parent_frame, variable=var)
                    checkbox.grid(row=row_idx, column=1, padx=5, pady=2, sticky="w")
                    widget = checkbox
                
                if var_key:
                    self.current_led_vars[var_key] = var
                    self.current_led_controls[var_key] = widget
                
                if help_text: # Voeg tooltip toe indien help_text aanwezig is
                    ToolTip(widget, help_text)
                
                row_idx += 1
        
        # Voeg commands toe aan checkboxes en dropdown na het aanmaken
        if 'fade_in' in self.current_led_controls:
            self.current_led_controls['fade_in'].config(command=lambda: self.toggle_fade_in_fields_in_row(self.current_led_index))
        if 'fade_out' in self.current_led_controls:
            self.current_led_controls['fade_out'].config(command=lambda: self.toggle_fade_out_fields_in_row(self.current_led_index))
        if 'var_bright' in self.current_led_controls:
            self.current_led_controls['var_bright'].config(command=lambda: self.toggle_variable_brightness_fields_in_row(self.current_led_index))
        if 'blinking' in self.current_led_controls:
            self.current_led_controls['blinking'].config(command=lambda: self.toggle_blinking_fields_in_row(self.current_led_index))
        if 'light_type' in self.current_led_controls:
            self.current_led_controls['light_type'].bind("<<ComboboxSelected>>", lambda event: self.populate_selected_led_from_profile())

        self.disable_all_edit_fields() # Start met het bewerkingspaneel uitgeschakeld

    def disable_all_edit_fields(self):
        """Schakelt alle invoervelden in het bewerkingspaneel uit."""
        for control in self.current_led_controls.values():
            control.config(state="disabled")

    def enable_all_edit_fields(self):
        """Schakelt alle invoervelden in het bewerkingspaneel in (voordat specifieke toggles plaatsvinden)."""
        for key, control in self.current_led_controls.items():
            # Dropdowns en checkboxes moeten 'normal' of 'readonly' zijn voor gebruik
            if isinstance(control, ttk.Combobox):
                control.config(state="readonly")
            elif isinstance(control, ttk.Checkbutton):
                control.config(state="normal")
            else: # Entry fields
                control.config(state="normal")

    def select_led(self, led_index):
        """Selecteert een LED en vult het bewerkingspaneel."""
        # Eerst, sla de huidige bewerkte LED op als die er is
        if self.current_led_index is not None:
            if not self.save_current_led_config():
                # Als opslaan mislukt (validatiefout), blijf dan op de huidige LED
                return

        self.current_led_index = led_index
        self.led_number_label.config(text=f"Bewerk LED {led_index + 1}")
        self.enable_all_edit_fields() # Enable all fields before populating and toggling

        # Update de knopstijlen
        for i, btn in enumerate(self.led_buttons):
            if i == led_index:
                # Voor ttk.Button, gebruik 'state' om een 'pressed' uiterlijk te simuleren
                btn.state(['pressed'])
            else:
                btn.state(['!pressed']) # Zorg dat de knop niet 'pressed' is

        # Vul het bewerkingspaneel met de data van de geselecteerde LED
        self.populate_row(led_index)

        # Reset en start de simulatie voor de geselecteerde LED
        self.stop_simulation() # Stop eventuele lopende simulatie
        self.simulator = LedSimulator(self.led_data[led_index]['vars_snapshot'])
        self.reset_simulation() # Reset de simulator state
        self.sim_canvas.itemconfig(self.sim_led_label, text=f"LED {led_index + 1}")
        self.start_simulation() # Start automatisch de simulatie voor de nieuwe LED

    def populate_selected_led_from_profile(self):
        """Roept populate_row aan voor de geselecteerde LED, gebaseerd op het profiel."""
        if self.current_led_index is not None:
            # We moeten eerst de huidige waarden van de widgets ophalen voordat we het profiel toepassen,
            # anders overschrijven we de handmatig ingevoerde pin etc.
            temp_config = {}
            for key, tk_var in self.current_led_vars.items():
                if isinstance(tk_var, tk.StringVar):
                    temp_config[key] = tk_var.get()
                elif isinstance(tk_var, tk.BooleanVar):
                    temp_config[key] = tk_var.get()
            
            # Nu het profiel toepassen, maar de pin en light_type behouden
            selected_profile_name = temp_config['light_type']
            profile_data = LIGHT_PROFILES.get(selected_profile_name, LIGHT_PROFILES["Uitgeschakeld"])
            
            # Update temp_config met profieldata, behoud pin en light_type
            for key, value in profile_data.items():
                if key not in ['pin', 'light_type']: # Zorg dat pin en light_type niet overschreven worden
                    temp_config[key] = value
            
            self.populate_row(self.current_led_index, config_data=temp_config)
            # Na het updaten van het profiel, reset de simulatie met de nieuwe configuratie
            if self.current_led_index is not None:
                self.stop_simulation()
                self.simulator = LedSimulator(self.led_data[self.current_led_index]['vars_snapshot'])
                self.reset_simulation()
                self.start_simulation()


    def save_current_led_config(self):
        """Slaat de data van de momenteel geselecteerde LED op in self.led_data."""
        if self.current_led_index is None:
            return True # Geen LED geselecteerd om op te slaan

        config = {}
        vars_ = self.current_led_vars

        # Tijd om de data uit de actieve velden te halen
        for key, tk_var in vars_.items():
            if isinstance(tk_var, tk.StringVar):
                config[key] = tk_var.get()
            elif isinstance(tk_var, tk.BooleanVar):
                config[key] = tk_var.get()
        
        # Voer validatie uit voor alleen DEZE LED
        # Belangrijk: config_to_validate is hier de data direct uit de UI StringVar/BooleanVar, dus strings/booleans
        validated_config, warnings = self._validate_single_led_config(config, self.current_led_index)
        
        if validated_config is None:
            return False # Validatie mislukt

        # Als er waarschuwingen zijn, toon ze (alleen hier, niet in generate_code_action)
        # We tonen ze hier alleen als de gebruiker actief een LED opslaat/verlaat.
        # Bij code generatie worden ze later collectief getoond.
        if warnings:
            messagebox.showwarning("Waarschuwing", "\n".join(warnings))

        # Als validatie succesvol is, update self.led_data
        self.led_data[self.current_led_index]['vars_snapshot'] = validated_config # Sla de gevalideerde data op

        return True # Opslaan succesvol

    def populate_row(self, led_index, config_data=None):
        """Vult het bewerkingspaneel met configuratiegegevens en togglet de velden."""
        
        # Gebruik de 'vars_snapshot' als de bron van waarheid voor de waarden van de LED
        # Als er geen config_data is meegegeven, gebruik dan de snapshot
        if config_data is None:
            if 'vars_snapshot' in self.led_data[led_index]:
                config_data = self.led_data[led_index]['vars_snapshot']
            else:
                # Dit zou niet mogen gebeuren na load_default_configs, maar voor de zekerheid
                # Valback naar een leeg profiel of een default indien geen snapshot aanwezig.
                config_data = LIGHT_PROFILES["Uitgeschakeld"].copy()
                # Gebruik PWM_PINS[led_index] voor de default
                config_data['pin'] = str(PWM_PINS[led_index % len(PWM_PINS)])
                config_data['light_type'] = "Uitgeschakeld"


        # Vul de Entry widgets en BooleanVars in het bewerkingspaneel
        for key, tk_var in self.current_led_vars.items():
            # Speciale afhandeling voor pin en light_type die mogelijk al zijn ingevuld door de gebruiker
            if key == 'pin':
                # Zorg dat de pin altijd als string wordt ingesteld in de StringVar
                tk_var.set(str(config_data.get(key, '')))
            elif key == 'light_type':
                tk_var.set(config_data.get(key, list(LIGHT_PROFILES.keys())[0]))
            else:
                value = config_data.get(key, '')
                if isinstance(tk_var, tk.StringVar):
                    tk_var.set(str(value))
                elif isinstance(tk_var, tk.BooleanVar):
                    tk_var.set(bool(value))
        
        # Tijdelijke vlag om recursie tijdens initialisatie/populatie te voorkomen
        if not hasattr(self, '_populating_row'):
            self._populating_row = False

        if not self._populating_row:
            self._populating_row = True
            # Roep de toggle functies aan voor de UI-state
            self.toggle_fade_in_fields_in_row(led_index)
            self.toggle_fade_out_fields_in_row(led_index)
            self.toggle_variable_brightness_fields_in_row(led_index)
            # Pas een extra controle toe voor de blinking-functionaliteit
            self.apply_blinking_profile_restriction() # NIEUW
            self.toggle_blinking_fields_in_row(led_index) # Deze overschrijft de anderen
            self._populating_row = False
        else:
            self._update_fields_based_on_blinking_state(led_index)


    # --- Toggle Functies voor rijen (nu voor het bewerkingspaneel) ---
    def toggle_fade_in_fields_in_row(self, led_index):
        # We gebruiken self.current_led_vars en self.current_led_controls
        enabled = self.current_led_vars['fade_in'].get()
        controls = self.current_led_controls
        blinking_active = self.current_led_vars['blinking'].get()
        
        state = "normal" if enabled and not blinking_active else "disabled"
        for field_name in ['min_fade_in_s', 'max_fade_in_s']:
            if field_name in controls:
                controls[field_name].config(state=state)
        if 'fade_in' in controls:
            # Check de light_type om te bepalen of fading überhaupt toegestaan is
            light_type = self.current_led_vars['light_type'].get()
            blinking_allowed = LIGHT_PROFILES.get(light_type, {}).get('blinking', False) # Check if blinking is enabled in the profile
            
            if blinking_active and not blinking_allowed: # If blinking is active but not allowed by profile
                controls['fade_in'].config(state="disabled")
            elif blinking_active and blinking_allowed: # If blinking is active and allowed (like TV profile)
                controls['fade_in'].config(state="disabled") # Fading is still disabled if blinking is on
            else: # Blinking is not active, fading can be normal
                controls['fade_in'].config(state="normal")


    def toggle_fade_out_fields_in_row(self, led_index):
        enabled = self.current_led_vars['fade_out'].get()
        controls = self.current_led_controls
        blinking_active = self.current_led_vars['blinking'].get()

        state = "normal" if enabled and not blinking_active else "disabled"
        for field_name in ['min_fade_out_s', 'max_fade_out_s']:
            if field_name in controls:
                controls[field_name].config(state=state)
        if 'fade_out' in controls:
            light_type = self.current_led_vars['light_type'].get()
            blinking_allowed = LIGHT_PROFILES.get(light_type, {}).get('blinking', False)
            
            if blinking_active and not blinking_allowed:
                controls['fade_out'].config(state="disabled")
            elif blinking_active and blinking_allowed:
                controls['fade_out'].config(state="disabled")
            else:
                controls['fade_out'].config(state="normal")


    def toggle_variable_brightness_fields_in_row(self, led_index):
        enabled = self.current_led_vars['var_bright'].get()
        controls = self.current_led_controls
        blinking_active = self.current_led_vars['blinking'].get()

        state = "normal" if enabled and not blinking_active else "disabled"
        # bright_interval_s is niet meer van toepassing op 'variabele helderheid' (fixed brightness in ON state)
        for field_name in ['min_bright', 'max_bright']: # bright_interval_s is verwijderd
            if field_name in controls:
                controls[field_name].config(state=state)
        
        # Nu voor bright_interval_s zelf. Deze blijft altijd uitgeschakeld voor 'variabele helderheid'
        if 'bright_interval_s' in controls:
            controls['bright_interval_s'].config(state="disabled")

        if 'var_bright' in controls:
            light_type = self.current_led_vars['light_type'].get()
            blinking_allowed = LIGHT_PROFILES.get(light_type, {}).get('blinking', False)

            # In TV simulatie mag var_bright wél aan zijn, ook al is blinking aan
            if blinking_active and not blinking_allowed:
                controls['var_bright'].config(state="disabled")
            else: # Als blinking niet actief is, of als het TV-profiel is
                controls['var_bright'].config(state="normal")


    def toggle_blinking_fields_in_row(self, led_index):
        blinking_enabled = self.current_led_vars['blinking'].get()
        controls = self.current_led_controls
        
        # Check of het huidige lichtprofiel de blinking functie toestaat
        light_type = self.current_led_vars['light_type'].get()
        blinking_allowed_by_profile = LIGHT_PROFILES.get(light_type, {}).get('blinking', False)
        
        # Schakel de 'Knipperen?' checkbox zelf in/uit
        if 'blinking' in controls:
            if not blinking_allowed_by_profile:
                # Als profiel knipperen niet toestaat, forceer dan uit en disabled
                self.current_led_vars['blinking'].set(False) 
                controls['blinking'].config(state="disabled")
            else:
                # Als profiel knipperen wel toestaat, kan het wel (normaal)
                controls['blinking'].config(state="normal")


        blink_state_fields = "normal" if blinking_enabled and blinking_allowed_by_profile else "disabled"
        for field_name in ['blink_on_ms', 'blink_off_ms']:
            if field_name in controls:
                controls[field_name].config(state=blink_state_fields)
        
        # Schakel andere gerelateerde velden uit als knipperen is ingeschakeld
        if blinking_enabled and blinking_allowed_by_profile: # Alleen als blinking echt actief én toegestaan is
            # Forceer fading uit en schakel hun checkboxes uit
            for field_name in ['fade_in', 'fade_out']:
                if field_name in controls:
                    self.current_led_vars[field_name].set(False) # Reset de BooleanVar
                    controls[field_name].config(state="disabled") # Schakel de checkbox uit

            # De variabele helderheid checkbox mag aan blijven, maar bright_interval_s moet 0 zijn
            # Helderheid min/max blijven toegankelijk
            # bright_interval_s wordt disabled
            if 'bright_interval_s' in controls:
                controls['bright_interval_s'].config(state="disabled")
            
            # Schakel de invoervelden van fade uit
            for field_name in ['min_fade_in_s', 'max_fade_in_s', 'min_fade_out_s', 'max_fade_out_s']:
                if field_name in controls:
                    controls[field_name].config(state="disabled")
            
            # De hoofdtijden (min_on_s, max_on_s, min_off_s, max_off_s) worden
            # voor de TV simulatie gebruikt om de totale duur van de 'aan' en 'uit' periodes te bepalen,
            # dus die moeten bewerkbaar blijven.
            for field_name in ['min_on_s', 'max_on_s', 'min_off_s', 'max_off_s']:
                if field_name in controls:
                    controls[field_name].config(state="normal")
            
        else: # Als knipperen uit staat, of niet toegestaan is door het profiel
            # Zet de checkboxes van fade en variable brightness weer aan (als ze niet al disabled zijn door light_type)
            # En toggle dan hun velden
            
            # Update de variabele helderheid checkbox staat (kan weer 'normal' worden)
            if 'var_bright' in controls:
                controls['var_bright'].config(state="normal")

            # Roep de individuele toggle functies aan om de tekstvelden te updaten
            # op basis van de (nu bewerkbare) checkbox-waarden.
            self.toggle_fade_in_fields_in_row(led_index)
            self.toggle_fade_out_fields_in_row(led_index)
            self.toggle_variable_brightness_fields_in_row(led_index)
            
            # De hoofdtijden zijn altijd bewerkbaar
            for field_name in ['min_on_s', 'max_on_s', 'min_off_s', 'max_off_s']:
                if field_name in controls:
                    controls[field_name].config(state="normal")

    def apply_blinking_profile_restriction(self):
        """Past de beperking toe op de 'blinking' checkbox op basis van het geselecteerde profiel."""
        light_type = self.current_led_vars['light_type'].get()
        
        # Haal de 'blinking' eigenschap op uit het geselecteerde profiel.
        # Als het profiel niet gevonden wordt, ga dan uit van False.
        blinking_allowed_by_profile = LIGHT_PROFILES.get(light_type, {}).get('blinking', False)

        blinking_checkbox = self.current_led_controls.get('blinking')
        
        if blinking_checkbox:
            if not blinking_allowed_by_profile:
                # Als het profiel knipperen NIET toestaat:
                # Forceer de BooleanVar naar False en schakel de checkbox uit.
                self.current_led_vars['blinking'].set(False)
                blinking_checkbox.config(state="disabled")
            else:
                # Als het profiel knipperen WEL toestaat:
                # Schakel de checkbox in, zodat de gebruiker deze kan aan- of uitzetten.
                blinking_checkbox.config(state="normal")
        
        # Na het instellen van de blinking checkbox zelf, roep de toggle functie aan
        # om alle andere velden correct te updaten.
        if self.current_led_index is not None:
            self.toggle_blinking_fields_in_row(self.current_led_index)


    def _update_fields_based_on_blinking_state(self, led_index):
        """Hulpmethode om de velden te updaten na het populeren, rekening houdend met 'blinking'."""
        blinking_enabled = self.current_led_vars['blinking'].get()
        controls = self.current_led_controls

        # Check of het huidige lichtprofiel de blinking functie toestaat
        light_type = self.current_led_vars['light_type'].get()
        blinking_allowed_by_profile = LIGHT_PROFILES.get(light_type, {}).get('blinking', False)
        
        # Eerste stap: Configureer de 'blinking' checkbox zelf
        if 'blinking' in controls:
            if not blinking_allowed_by_profile:
                self.current_led_vars['blinking'].set(False) # Forceer uit
                controls['blinking'].config(state="disabled")
            else:
                controls['blinking'].config(state="normal") # Wel bewerkbaar


        blink_state = "normal" if blinking_enabled and blinking_allowed_by_profile else "disabled"
        for field_name in ['blink_on_ms', 'blink_off_ms']:
            if field_name in controls:
                controls[field_name].config(state=blink_state)

        # Schakel andere velden uit als knipperen actief is EN toegestaan door profiel
        if blinking_enabled and blinking_allowed_by_profile:
            # Forceer fading uit (checkboxes en hun tekstvelden)
            for field_name in ['fade_in', 'fade_out']:
                if field_name in controls:
                    self.current_led_vars[field_name].set(False) # Reset de BooleanVar
                    controls[field_name].config(state="disabled") # Schakel de checkbox uit

            # Schakel de invoervelden van fade uit
            for field_name in ['min_fade_in_s', 'max_fade_in_s', 'min_fade_out_s', 'max_fade_out_s']:
                if field_name in controls:
                    controls[field_name].config(state="disabled")
            
            # De variabele helderheid checkbox mag aan blijven als profiel dit toestaat
            # Zowel de checkbox zelf als min/max helderheid blijven bewerkbaar
            # bright_interval_s wordt disabled
            if 'bright_interval_s' in controls:
                controls['bright_interval_s'].config(state="disabled")
            
            # De hoofdtijden (min_on_s, max_on_s, min_off_s, max_off_s) blijven normaal
            for field_name in ['min_on_s', 'max_on_s', 'min_off_s', 'max_off_s']:
                if field_name in controls:
                    controls[field_name].config(state="normal")

        else: # Als knipperen uit staat, of niet toegestaan is door het profiel
            # Zet de checkboxes van fade en variable brightness weer aan (als ze niet al disabled zijn door light_type)
            # En toggle dan hun velden
            
            # Update de variabele helderheid checkbox staat (kan weer 'normal' worden)
            if 'var_bright' in controls:
                controls['var_bright'].config(state="normal")

            # Roep de individuele toggle functies aan om de tekstvelden te updaten
            # op basis van de (nu bewerkbare) checkbox-waarden.
            self.toggle_fade_in_fields_in_row(led_index)
            self.toggle_fade_out_fields_in_row(led_index)
            self.toggle_variable_brightness_fields_in_row(led_index)
            
            # De hoofdtijden zijn altijd bewerkbaar
            for field_name in ['min_on_s', 'max_on_s', 'min_off_s', 'max_off_s']:
                if field_name in controls:
                    controls[field_name].config(state="normal")


    def load_default_configs(self):
        """Laadt standaardconfiguraties voor alle LEDs (15 stuks) en vult de led_data."""
        self.led_data = []
        for i in range(self.num_leds):
            # Gebruik het "Uitgeschakeld" profiel als basis
            default_config = LIGHT_PROFILES["Uitgeschakeld"].copy()
            # Wijs een PWM-pin toe uit de PWM_PINS lijst
            default_config['pin'] = str(PWM_PINS[i]) # Zorg ervoor dat de pin als string wordt opgeslagen

            self.led_data.append({
                'id': f"LED_{i+1}",
                'vars_snapshot': default_config
            })
        
        if self.num_leds > 0:
            # Check if simulation_job is initialized before trying to cancel
            # This check is actually done inside stop_simulation now, but good to be explicit
            self.select_led(0) # Selecteer de eerste LED om mee te beginnen

    def _validate_single_led_config(self, config, led_index):
        """Valideert de configuratie van één LED en retourneert de opgeschoonde config."""
        validated_config = config.copy()
        errors = []
        warnings = []
        
        # Validatie van 'pin'
        # CONVERTEER ALTIJD NAAR STRING VOORDAT JE .isdigit() GEBRUIKT
        pin_str = str(validated_config.get('pin', '')) 
        
        if not pin_str.isdigit():
            errors.append(f"LED {led_index+1}: Pin moet een nummer zijn.")
        else:
            pin = int(pin_str)
            if pin not in PWM_PINS:
                errors.append(f"LED {led_index+1}: Pin {pin} is geen geldige Arduino Mega PWM pin ({PWM_PINS}).")
            # Controleer op dubbele pinnen
            for i, existing_led in enumerate(self.led_data):
                if i != led_index and 'pin' in existing_led['vars_snapshot']:
                    # Zorg ervoor dat de bestaande pin ook als int wordt vergeleken
                    existing_pin = int(str(existing_led['vars_snapshot']['pin']))
                    if existing_pin == pin:
                        errors.append(f"LED {led_index+1}: Pin {pin} is al toegewezen aan LED {i+1}.")
                        break
            validated_config['pin'] = pin # Converteer naar int voor opslag en Arduino code

        # Validatie van numerieke velden (tijden en helderheid)
        time_fields = ['min_on_s', 'max_on_s', 'min_off_s', 'max_off_s',
                       'min_fade_in_s', 'max_fade_in_s', 'min_fade_out_s', 'max_fade_out_s',
                       'bright_interval_s']
        ms_fields = ['blink_on_ms', 'blink_off_ms']
        brightness_fields = ['min_bright', 'max_bright']

        # Hulpfunctie voor numerieke validatie
        def validate_numeric_field(field_name, min_val=0, max_val=float('inf')):
            value_str = str(validated_config.get(field_name, '')) # Zorg dat het een string is
            if value_str == '': # Lege string, behandel als 0 voor numerieke conversie
                validated_config[field_name] = '0'
                value = 0.0 # Gebruik float voor seconden
            else:
                try:
                    # Check voor float of int, afhankelijk van het veld
                    if '_s' in field_name:
                        value = float(value_str)
                    else:
                        value = int(value_str)

                    if not (min_val <= value <= max_val):
                        errors.append(f"LED {led_index+1}: '{field_name}' ({value}) moet tussen {min_val} en {max_val} zijn.")
                    validated_config[field_name] = str(value) if '_s' in field_name else str(int(value)) # Sla als string op (voor UI consistentie)
                except ValueError:
                    errors.append(f"LED {led_index+1}: '{field_name}' moet een geldig nummer zijn.")
        
        for field in time_fields:
            validate_numeric_field(field, 0)
        for field in ms_fields:
            validate_numeric_field(field, 0)
        for field in brightness_fields:
            validate_numeric_field(field, 0, 255)

        # Validatie van min/max relaties
        if float(validated_config.get('min_on_s', '0')) > float(validated_config.get('max_on_s', '0')):
            errors.append(f"LED {led_index+1}: 'Min Aan' kan niet groter zijn dan 'Max Aan'.")
        if float(validated_config.get('min_off_s', '0')) > float(validated_config.get('max_off_s', '0')):
            errors.append(f"LED {led_index+1}: 'Min Uit' kan niet groter zijn dan 'Max Uit'.")
        if float(validated_config.get('min_fade_in_s', '0')) > float(validated_config.get('max_fade_in_s', '0')):
            errors.append(f"LED {led_index+1}: 'Min Fade In' kan niet groter zijn dan 'Max Fade In'.")
        if float(validated_config.get('min_fade_out_s', '0')) > float(validated_config.get('max_fade_out_s', '0')):
            errors.append(f"LED {led_index+1}: 'Min Fade Out' kan niet groter zijn dan 'Max Fade Out'.")
        if int(float(validated_config.get('min_bright', '0'))) > int(float(validated_config.get('max_bright', '0'))): # Gebruik float voor consistentie met parse
            errors.append(f"LED {led_index+1}: 'Min Helderheid' kan niet groter zijn dan 'Max Helderheid'.")
        if int(validated_config.get('blink_on_ms', '0')) > 0 and int(validated_config.get('blink_off_ms', '0')) == 0:
            warnings.append(f"LED {led_index+1}: 'Knipper Aan' is ingesteld, maar 'Knipper Uit' is 0ms. Dit kan onverwacht gedrag veroorzaken.")
        if int(validated_config.get('blink_off_ms', '0')) > 0 and int(validated_config.get('blink_on_ms', '0')) == 0:
            warnings.append(f"LED {led_index+1}: 'Knipper Uit' is ingesteld, maar 'Knipper Aan' is 0ms. Dit kan onverwacht gedrag veroorzaken.")

        # Specifieke validatie voor Blinking mode
        # Haal de light_type van de _gevalideerde_ configuratie op.
        current_light_type = validated_config.get('light_type', 'Uitgeschakeld')
        blinking_allowed_by_profile = LIGHT_PROFILES.get(current_light_type, {}).get('blinking', False)

        if validated_config.get('blinking'): # Alleen als blinking is aangevinkt
            # Als profiel knipperen niet toestaat, is dit een fout
            if not blinking_allowed_by_profile:
                errors.append(f"LED {led_index+1}: Knippermodus is alleen toegestaan voor het 'TV Simulatie' profiel. Schakel 'Knipperen?' uit of kies het 'TV Simulatie' profiel.")
            else: # Als blinking wel toegestaan is door het profiel (d.w.z. TV Simulatie)
                # Fading is niet toegestaan in knippermodus
                if validated_config.get('fade_in') or validated_config.get('fade_out'):
                    errors.append(f"LED {led_index+1}: Fading is niet toegestaan in knippermodus. Schakel 'Fade In?' en 'Fade Out?' uit.")
                
                # bright_interval_s heeft geen effect
                if float(validated_config.get('bright_interval_s', '0')) > 0:
                    warnings.append(f"LED {led_index+1}: 'Interval Helderheid' heeft geen effect in knippermodus en wordt genegeerd.")

                # Zorg dat min_bright en max_bright geldig zijn voor knipperen
                if not (0 <= int(float(validated_config.get('min_bright', '0'))) <= 255) or \
                   not (0 <= int(float(validated_config.get('max_bright', '0'))) <= 255):
                   errors.append(f"LED {led_index+1}: Min/Max Helderheid moet tussen 0 en 255 zijn voor knipperen.")
                
                # Zorg dat blink_on_ms en blink_off_ms zinvolle waarden hebben
                if int(validated_config.get('blink_on_ms', '0')) <= 0 or int(validated_config.get('blink_off_ms', '0')) <= 0:
                    errors.append(f"LED {led_index+1}: 'Knipper Aan (ms)' en 'Knipper Uit (ms)' moeten groter zijn dan 0 in knippermodus.")
            
        if errors:
            # print(f"Validation errors for LED {led_index+1}: {errors}") # Debugging
            messagebox.showerror(f"Validatie Fout LED {led_index+1}", "\n".join(errors))
            return None, warnings # Geen gevalideerde config bij fouten
        
        return validated_config, warnings

    def generate_code_action(self):
        """Valideert alle LEDs en genereert de Arduino code."""
        # Eerst, zorg dat de actieve LED's configuratie is opgeslagen
        if self.current_led_index is not None:
            if not self.save_current_led_config():
                return # Opslaan mislukt, niet verder gaan

        final_led_configs = []
        all_warnings = []
        all_errors_present = False # Nieuwe vlag om aan te geven of er *fouten* waren

        # Verzamel en valideer alle configuraties
        for i, led_entry in enumerate(self.led_data):
            config_to_validate = led_entry['vars_snapshot']
            
            validated_config, warnings = self._validate_single_led_config(config_to_validate, i)
            
            if validated_config is None:
                all_errors_present = True
                # Foutmelding is al getoond door _validate_single_led_config, dus hier geen extra messagebox
                break # Stop bij de eerste fout
            else:
                final_led_configs.append(validated_config) # Gebruik de gevalideerde config direct
                all_warnings.extend(warnings) # Verzamel alle waarschuwingen

        if all_errors_present:
            # Als er fouten waren, is de messagebox al getoond in _validate_single_led_config.
            return # Stop als er fouten zijn

        if all_warnings:
            messagebox.showwarning("Waarschuwingen", "De volgende waarschuwingen zijn gevonden:\n" + "\n".join(all_warnings) + "\n\nDe code wordt wel gegenereerd.")

        # Vraag waar het bestand moet worden opgeslagen
        file_path = filedialog.asksaveasfilename(defaultextension=".ino",
                                                 filetypes=[("Arduino Sketch", "*.ino"), ("All Files", "*.*")])
        if file_path:
            try:
                arduino_code = generate_arduino_code(final_led_configs)
                with open(file_path, "w") as f:
                    f.write(arduino_code)
                messagebox.showinfo("Succes", f"Arduino code opgeslagen naar:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Fout", f"Fout bij opslaan van code: {e}")

    def save_configs(self):
        """Slaat de huidige LED-configuraties en simulatieparameters op naar een JSON-bestand."""
        if self.current_led_index is None:
            return # Geen LED geselecteerd om op te slaan

        if not self.save_current_led_config():
            return # Opslaan mislukt, niet verder gaan

        file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if file_path:
            try:
                # Alleen de 'vars_snapshot' van elke LED opslaan
                data_to_save = {
                    "led_configurations": [led['vars_snapshot'] for led in self.led_data],
                    "simulation_settings": {
                        "simulation_speed_factor": self.simulation_speed_factor
                        # We slaan de 'running' status niet op, simulatie begint altijd gepauzeerd na laden
                    }
                }
                with open(file_path, "w") as f:
                    json.dump(data_to_save, f, indent=4)
                messagebox.showinfo("Succes", f"Configuraties opgeslagen naar:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Fout", f"Fout bij opslaan van configuraties: {e}")

    def load_configs(self):
        """Laadt LED-configuraties en simulatieparameters van een JSON-bestand."""
        file_path = filedialog.askopenfilename(defaultextension=".json",
                                               filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, "r") as f:
                    loaded_data = json.load(f)
                
                # Controleer of het een nieuw formaat is met simulation_settings
                if isinstance(loaded_data, dict) and "led_configurations" in loaded_data:
                    led_configs = loaded_data["led_configurations"]
                    sim_settings = loaded_data.get("simulation_settings", {})
                elif isinstance(loaded_data, list): # Ouder formaat
                    led_configs = loaded_data
                    sim_settings = {} # Geen sim settings in oud formaat
                else:
                    raise ValueError("Bestand bevat geen geldige lijst of dict van configuraties.")

                if not isinstance(led_configs, list):
                    raise ValueError("Bestand bevat geen geldige lijst van LED configuraties.")

                # Leeg bestaande data en vul met geladen data
                self.led_data = []
                for i, config_dict in enumerate(led_configs):
                    # Zorg ervoor dat geladen config een snapshot is
                    self.led_data.append({'id': f"LED_{i+1}", 'vars_snapshot': config_dict})
                
                # Als er meer LEDs geladen zijn dan PWM_PINS, truncaten we of waarschuwen we.
                # Voor nu, als de geladen data minder is dan self.num_leds, vullen we aan met defaults
                if len(self.led_data) < self.num_leds:
                    for i in range(len(self.led_data), self.num_leds):
                        default_config = LIGHT_PROFILES["Uitgeschakeld"].copy()
                        default_config['pin'] = str(PWM_PINS[i])
                        self.led_data.append({'id': f"LED_{i+1}", 'vars_snapshot': default_config})
                elif len(self.led_data) > self.num_leds:
                    messagebox.showwarning("Waarschuwing", f"Het geladen bestand bevat {len(self.led_data)} LEDs, maar dit programma ondersteunt maximaal {self.num_leds} LEDs (gebaseerd op Arduino Mega PWM pinnen). De extra LEDs worden genegeerd.")
                    self.led_data = self.led_data[:self.num_leds] # Truncate

                # Laad simulatie-instellingen
                loaded_speed = sim_settings.get("simulation_speed_factor")
                if loaded_speed is not None:
                    try:
                        self.simulation_speed_factor = float(loaded_speed)
                        self.speed_slider.set(self.simulation_speed_factor)
                        self.speed_label.config(text=f"{self.simulation_speed_factor:.1f}x")
                    except ValueError:
                        messagebox.showwarning("Waarschuwing", "Ongeldige simulatiesnelheid gevonden in bestand. Standaardwaarde wordt gebruikt.")
                        self.simulation_speed_factor = 1.0 # Reset naar default
                        self.speed_slider.set(self.simulation_speed_factor)
                        self.speed_label.config(text=f"{self.simulation_speed_factor:.1f}x")
                else:
                    # Als er geen simulatiesnelheid is opgeslagen, blijft de huidige snelheid gehandhaafd of de default
                    pass

                if self.led_data:
                    self.select_led(0) # Selecteer de eerste geladen LED
                    self.stop_simulation() # Zorg dat simulatie gepauzeerd is na laden
                    messagebox.showinfo("Succes", f"Configuraties succesvol geladen van:\n{file_path}")
                else:
                    messagebox.showwarning("Waarschuwing", "Het geladen bestand bevatte geen LED configuraties.")
                    self.load_default_configs() # Herlaad defaults als bestand leeg is

            except json.JSONDecodeError:
                messagebox.showerror("Fout", "Ongeldig JSON-bestand.")
            except ValueError as ve:
                messagebox.showerror("Fout", f"Fout in bestandsformaat: {ve}")
            except Exception as e:
                messagebox.showerror("Fout", f"Fout bij laden van configuraties: {e}")

    def start_simulation(self):
        if not self.simulation_running:
            if self.current_led_index is None:
                messagebox.showwarning("Geen LED Geselecteerd", "Selecteer eerst een LED om de simulatie te starten.")
                return
            
            # Zorg dat de huidige configuratie is opgeslagen en gevalideerd voordat de simulatie start
            if not self.save_current_led_config():
                return # Validatie mislukt, start simulatie niet

            self.simulator = LedSimulator(self.led_data[self.current_led_index]['vars_snapshot'])
            self.simulation_start_time = time.time() * 1000 # Huidige tijd in ms
            self.simulation_running = True
            self.start_sim_button.config(state="disabled")
            self.pause_sim_button.config(state="normal")
            self.reset_sim_button.config(state="normal")
            self._update_simulation() # Start de update loop

    def pause_simulation(self):
        self.simulation_running = False
        self.start_sim_button.config(state="normal")
        self.pause_sim_button.config(state="disabled")

    def reset_simulation(self):
        self.stop_simulation() # Stop eventuele lopende animatie, reset _simulation_job
        if self.simulator:
            self.simulator.reset()
        
        # Geef 0 door als de huidige simulatietijd voor de reset-weergave
        self.update_simulation_display(0, LedSimulator.MODE_OFF, 0, 0, current_sim_time_ms=0) # Zet display op 0 helderheid en uit

        # Reset timers
        self.on_timer_label.config(text="Aan: 0.0s / 0.0s")
        self.off_timer_label.config(text="Uit: 0.0s / 0.0s")
        self.mode_label.config(text="Modus: UIT") # NIEUW: Reset modus label

    def stop_simulation(self):
        self.simulation_running = False
        self.start_sim_button.config(state="normal")
        self.pause_sim_button.config(state="disabled")
        self.reset_sim_button.config(state="disabled") # Disable reset button when simulation is fully stopped
        
        # Alleen after_cancel aanroepen als er daadwerkelijk een geplande job is
        if self._simulation_job is not None:
            self.master.after_cancel(self._simulation_job)
            self._simulation_job = None # Reset de job ID


    def set_simulation_speed(self, value):
        self.simulation_speed_factor = float(value)
        # Controleer of speed_label al is geïnitialiseerd
        if self.speed_label:
            self.speed_label.config(text=f"{self.simulation_speed_factor:.1f}x")

    def _update_simulation(self):
        if not self.simulation_running:
            self._simulation_job = None # Zorg dat de job ID wordt gereset als simulatie stopt
            return

        current_sim_time_ms = (time.time() * 1000 - self.simulation_start_time) * self.simulation_speed_factor
        
        # De simulator update zijn interne toestand en retourneert de huidige helderheid
        brightness, current_mode, expected_duration_ms, phase_start_time_ms = self.simulator.update(current_sim_time_ms)

        # Update de visualisatie
        self.update_simulation_display(brightness, current_mode, expected_duration_ms, phase_start_time_ms, current_sim_time_ms)

        # Plan de volgende update en sla de job ID op
        self._simulation_job = self.master.after(self.simulation_update_interval_ms, self._update_simulation)

    def update_simulation_display(self, brightness, current_mode, expected_duration_ms, phase_start_time_ms, current_sim_time_ms):
        # Helderheid van de LED cirkel
        # Convergeer helderheid naar hexadecimale kleur
        hex_brightness = hex(brightness)[2:].zfill(2)
        color = f"#{hex_brightness}{hex_brightness}{hex_brightness}"
        self.sim_canvas.itemconfig(self.sim_led_circle, fill=color)

        # Update de modus weergave
        mode_name = LedSimulator.MODE_NAMES.get(current_mode, "Onbekend")
        self.mode_label.config(text=f"Modus: {mode_name}")


        # Update de timers
        # De elapsed_phase_time_s moet gebaseerd zijn op de huidige 'simulatietijd'
        # niet op de werkelijke tijd. De `phase_start_time_ms` komt al van de simulator.
        elapsed_phase_time_s_sim = (current_sim_time_ms - phase_start_time_ms) / 1000.0
        
        # Voorkom negatieve waarden door float afrondingsfouten bij start
        elapsed_phase_time_s_sim = max(0.0, elapsed_phase_time_s_sim) 

        expected_duration_s = expected_duration_ms / 1000.0

        if current_mode == LedSimulator.MODE_ON:
            self.on_timer_label.config(text=f"Aan: {elapsed_phase_time_s_sim:.1f}s / {expected_duration_s:.1f}s")
            self.off_timer_label.config(text="Uit: ---")
        elif current_mode == LedSimulator.MODE_OFF:
            self.on_timer_label.config(text="Aan: ---")
            self.off_timer_label.config(text=f"Uit: {elapsed_phase_time_s_sim:.1f}s / {expected_duration_s:.1f}s")
        elif current_mode == LedSimulator.MODE_FADE_IN:
            self.on_timer_label.config(text=f"Fading In: {elapsed_phase_time_s_sim:.1f}s / {expected_duration_s:.1f}s")
            self.off_timer_label.config(text="---")
        elif current_mode == LedSimulator.MODE_FADE_OUT:
            self.on_timer_label.config(text=f"Fading Uit: {elapsed_phase_time_s_sim:.1f}s / {expected_duration_s:.1f}s")
            self.off_timer_label.config(text="---")
        elif current_mode == LedSimulator.MODE_BLINKING:
            # Voor knipperen tonen we de hoofdtijd van de "aan" periode (TV simulatie)
            self.on_timer_label.config(text=f"Actieve periode: {elapsed_phase_time_s_sim:.1f}s / {expected_duration_s:.1f}s")
            # De blink_state geeft aan of de korte knipper-cyclus AAN of UIT is
            if self.simulator.blink_state: 
                self.off_timer_label.config(text=f"Knipper: AAN (Helderheid: {brightness})") # Toon ook helderheid
            else:
                self.off_timer_label.config(text=f"Knipper: UIT")
        else: # Onbekende modus of initiële staat
            self.on_timer_label.config(text="Aan: 0.0s / 0.0s")
            self.off_timer_label.config(text="Uit: 0.0s / 0.0s")


if __name__ == "__main__":
    root = tk.Tk()
    app = LedConfiguratorApp(root)
    root.mainloop()
