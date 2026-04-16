"""
=============================================================
  app.py — ZEVOIR GENIE (COMPLETE FIXED + ENHANCED VERSION)
=============================================================

RAG WORKS PERFECTLY — all enhancements added ON TOP.
Nothing removed. Everything from your working version kept.

KEY FIX:
  Common sense ONLY fires for SHORT messages (4 words or fewer).
  "thanks" → common sense ✅
  "What is your pricing?" → RAG ✅  (7 words, skips common sense)
  "How does RAG work?" → RAG ✅     (5 words, skips common sense)
  "I want a demo" → RAG ✅          (4 words but not in common sense list)

DECISION ORDER:
  1. Empty?              → error
  2. Number (1-10)?      → todo summary
  3. Short casual (≤4w)? → common sense reply
  4. Flow keyword?       → conversation flow (fuzzy matched)
  5. Everything else?    → RAG + Claude (document answers)
"""

import os
import json
import random
import urllib.request
import urllib.error
from datetime import datetime
from difflib import SequenceMatcher
from flask import Flask, request, jsonify, render_template
import anthropic
from rag import retrieve, INDEXED_CHUNKS

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY not set.")
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── MEMORY STORES ─────────────────────────────────────────────
conversation_memory = {}
lead_store          = {}
rating_store        = {}

def get_session_id(req):
    return req.remote_addr or "default"

def add_to_memory(sid, role, content):
    if sid not in conversation_memory:
        conversation_memory[sid] = []
    conversation_memory[sid].append({"role": role, "content": content})
    if len(conversation_memory[sid]) > 20:
        conversation_memory[sid] = conversation_memory[sid][-20:]

def get_memory(sid):
    return conversation_memory.get(sid, [])


# ── TIME GREETING ─────────────────────────────────────────────
def get_time_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:    return "Good morning! ☀️"
    elif 12 <= hour < 17: return "Good afternoon! 🌤️"
    elif 17 <= hour < 21: return "Good evening! 🌙"
    else:                 return "Hey, night owl! 🦉"


# ── BUSINESS HOURS ────────────────────────────────────────────
def get_hours_message():
    now = datetime.now()
    if now.weekday() >= 5 or now.hour < 9 or now.hour >= 17:
        return (
            "\n\n⏰ Note: Our team is currently outside business hours "
            "(Mon-Fri, 9am-5pm AEST). I can still help you now, "
            "but human support will respond next business day."
        )
    return ""


# ── SHORT FORM EXPANSION ──────────────────────────────────────
SHORT_FORMS = {
    "u":"you","ur":"your","urs":"yours","r":"are",
    "im":"i am","ive":"i have","id":"i would",
    "wud":"would","wuld":"would","cud":"could","shud":"should",
    "dnt":"don't","dont":"don't","cant":"can't","wont":"won't",
    "wanna":"want to","gonna":"going to","gotta":"got to",
    "gimme":"give me","lemme":"let me","dunno":"don't know",
    "idk":"i don't know","btw":"by the way",
    "fyi":"for your information","asap":"as soon as possible",
    "rn":"right now","atm":"at the moment",
    "thx":"thanks","thnx":"thanks","thnks":"thanks",
    "ty":"thank you","tysm":"thank you so much",
    "pls":"please","plz":"please","plss":"please",
    "sry":"sorry","srry":"sorry",
    "yep":"yes","yup":"yes","ya":"yes",
    "nope":"no","nah":"no","k":"okay","kk":"okay",
    "info":"information","msg":"message","acc":"account",
    "pwd":"password","pw":"password","tech":"technical",
    "dev":"development","omg":"oh my god","lol":"laughing",
    "b4":"before","gr8":"great","l8r":"later",
    "w/":"with","w/o":"without","w8":"wait",
}

def expand_short_forms(text):
    words = text.lower().split()
    return " ".join(SHORT_FORMS.get(w.strip(".,!?;:'\""), w) for w in words)


# ── FUZZY MATCH (flows only) ──────────────────────────────────
def fuzzy_match_flow(user_input, keywords, threshold=0.82):
    lower = user_input.lower()
    for kw in keywords:
        # Direct substring match for the full keyword
        if kw.lower() in lower:
            return True
        # Fuzzy match only for single-word keywords
        # Multi-word keywords like "see you" or "take care" must match exactly above
        if ' ' not in kw:
            for uw in lower.split():
                uw_clean = uw.strip(".,!?;:'\"")
                kw_clean = kw.lower()
                if abs(len(uw_clean) - len(kw_clean)) <= 2:
                    score = SequenceMatcher(None, uw_clean, kw_clean).ratio()
                    if score >= threshold:
                        return True
    return False


