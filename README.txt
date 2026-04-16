=============================================================
  ZEVOIR GENIE — RAG CHATBOT
  Setup and Run Instructions
=============================================================

WHAT THIS PROJECT IS:
  A full RAG (Retrieval-Augmented Generation) chatbot that:
  - Answers questions from Zevoir's documents using Claude AI
  - Handles greetings and support flows (rule-based)
  - Fetches todo stats when user types a number (1-10)
  - Has dark/light mode toggle
  - Shows source badge (answered from documents / conversation / API)


PROJECT STRUCTURE:
  zevoir_rag/
    app.py              ← Flask server (connects everything)
    rag.py              ← RAG pipeline (chunks, embeds, retrieves)
    requirements.txt    ← Python libraries to install
    .env                ← Your API key goes here
    documents/
      services.txt      ← Zevoir services info
      faq.txt           ← Frequently asked questions
      pricing.txt       ← Pricing information
      support.txt       ← Support and account help
      about.txt         ← About Zevoir Technologies
    templates/
      index.html        ← Chat UI (HTML/CSS/JavaScript)


=============================================================
  STEP 1 — ADD YOUR API KEY
=============================================================

Open the .env file and replace the placeholder:

  ANTHROPIC_API_KEY=your-api-key-here

Change it to your actual key:

  ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx

Save the file.


=============================================================
  STEP 2 — INSTALL PYTHON LIBRARIES
=============================================================

Open your terminal (PowerShell on Windows) and run:

  pip install -r requirements.txt

This installs:
  - flask             (web server)
  - anthropic         (Claude API)
  - sentence-transformers (converts text to vectors, free)
  - numpy             (math for similarity calculation)

NOTE: sentence-transformers downloads a small model (~90MB)
on first run. This is automatic — just takes a minute.


=============================================================
  STEP 3 — SET YOUR API KEY IN TERMINAL
=============================================================

On Windows (PowerShell):
  $env:ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxxxxxxxxx"

On Mac/Linux:
  export ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxxxxxxxxx"

Replace with your actual key from the .env file.


=============================================================
  STEP 4 — RUN THE SERVER
=============================================================

In your terminal, from the zevoir_rag folder:

  python app.py

You will see:
  Loading embedding model...
  Embedding model loaded.
  Loaded X chunks from documents/
  Indexed X chunks successfully.
  ==================================================
    Zevoir Genie RAG Chatbot starting...
    Open: http://localhost:5000
  ==================================================


=============================================================
  STEP 5 — OPEN IN BROWSER
=============================================================

Open your browser and go to:
  http://localhost:5000

You should see the Zevoir Genie chat interface.


=============================================================
  HOW TO TEST IT
=============================================================

Try these messages:

  "Hi"
    → Conversation flow (greeting)

  "What services does Zevoir offer?"
    → RAG answer from services.txt

  "How much does a chatbot cost?"
    → RAG answer from pricing.txt

  "How do I reset my password?"
    → Conversation flow OR RAG from support.txt

  "What is RAG?"
    → RAG answer from faq.txt

  "1"
    → Fetches todos for userId 1 from API

  "Tell me about Zevoir"
    → RAG answer from about.txt

Each answer shows a small badge at the bottom:
  📄 Answered from Zevoir documents  → came from RAG
  💬 Conversation flow               → rule-based reply
  🔗 Fetched from API                → todo data


=============================================================
  HOW TO ADD YOUR OWN DOCUMENTS
=============================================================

1. Create a .txt file in the documents/ folder
2. Write your content (services, FAQs, policies, etc.)
3. Restart the server (Ctrl+C then python app.py again)
4. The new documents are automatically indexed

That's it! The chatbot will now answer from your new documents.


=============================================================
  TROUBLESHOOTING
=============================================================

"API key error" in chat:
  → Check your API key in .env and in terminal environment variable

"Could not reach the server":
  → Make sure app.py is running in terminal

Slow first start:
  → Normal! sentence-transformers downloads model on first run

"Module not found" error:
  → Run: pip install -r requirements.txt again
