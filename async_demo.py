"""
async_demo.py — asyncio Example for Zevoir

YOUR APP ALREADY DOES THIS SYNCHRONOUSLY:
  In app.py, fetch_todos() uses urllib.request.urlopen()
  This is BLOCKING — it waits for the response before continuing.

  If you had to fetch todos for 5 users at once, it would do:
    User 1 → wait → User 2 → wait → User 3 → wait ...

THIS FILE SHOWS:
  The same logic rewritten with asyncio + aiohttp.
  All 5 requests fire AT THE SAME TIME and we wait for all of them.

  User 1 ─┐
  User 2 ─┤→ all fire at once → all arrive → process
  User 3 ─┘

WHY THIS MATTERS FOR OPTIVER:
  Optiver's AI agents need to handle multiple data sources
  concurrently — market feeds, risk calculations, model inference.
  asyncio is the foundation of that. If you understand this,
  you understand why FastAPI (their likely production choice)
  uses it too.

REQUIREMENTS:
  pip install aiohttp
"""

import asyncio
import time
import urllib.request
import json


# ──────────────────────────────────────────────────────────────
# SYNCHRONOUS VERSION (what app.py does now)
# ──────────────────────────────────────────────────────────────

def fetch_user_todos_sync(user_id: int) -> dict:
    """
    Fetches todos for one user — BLOCKING.
    The program stops here and waits until the response arrives.
    """
    url = f"https://jsonplaceholder.typicode.com/todos?userId={user_id}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        todos = json.loads(resp.read().decode())
    completed = sum(1 for t in todos if t["completed"])
    return {"user_id": user_id, "total": len(todos), "completed": completed}


def run_sync(user_ids: list) -> list:
    """Fetch todos for multiple users one by one (slow)"""
    results = []
    for uid in user_ids:
        result = fetch_user_todos_sync(uid)
        results.append(result)
    return results


# ──────────────────────────────────────────────────────────────
# ASYNC VERSION (the upgrade)
# ──────────────────────────────────────────────────────────────

async def fetch_user_todos_async(session, user_id: int) -> dict:
    """
    Fetches todos for one user — NON-BLOCKING.

    'async def' means this is a coroutine.
    'await' means: start this, then let other coroutines run
    while we wait for the network response to come back.
    """
    import aiohttp
    url = f"https://jsonplaceholder.typicode.com/todos?userId={user_id}"

    async with session.get(url) as response:   # async HTTP request
        todos = await response.json()          # await the response

    completed = sum(1 for t in todos if t["completed"])
    return {"user_id": user_id, "total": len(todos), "completed": completed}


async def run_async(user_ids: list) -> list:
    """
    Fetch todos for multiple users all at once (fast).

    asyncio.gather() fires all coroutines simultaneously
    and waits for ALL of them to finish.
    """
    import aiohttp

    # One shared session for all requests (more efficient)
    async with aiohttp.ClientSession() as session:
        # Create all tasks at once
        tasks = [fetch_user_todos_async(session, uid) for uid in user_ids]
        # Fire them all simultaneously and wait
        results = await asyncio.gather(*tasks)

    return list(results)


# ──────────────────────────────────────────────────────────────
# DEMO — compare sync vs async timing
# ──────────────────────────────────────────────────────────────

def demo():
    user_ids = [1, 2, 3, 4, 5]

    print("=" * 55)
    print("  SYNC version (one at a time — blocking)")
    print("=" * 55)
    start = time.time()
    sync_results = run_sync(user_ids)
    sync_time = time.time() - start

    for r in sync_results:
        print(f"  User {r['user_id']}: {r['completed']}/{r['total']} completed")
    print(f"\n  Time taken: {sync_time:.2f}s")

    print()
    print("=" * 55)
    print("  ASYNC version (all at once — non-blocking)")
    print("=" * 55)

    try:
        start = time.time()
        async_results = asyncio.run(run_async(user_ids))  # entry point for async
        async_time = time.time() - start

        for r in async_results:
            print(f"  User {r['user_id']}: {r['completed']}/{r['total']} completed")
        print(f"\n  Time taken: {async_time:.2f}s")

        print()
        print(f"  Async was {sync_time / async_time:.1f}x faster")

    except ImportError:
        print("  aiohttp not installed. Run: pip install aiohttp")
        print("  (The sync version above still demonstrates the concept)")

    print()
    print("=" * 55)
    print("  KEY TAKEAWAY FOR INTERVIEW")
    print("=" * 55)
    print("  'My Zevoir chatbot fetches todos synchronously.")
    print("  I also built an async version using asyncio.gather()")
    print("  to fire multiple requests concurrently — this is the")
    print("  same pattern used in production AI agent pipelines")
    print("  when calling multiple data sources simultaneously.'")


if __name__ == "__main__":
    demo()