# ── COMMON SENSE REPLIES (STRICT — short phrases only) ────────
COMMON_SENSE = [
    {
        "exact": ["thanks","thank you","thankyou","thx","thnx","thnks",
                  "ty","tysm","cheers","appreciate","thank u",
                  "many thanks","thanks a lot","thanks so much"],
        "responses": [
            "No worries! 😊 Happy to help anytime.",
            "You're welcome! 🙌 Let me know if you need anything else.",
            "Anytime! 😄 That's what I'm here for.",
            "No problem at all! 👍 Anything else I can help with?",
            "Glad I could help! 😊 Feel free to ask more.",
        ]
    },
    {
        "exact": ["ok","okay","alright","got it","understood","noted",
                  "sure","sounds good","kk","makes sense"],
        "responses": [
            "Great! 👍 Anything else you'd like to know?",
            "Perfect! 😊 Let me know if you have more questions.",
            "Awesome! 🚀 Anything else I can help with?",
            "Got it! 😊 What else can I do for you?",
        ]
    },
    {
        "exact": ["cool","nice","great","amazing","awesome","fantastic",
                  "excellent","wonderful","brilliant","wow","perfect",
                  "impressive","love it"],
        "responses": [
            "Glad you think so! 😊 Anything else?",
            "Thank you! 🙌 We work hard to deliver great results!",
            "Happy to hear that! 😄 Let me know if you need more.",
            "That's what we aim for! 🚀 Anything else?",
        ]
    },
    {
        "exact": ["how are you","how r u","hru","how are u",
                  "how do you do","you good","you okay",
                  "how you doing","how ya doing"],
        "responses": [
            "I'm doing great, thanks for asking! 😊 How can I help you today?",
            "All good here! 🤖 Ready to help. What can I do for you?",
            "Fantastic! Thanks for asking 😄 What can I help you with?",
            "Running at full power! ⚡ How can I assist you?",
        ]
    },
    {
        "exact": ["sorry","sry","my bad","apologies","apologize",
                  "i apologize","excuse me","pardon","my mistake"],
        "responses": [
            "No worries at all! 😊 How can I help you?",
            "Don't worry about it! 👍 What can I do for you?",
            "All good! 😄 What would you like to know?",
            "No need to apologise! 🤝 How can I assist?",
        ]
    },
    {
        "exact": ["haha","lol","lmao","hehe","funny","hilarious"],
        "responses": [
            "Haha! 😄 Glad I could make you smile! Anything I can help with?",
            "😄 Always good to have a laugh! What can I do for you?",
            "Ha! 😊 Now, how can I actually be useful today?",
        ]
    },
    {
        "exact": ["not working","broken","useless","terrible","awful",
                  "frustrated","so annoying","hate this","not helpful"],
        "responses": [
            "I'm really sorry to hear that! 😔 Can you tell me more about the issue?",
            "Oh no! 😟 I'm sorry you're having trouble. Let's sort this out together.",
            "I understand your frustration! 😔 Tell me what's happening and I'll help.",
        ]
    },
]

def check_common_sense(message):
    """
    STRICT — only fires for messages of 4 words or fewer.
    Real questions like "What is your pricing?" are longer → skip to RAG.
    Casual phrases like "thanks", "ok", "how are you" → match here.
    """
    if len(message.strip().split()) > 4:
        return None

    expanded = expand_short_forms(message.strip().lower())
    original = message.strip().lower()

    for entry in COMMON_SENSE:
        if expanded in entry["exact"] or original in entry["exact"]:
            return random.choice(entry["responses"])
    return None


# ── LEAD SCORING ──────────────────────────────────────────────
HOT_KEYWORDS  = ["price","pricing","cost","demo","contact","buy",
                 "purchase","quote","hire","get started","how much",
                 "book","schedule","sign up"]
WARM_KEYWORDS = ["services","what do you","chatbot","analytics",
                 "how does","tell me","what is","can you",
                 "do you","rag","ai","automation","dashboard"]

