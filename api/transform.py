import json, os, re
from http.server import BaseHTTPRequestHandler
import openai

# Tes variables secrètes (définies dans Vercel, jamais dans le code)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
MOT_DE_PASSE = os.environ.get("APP_PASSWORD", "monmotdepasse")

client = openai.OpenAI(api_key=OPENAI_KEY)

PROMPT_ANALYSE = """
Tu es un analyste narratif. Lis ce synopsis et extrais :
1. Les énigmes (liste précise)
2. La structure narrative (début / nœud / dénouement)
3. Les éléments immuables (personnages-clés, logique interne, style)

Réponds UNIQUEMENT en JSON, exactement comme ceci :
{{
  "enigmes": ["...", "..."],
  "structure": {{"debut": "...", "noeud": "...", "denouement": "..."}},
  "elements_immuables": ["...", "..."],
  "style": "..."
}}

Synopsis :
{synopsis}
"""

PROMPT_TRANSFORMATION = """
Tu es un auteur créatif. Réécris ce synopsis dans le thème demandé.

RÈGLES ABSOLUES :
- Conserve EXACTEMENT ces énigmes : {enigmes}
- Conserve EXACTEMENT cette structure : {structure}
- Conserve EXACTEMENT ces éléments : {elements_immuables}
- Imite ce style d'écriture : {style}
- Change UNIQUEMENT le thème, l'univers, l'esthétique

Thème cible : {theme_cible}
Synopsis original :
{synopsis}
"""

def appeler_llm(prompt):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content

def analyser(synopsis):
    brut = appeler_llm(PROMPT_ANALYSE.format(synopsis=synopsis))
    match = re.search(r'\{.*\}', brut, re.DOTALL)
    if match:
        brut = match.group()
    brut = re.sub(r',\s*([}\]])', r'\1', brut)
    return json.loads(brut)

def transformer(synopsis, analyse, theme):
    return appeler_llm(PROMPT_TRANSFORMATION.format(
        synopsis=synopsis, theme_cible=theme,
        enigmes=analyse["enigmes"],
        structure=analyse["structure"],
        elements_immuables=analyse["elements_immuables"],
        style=analyse["style"]
    ))

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", 0))
        donnees = json.loads(self.rfile.read(longueur))

        # Vérification du mot de passe
        if donnees.get("password") != MOT_DE_PASSE:
            self._repondre(401, {"ok": False, "erreur": "Mot de passe incorrect."})
            return

        try:
            analyse = analyser(donnees["synopsis"])
            resultat = transformer(donnees["synopsis"], analyse, donnees["theme"])
            self._repondre(200, {"ok": True, "resultat": resultat, "analyse": analyse})
        except Exception as e:
            self._repondre(500, {"ok": False, "erreur": str(e)})

    def _repondre(self, code, data):
        corps = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(corps))
        self.end_headers()
        self.wfile.write(corps)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def log_message(self, *args):
        pass