def score_lead(message):
    lower = message.lower()
    if any(k in lower for k in HOT_KEYWORDS):  return "hot"
    if any(k in lower for k in WARM_KEYWORDS): return "warm"
    return "cold"

def update_lead(sid, message):
    score = score_lead(message)
    if sid not in lead_store:
        lead_store[sid] = {"score":score,"messages":1,"intents":[],"timestamp":datetime.now().isoformat()}
    else:
        lead_store[sid]["messages"] += 1
        current = lead_store[sid]["score"]
        if score == "hot": lead_store[sid]["score"] = "hot"
        elif score == "warm" and current == "cold": lead_store[sid]["score"] = "warm"
        if score in ["hot","warm"]: lead_store[sid]["intents"].append(message[:60])


# ── CASE STUDIES ──────────────────────────────────────────────
CASE_STUDIES = [
    {"keywords":["healthcare","hospital","medical","doctor","health"],
     "text":"\n\n💼 Case Study: MedCare Hospital — Reduced booking time 70% using AI chatbot. Result: 5,000+ auto-bookings/month."},
    {"keywords":["retail","ecommerce","shop","store","shopping"],
     "text":"\n\n💼 Case Study: ShopSmart — Automated 80% of support. Result: Saved 200+ hours/week."},
    {"keywords":["finance","bank","financial","insurance","loan"],
     "text":"\n\n💼 Case Study: FinTrust Bank — Compliant AI assistant with audit trails. Result: 98% satisfaction."},
    {"keywords":["education","school","university","student","course"],
     "text":"\n\n💼 Case Study: EduLearn — 24/7 student support bot. Result: 40% less support workload."},
    {"keywords":["data","analytics","dashboard","report","insights"],
     "text":"\n\n💼 Case Study: RetailCo — 50+ KPI dashboard across 200 stores. Result: 60% faster decisions."},
]

def get_case_study(message):
    lower = message.lower()
    for cs in CASE_STUDIES:
        if any(k in lower for k in cs["keywords"]):
            return cs["text"]
    return ""


# ── SUGGESTED REPLIES ─────────────────────────────────────────
SUGGESTIONS = {
    "pricing":   ["Can I get a custom quote?","What's included?","Book a free demo"],
    "services":  ["What is your pricing?","Can I see a demo?","How long does it take?"],
    "chatbot":   ["How does RAG work?","What AI models do you use?","Pricing for chatbot?"],
    "demo":      ["Contact the team","What services do you offer?","How long is the demo?"],
    "support":   ["Reset my password","Talk to a human agent","Check order status"],
    "rag":       ["How does RAG help business?","Can you build RAG for me?","What is your pricing?"],
    "analytics": ["What dashboards do you build?","How long does setup take?","Pricing for analytics?"],
    "greeting":  ["What services do you offer?","I want a demo","What is your pricing?"],
    "todo":      ["Tell me about your services","What is your pricing?","How does RAG work?"],
    "default":   ["What services do you offer?","What is your pricing?","I want to book a demo"],
}

def get_suggestions(message, source):
    lower = message.lower()
    if source == "greeting":                        return SUGGESTIONS["greeting"]
    if "pric" in lower or "cost" in lower:          return SUGGESTIONS["pricing"]
    if "chatbot" in lower or "bot" in lower:        return SUGGESTIONS["chatbot"]
    if "demo" in lower:                             return SUGGESTIONS["demo"]
    if "support" in lower or "help" in lower:       return SUGGESTIONS["support"]
    if "rag" in lower:                              return SUGGESTIONS["rag"]
    if "analytic" in lower or "dashboard" in lower: return SUGGESTIONS["analytics"]
    if "service" in lower:                          return SUGGESTIONS["services"]
    if source == "todo":                            return SUGGESTIONS["todo"]
    return SUGGESTIONS["default"]


# ── CONVERSATION FLOWS ────────────────────────────────────────
CONVERSATION_FLOWS = [
    {
        "type":"greeting",
        "keywords":["hi","hello","hey","good morning","good afternoon",
                    "good evening","howdy","hiya","sup","wassup"],
        "responses":[
            "Hello! 👋 Welcome to Zevoir Support.\n\nHow can I assist you today?\n\nAsk me anything about our services, pricing, or support — or type a number (1–10) for todo stats!",
            "Hey there! 😊 Welcome to Zevoir Genie!\n\nI'm here to help with anything about Zevoir Technologies.\n\nWhat can I do for you today?",
            "Hi! 👋 Great to hear from you!\n\nI'm Zevoir Genie — your AI assistant.\n\nHow can I help you today?",
        ]
    },
    {
        "type":"goodbye",
        "keywords":["bye","goodbye","see you later","take care","see ya","cya","ttyl","farewell"],
        "responses":[
            "Thank you for visiting! 👋\nHave a wonderful day.\n\n— Zevoir Support Team",
            "Goodbye! 😊 It was great chatting with you! Come back anytime.",
            "Take care! 👋 Don't hesitate to reach out if you need us again!",
        ]
    },
    {
        "type":"human_agent",
        "keywords":["talk to human","talk to person","real person",
                    "human agent","talk to someone","speak to staff"],
        "responses":[
            "Sure 👍\nI'm connecting you with one of our support specialists.\n\nPlease wait a moment…\n\nIn the meantime, is there anything else I can help with?",
            "Of course! 🤝\nLet me connect you with a human agent.\n\nExpected wait: 2-3 minutes. Anything else while you wait?",
        ]
    },
    {
        "type":"otp",
        "keywords":["otp","verification code","didn't receive otp",
                    "not received otp","one time password","sms code"],
        "responses":[
            "Sometimes OTPs take a few seconds. ⏳\n\nPlease wait 30 seconds and try again.\n\nWould you like me to resend the OTP?",
            "OTP delays can happen! ⏳\n\n1. Wait 30 seconds\n2. Check spam folder\n3. Check your number is correct\n\nShall I resend it?",
        ]
    },
    {
        "type":"login",
        "keywords":["can't login","cannot login","forgot password",
                    "reset password","locked out","password help"],
        "responses":[
            "No worries! 🔐\n\nUse the 'Forgot Password' option on the login page.\n\nWould you like me to send you the reset link?",
            "Let's get you back in! 🔐\n\nClick 'Forgot Password' on the login screen.\n\nA reset link will arrive within 2 minutes. Shall I send it?",
        ]
    },
    {
        "type":"order",
        "keywords":["where is my order","track my order","order status",
                    "my delivery","shipping status","track parcel"],
        "responses":[
            "I can help with that! 📦\n\nPlease enter your Order ID to check the latest status.",
            "Let me look that up! 📦\n\nWhat's your Order ID?",
        ]
    },
]

def check_conversation_flow(message):
    expanded = expand_short_forms(message)
    for flow in CONVERSATION_FLOWS:
        if fuzzy_match_flow(expanded, flow["keywords"]):
            reply = random.choice(flow["responses"])
            if flow["type"] == "greeting":
                reply = f"{get_time_greeting()}\n\n{reply}"
            reply += get_hours_message()
            return reply, flow["type"]
    return None, None


# ── TODO FETCHER ──────────────────────────────────────────────
_todos_cache = None

def fetch_todos():
    global _todos_cache
    if _todos_cache is not None: return _todos_cache
    with urllib.request.urlopen("https://jsonplaceholder.typicode.com/todos", timeout=10) as r:
        _todos_cache = json.loads(r.read().decode())
    return _todos_cache

def build_todo_summary(user_id):
    try:
        todos = fetch_todos()
        ut    = [t for t in todos if t.get("userId") == user_id]
        if not ut: return f"No todos found for userId {user_id}. Try 1–10."
        total = len(ut)
        done  = sum(1 for t in ut if t.get("completed"))
        pct   = (done/total)*100
        f5    = "\n".join(f"  • {t['title']}" for t in ut[:5])
        return (f"📋 Todo Summary for userId {user_id}:\n\n"
                f"✅ Completed:  {done}\n⏳ Pending:    {total-done}\n"
                f"📊 Total:      {total}\n📈 Completion: {pct:.2f}%\n\n"
                f"First 5 titles:\n{f5}")
    except Exception as e:
        return f"⚠️ Could not fetch todos: {str(e)}"


# ── RAG + CLAUDE ──────────────────────────────────────────────
def ask_claude_with_rag(user_question, session_id):
    chunks  = retrieve(user_question, INDEXED_CHUNKS, top_k=3)
    context = "\n\n".join(
        f"[Source {i} — {c['source'].replace('.txt','').replace('_',' ').title()}]\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )
    history  = get_memory(session_id)
    messages = (history[-6:] if len(history) > 6 else history[:]) + [{
        "role":    "user",
        "content": f"Relevant documents:\n{context}\n\nQuestion: {user_question}"
    }]
    response = claude_client.messages.create(
        model      = "claude-opus-4-5",
        max_tokens = 500,
        system     = (
            "You are Zevoir Genie, the friendly AI assistant for Zevoir Technologies, Sydney Australia. "
            "Be professional, warm, concise. Use emojis appropriately. "
            "RULES: Answer ONLY from provided documents. If not in documents, say so and suggest support@zevoir.com.au. "
            "Mention which document the answer came from. Use bullet points for lists. "
            "If user seems interested in a demo or buying, encourage them to contact hello@zevoir.com.au"
        ),
        messages=messages
    )
    return response.content[0].text


# ── ROUTES ────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data    = request.get_json()
    message = data.get("message", "").strip()
    sid     = get_session_id(request)

    if not message:
        return jsonify({"reply":"Please type a message.","source":"error"})

    add_to_memory(sid, "user", message)
    update_lead(sid, message)

    # 1 — Number → todo
    try:
        uid   = int(message)
        reply = build_todo_summary(uid)
        add_to_memory(sid, "assistant", reply)
        return jsonify({"reply":reply,"source":"todo","suggestions":get_suggestions(message,"todo")})
    except ValueError:
        pass

    # 2 — Short casual phrase → common sense (≤4 words only)
    cs = check_common_sense(message)
    if cs:
        add_to_memory(sid, "assistant", cs)
        return jsonify({"reply":cs,"source":"flow","suggestions":get_suggestions(message,"flow")})

    # 3 — Conversation flow → fuzzy matched
    fr, ft = check_conversation_flow(message)
    if fr:
        full = fr + get_case_study(message)
        add_to_memory(sid, "assistant", full)
        return jsonify({"reply":full,"source":"flow","suggestions":get_suggestions(message, ft or "flow")})

    # 4 — RAG + Claude → real document answers
    try:
        expanded = expand_short_forms(message)
        reply    = ask_claude_with_rag(expanded, sid)
        full     = reply + get_case_study(message)
        add_to_memory(sid, "assistant", full)
        return jsonify({"reply":full,"source":"rag","suggestions":get_suggestions(message,"rag")})
    except anthropic.AuthenticationError:
        return jsonify({"reply":"⚠️ API key error. Check your ANTHROPIC_API_KEY.","source":"error"})
    except Exception as e:
        return jsonify({"reply":f"⚠️ Something went wrong: {str(e)}","source":"error"})


@app.route("/rate", methods=["POST"])
def rate():
    data = request.get_json()
    sid  = get_session_id(request)
    if sid not in rating_store: rating_store[sid] = []
    rating_store[sid].append({
        "message":   data.get("message","")[:100],
        "rating":    data.get("rating",""),
        "timestamp": datetime.now().isoformat()
    })
    if data.get("rating") == "up":
        return jsonify({"status":"saved","reply":"Thanks for the feedback! 😊"})
    return jsonify({"status":"saved","reply":"Sorry about that! 🙏 We'll keep improving."})


@app.route("/lead", methods=["POST"])
def save_lead():
    data    = request.get_json()
    sid     = get_session_id(request)
    name    = data.get("name","").strip()
    email   = data.get("email","").strip()
    company = data.get("company","").strip()
    if not name or not email:
        return jsonify({"status":"error","reply":"Please provide name and email."})
    score = lead_store.get(sid, {}).get("score","warm")
    if sid not in lead_store: lead_store[sid] = {}
    lead_store[sid].update({"name":name,"email":email,"company":company,
                             "score":score,"timestamp":datetime.now().isoformat()})
    print(f"\n🎯 NEW LEAD [{score.upper()}]: {name} | {email} | {company}\n")
    return jsonify({"status":"saved","reply":(
        f"🎉 Thank you, {name}!\n\nWe've saved your details and will reach out to "
        f"{email} within 24 hours.\n\nLooking forward to working with you! 🚀"
    )})


@app.route("/leads", methods=["GET"])
def view_leads():
    return jsonify({"total_leads":len(lead_store),"leads":list(lead_store.values())})


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Zevoir Genie — Enhanced RAG Chatbot")
    print("  Chatbot: http://localhost:5000")
    print("  Leads:   http://localhost:5000/leads")
    print("="*55 + "\n")
    app.run(debug=True, port=5000)